"""Monta o catálogo inicial a partir das bases abertas do Open Food Facts.

Roda no GitHub Actions (workflow catalog-seed), que tem acesso à internet.
Busca os produtos vendidos no Brasil mais escaneados em três bases irmãs:

- Open Food Facts: alimentos e bebidas;
- Open Beauty Facts: higiene pessoal;
- Open Products Facts: limpeza e utilidades.

Cada produto passa pelas mesmas regras de entrada da API (``ProductCreate``):
nome, marca, quantidade canônica e código de barras com dígito verificador.
Produtos repetidos pela identidade (RN08) ou pelo código são descartados.
O resultado vai para ``data/catalogo-inicial.json`` com a atribuição exigida
pela licença ODbL, e a migração 0009 o insere no banco.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError  # noqa: E402

from app.schemas import ProductCreate  # noqa: E402
from app.validation import build_identity_key, identity_text  # noqa: E402

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "catalogo-inicial.json"
USER_AGENT = "MerchantApp/1.0 (https://github.com/vsys-val/fastapi-merchant-app)"
FIELDS = ",".join(
    [
        "code",
        "product_name_pt",
        "product_name",
        "brands",
        "quantity",
        "product_quantity",
        "product_quantity_unit",
        "categories_tags",
        "unique_scans_n",
    ]
)
# A API de busca aceita 10 requisições por minuto.
PAUSE_SECONDS = 7

# Quantos produtos de cada categoria entram no catálogo (~500 no total).
TARGETS = {
    "food": 260,
    "beverages": 110,
    "personal_hygiene": 70,
    "cleaning": 45,
    "household_utilities": 15,
}


@dataclass(frozen=True)
class Source:
    name: str
    host: str
    pages: int


SOURCES = (
    Source("Open Food Facts", "world.openfoodfacts.org", 25),
    Source("Open Beauty Facts", "world.openbeautyfacts.org", 6),
    Source("Open Products Facts", "world.openproductsfacts.org", 6),
)

CLEANING_TAGS = (
    "clean",
    "detergent",
    "laundry",
    "dishwash",
    "disinfect",
    "bleach",
    "soap-for-dishes",
    "fabric-softener",
    "limpeza",
)
BEVERAGE_TAGS = ("en:beverages", "en:waters", "en:sodas", "en:juices")
QUANTITY = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|grs|gramas|mg|l|lt|litros?|ml|cl|un|und|unid|unidades?)\b",
    re.IGNORECASE,
)
UNIT_ALIASES = {
    "kg": "kg",
    "g": "g",
    "gr": "g",
    "grs": "g",
    "gramas": "g",
    "l": "L",
    "lt": "L",
    "litro": "L",
    "litros": "L",
    "ml": "ml",
    "un": "un",
    "und": "un",
    "unid": "un",
    "unidade": "un",
    "unidades": "un",
}
# Palavras que ficam em minúsculas quando o nome vem todo em maiúsculas.
LOWER_WORDS = {"de", "da", "do", "das", "dos", "e", "com", "sem", "em", "para", "a", "o", "ao"}


def fetch(source: Source, page: int) -> list[dict]:
    query = urlencode(
        {
            "countries_tags_en": "brazil",
            "sort_by": "unique_scans_n",
            "page_size": 100,
            "page": page,
            "fields": FIELDS,
        }
    )
    url = f"https://{source.host}/api/v2/search?{query}"
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as response:
                return json.load(response).get("products", [])
        except Exception as exc:  # noqa: BLE001 - rede instável: tentar de novo
            print(f"  {source.name} página {page}: tentativa {attempt + 1} falhou ({exc})")
            time.sleep(PAUSE_SECONDS * (attempt + 2))
    return []


def tidy_case(value: str) -> str:
    """Nomes TODOS EM MAIÚSCULAS viram "Iniciais maiúsculas"; o resto fica igual."""

    letters = [char for char in value if char.isalpha()]
    if not letters or sum(char.isupper() for char in letters) / len(letters) < 0.8:
        return value
    words = value.lower().split()
    return " ".join(
        word if index and word in LOWER_WORDS else word[:1].upper() + word[1:]
        for index, word in enumerate(words)
    )


def clean_name(raw: str, brand: str) -> str:
    name = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", raw)).strip(" -–,.")
    # Quantidade no fim do nome ("Arroz Tipo 1 5kg") já vai no campo próprio.
    name = re.sub(r"\s*[-–,]?\s*\d+(?:[.,]\d+)?\s*(kg|g|gr|ml|l|lt|un)\.?$", "", name, flags=re.IGNORECASE)
    return tidy_case(name.strip()) if name.strip() else ""


def clean_brand(raw: str) -> str:
    brand = raw.split(",")[0].strip()
    return tidy_case(brand)


def quantity_of(product: dict) -> tuple[Decimal, str] | None:
    amount = product.get("product_quantity")
    unit = (product.get("product_quantity_unit") or "").strip().lower()
    text = (product.get("quantity") or "").strip()
    # Embalagens múltiplas ("6 x 200 ml") ficam de fora: a quantidade do produto é ambígua.
    if re.search(r"\d\s*[x×]\s*\d", text, re.IGNORECASE):
        return None
    if amount not in (None, "") and unit in {"g", "ml"}:
        try:
            value = Decimal(str(amount))
        except ArithmeticError:
            value = None
        if value is not None and value > 0:
            return value, unit
    match = QUANTITY.match(text)
    if not match:
        return None
    value = Decimal(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    if unit == "mg":
        return value / 1000, "g"
    if unit == "cl":
        return value * 10, "ml"
    return value, UNIT_ALIASES[unit]


def category_of(source: Source, tags: list[str]) -> str:
    if source.host.startswith("world.openbeautyfacts"):
        return "personal_hygiene"
    if source.host.startswith("world.openproductsfacts"):
        joined = " ".join(tags)
        return "cleaning" if any(tag in joined for tag in CLEANING_TAGS) else "household_utilities"
    return "beverages" if any(tag in tags for tag in BEVERAGE_TAGS) else "food"


def to_seed_row(source: Source, product: dict) -> dict | None:
    brand = clean_brand(product.get("brands") or "")
    name = clean_name(product.get("product_name_pt") or product.get("product_name") or "", brand)
    quantity = quantity_of(product)
    code = (product.get("code") or "").strip()
    if not brand or not name or quantity is None or identity_text(name) == identity_text(brand):
        return None
    try:
        payload = ProductCreate(
            name=name,
            brand=brand,
            variant=None,
            quantity=quantity[0],
            unit=quantity[1],
            category=category_of(source, product.get("categories_tags") or []),
            barcode=code or None,
        )
    except ValidationError:
        return None
    return {
        "name": payload.name,
        "brand": payload.brand,
        "variant": payload.variant,
        "quantity": format(payload.quantity.normalize(), "f"),
        "unit": payload.unit,
        "category": payload.category,
        "barcode": payload.barcode,
        "identity_key": build_identity_key(
            name=payload.name,
            brand=payload.brand,
            variant=payload.variant,
            quantity=payload.quantity,
            unit=payload.unit,
        ),
        "search_name": identity_text(payload.name),
        "search_brand": identity_text(payload.brand),
        "source": source.name,
        "source_url": f"https://{source.host}/product/{payload.barcode}" if payload.barcode else None,
        "scans": int(product.get("unique_scans_n") or 0),
    }


def main() -> None:
    candidates: dict[str, list[dict]] = {category: [] for category in TARGETS}
    seen_keys: set[str] = set()
    seen_codes: set[str] = set()
    rejected = Counter()
    for source in SOURCES:
        print(f"== {source.name}")
        for page in range(1, source.pages + 1):
            products = fetch(source, page)
            print(f"  página {page}: {len(products)} produtos")
            if not products:
                break
            for product in products:
                row = to_seed_row(source, product)
                if row is None:
                    rejected[source.name] += 1
                    continue
                if row["identity_key"] in seen_keys or (row["barcode"] and row["barcode"] in seen_codes):
                    rejected["repetidos"] += 1
                    continue
                seen_keys.add(row["identity_key"])
                if row["barcode"]:
                    seen_codes.add(row["barcode"])
                candidates[row["category"]].append(row)
            time.sleep(PAUSE_SECONDS)

    selected: list[dict] = []
    shortfall = 0
    for category, target in TARGETS.items():
        ranked = sorted(candidates[category], key=lambda row: -row["scans"])
        selected.extend(ranked[:target])
        shortfall += max(0, target - len(ranked))
    # O que faltar numa categoria é completado com os alimentos seguintes mais escaneados.
    extra_food = sorted(candidates["food"], key=lambda row: -row["scans"])[TARGETS["food"] :]
    selected.extend(extra_food[:shortfall])

    for row in selected:
        row.pop("scans")
    selected.sort(key=lambda row: (row["category"], row["search_brand"], row["search_name"]))

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "attribution": (
                    "Dados de produtos do Open Food Facts, Open Beauty Facts e Open Products Facts "
                    "(https://openfoodfacts.org), disponíveis sob a Open Database License (ODbL)."
                ),
                "license": "ODbL-1.0",
                "products": selected,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    by_category = Counter(row["category"] for row in selected)
    print(f"\nCandidatos por categoria: { {key: len(value) for key, value in candidates.items()} }")
    print(f"Rejeitados: {dict(rejected)}")
    print(f"Selecionados: {len(selected)} {dict(by_category)}")


if __name__ == "__main__":
    main()
