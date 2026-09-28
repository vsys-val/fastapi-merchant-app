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
pela licença ODbL, e a migração 0010 o insere no banco.
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
        "image_front_url",
    ]
)
# Só fotos servidas pelas próprias bases (CC BY-SA); o site libera esses hosts na CSP.
IMAGE_URL = re.compile(
    r"^https://images\.open(food|beauty|products)facts\.org/images/products/[0-9/]+/front_[a-z]{2}\.\d+\.400\.jpg$"
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

# Categoria pelo nome: as etiquetas das bases abertas são irregulares. A ordem
# importa (limpeza antes de utilidades antes de bebidas).
NAME_CATEGORIES = (
    (
        "cleaning",
        re.compile(
            r"lava[ -]?lou[cç]as?|lava[ -]?roupas?|lavagem|sab[aã]o (em p[oó]|l[ií]quido|em barra)|amaciante|"
            r"detergente|desinfetante|[aá]gua sanit[aá]ria|alvejante|limpador|limpa[ -]|multiuso|"
            r"tira[ -]?manchas|[aá]lcool (em )?(gel|l[ií]quido|70)",
            re.IGNORECASE,
        ),
    ),
    (
        "household_utilities",
        re.compile(
            r"filtro de papel|coador|saco (de|para) lixo|palito|papel alum[ií]nio|filme pl[aá]stico|"
            r"guardanapo|papel toalha|f[oó]sforos?\b|\bvelas?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "beverages",
        re.compile(
            r"refrigerante|guaran[aá]|\bsuco|refresco|n[eé]ctar|\b[aá]gua\b|\bch[aá]\b|\bmatt?e\b|cerveja|"
            r"energ[eé]tico|\benergy\b|isot[oô]nico|\bbebida|\bcoca\b|\bsoda\b|t[oô]nica|kombucha",
            re.IGNORECASE,
        ),
    ),
)
BEVERAGE_TAGS = ("en:beverages", "en:waters", "en:sodas", "en:juices")
# Marcas que são nomes de produto, não marcas (erros de preenchimento na fonte).
GENERIC_BRANDS = {"mas", "margarina", "locao hidratante", "gourmet", "generico", "sem marca", "creme"}
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
# Siglas que continuam em maiúsculas.
ACRONYMS = {"UHT", "UHT.", "PET", "TP", "BR", "ZMA", "DHA", "SPF", "FPS"}


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


def _soften_shouting(word: str) -> str:
    """Uma palavra gritada no meio do nome ("NESCAU") vira "Nescau"; siglas ficam."""

    letters = [char for char in word if char.isalpha()]
    if len(letters) >= 4 and all(char.isupper() for char in letters) and word not in ACRONYMS:
        return word[:1] + word[1:].lower()
    return word


def clean_brand(raw: str) -> str:
    brand = tidy_case(raw.split(",")[0].strip())
    # Marca toda em minúsculas ("quatá", "coca cola") ganha iniciais maiúsculas.
    if brand and brand == brand.lower():
        brand = " ".join(word[:1].upper() + word[1:] for word in brand.split())
    return brand


def clean_name(raw: str, brand: str) -> str:
    name = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", raw)).strip(" -–,.")
    # Quantidade no fim do nome ("Arroz Tipo 1 5kg", "Açúcar (1 kg)") já vai no campo próprio.
    name = re.sub(
        r"\s*[-–,]?\s*\(?\d+(?:[.,]\d+)?\s*(kg|g|gr|ml|l|lt|un)\.?\)?$", "", name, flags=re.IGNORECASE
    ).strip(" -–,.")
    if not name:
        return ""
    name = tidy_case(name)
    words = [_soften_shouting(word) for word in name.split()]
    brand_words = identity_text(brand).split()
    # "YOKI Batata Palha" → "Batata Palha": a marca repetida no começo sai quando sobra nome.
    if brand_words and len(words) > len(brand_words) + 1 and [identity_text(w) for w in words[: len(brand_words)]] == brand_words:
        words = words[len(brand_words):]
        if words and words[0] in {"-", "–"}:
            words = words[1:]
    # "Bacon - Torcida - Torcida": a marca repetida no fim sai.
    while len(words) > 2 and words[-2] in {"-", "–"} and identity_text(words[-1]) == identity_text(brand):
        words = words[:-2]
    name = " ".join(words)
    return name[:1].upper() + name[1:]


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


def category_of(source: Source, tags: list[str], name: str = "", unit: str = "") -> str | None:
    """Categoria do produto; ``None`` quando a base de utilidades traz algo fora do mercado."""

    if source.host.startswith("world.openbeautyfacts"):
        # Na base de higiene, "água micelar" e "água de colônia" não são bebidas.
        cleaning = NAME_CATEGORIES[0][1]
        return "cleaning" if cleaning.search(name) else "personal_hygiene"
    for category, pattern in NAME_CATEGORIES:
        if pattern.search(name):
            return category
    if source.host.startswith("world.openproductsfacts"):
        # Sem palavra reconhecida, a base de produtos traz de tudo (livros, suplementos...).
        return None
    # Pós para preparar (leite em pó, achocolatado, café) ficam em alimentos.
    if any(tag in tags for tag in BEVERAGE_TAGS) and unit != "g":
        return "beverages"
    return "food"


def image_url_of(product: dict) -> str | None:
    url = (product.get("image_front_url") or "").strip()
    return url if IMAGE_URL.match(url) else None


def to_seed_row(source: Source, product: dict) -> dict | None:
    raw_name = (product.get("product_name_pt") or product.get("product_name") or "").strip()
    brand = clean_brand(product.get("brands") or "")
    name = clean_name(raw_name, brand)
    quantity = quantity_of(product)
    code = (product.get("code") or "").strip()
    if not brand or not name or quantity is None or identity_text(name) == identity_text(brand):
        return None
    if identity_text(brand) in GENERIC_BRANDS:
        return None
    # Nome de uma palavra só, todo em minúsculas ("predilecta", "maionese"): dado incompleto.
    if " " not in raw_name and raw_name == raw_name.lower():
        return None
    normalized_unit = "g" if quantity[1] in {"g", "kg"} else "ml" if quantity[1] in {"ml", "L"} else "un"
    category = category_of(source, product.get("categories_tags") or [], name, normalized_unit)
    if category is None:
        return None
    try:
        payload = ProductCreate(
            name=name,
            brand=brand,
            variant=None,
            quantity=quantity[0],
            unit=quantity[1],
            category=category,
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
        "image_url": image_url_of(product),
        "scans": int(product.get("unique_scans_n") or 0),
    }


def drop_brand_conflicts(candidates: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], int]:
    """Descarta produtos com a marca trocada na fonte ("Água de coco Sococo", marca Kellogg's).

    Só quando a marca aparece uma única vez no catálogo, não está no nome, e o
    nome cita outra marca da mesma categoria. Submarcas ("Nescau", da Nestlé)
    ficam, porque a marca-mãe se repete em outros produtos.
    """

    counts = Counter(row["search_brand"] for rows in candidates.values() for row in rows)
    kept: dict[str, list[dict]] = {}
    dropped = 0
    for category, rows in candidates.items():
        brands = {row["search_brand"] for row in rows if len(row["search_brand"]) >= 5}
        kept[category] = []
        for row in rows:
            name = f" {row['search_name']} "
            own = row["search_brand"]
            cites_other = any(f" {brand} " in name for brand in brands if brand != own)
            if counts[own] == 1 and f" {own} " not in name and cites_other:
                dropped += 1
                continue
            kept[category].append(row)
    return kept, dropped


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

    candidates, conflicting = drop_brand_conflicts(candidates)
    rejected["marca trocada"] = conflicting

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
    print(f"Com foto: {sum(1 for row in selected if row['image_url'])}")


if __name__ == "__main__":
    main()
