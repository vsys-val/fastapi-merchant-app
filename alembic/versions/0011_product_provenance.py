"""Proveniência opcional; backfill conservador do snapshot congelado da 0010.

Não altera identidade, dono, imagem, exclusão nem avaliações. Campos de licença
não verificados permanecem nulos. Não consulta serviços externos.
"""
import hashlib
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "0011_product_provenance"
down_revision = "0010_catalog_seed"
branch_labels = None
depends_on = None

COLUMNS = ("source", "source_url", "image_source", "image_license", "image_license_url")
SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "catalogo-inicial.json"
SEED_SHA256 = "04cfd55586755c23efb4d5ea2061c685bc369d969fe6fe742d50e41e4c1200d9"
# Sources: official Product Opener license guide; official OpenBeautyFacts.pdf.
# These confirm the family only; do not guess a version or photographer.
VERIFIED_IMAGE_LICENSES = {
    "Open Food Facts": "CC-BY-SA",
    "Open Beauty Facts": "CC-BY-SA",
}
SOURCES = {
    "Open Food Facts": "world.openfoodfacts.org",
    "Open Beauty Facts": "world.openbeautyfacts.org",
    "Open Products Facts": "world.openproductsfacts.org",
}


def backfill(connection, products):
    changed = 0
    for product in products:
        source = product.get("source")
        code = product.get("barcode")
        # Reject unknown provenance and require the exact original source URL.
        if source not in SOURCES or not code:
            continue
        source_url = f"https://{SOURCES[source]}/product/{code}"
        if product.get("source_url") != source_url:
            continue
        image = product.get("image_url")
        result = connection.execute(sa.text("""
            UPDATE produtos SET source = :source, source_url = :source_url,
                image_source = :image_source, image_license = :image_license
            WHERE chave_identidade = :identity_key AND codigo_barras = :barcode
              AND (imagem_url = :image_url OR (imagem_url IS NULL AND :image_url IS NULL))
              AND criador_id IN (SELECT id FROM usuarios WHERE email = :curator)
              AND source IS NULL AND source_url IS NULL AND image_source IS NULL
              AND image_license IS NULL AND image_license_url IS NULL
        """), {
            "source": source, "source_url": source_url,
            "image_source": source if image else None,
            "image_license": VERIFIED_IMAGE_LICENSES.get(source) if image else None,
            "identity_key": product["identity_key"], "barcode": code,
            "image_url": image, "curator": "catalogo@merchant-app.invalid",
        })
        changed += result.rowcount
    return changed


def upgrade():
    raw = SEED_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SEED_SHA256:
        raise RuntimeError("O snapshot publicado da migração 0010 foi alterado")
    for column in COLUMNS:
        op.add_column("produtos", sa.Column(column, sa.Text(), nullable=True))
    backfill(op.get_bind(), json.loads(raw)["products"])


def downgrade():
    for column in reversed(COLUMNS):
        op.drop_column("produtos", column)
