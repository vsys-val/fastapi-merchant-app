"""Catálogo inicial: ~500 produtos do Open Food Facts em nome de "Catálogo Merchant".

Os dados vêm de ``data/catalogo-inicial.json``, gerado por
``scripts/build_catalog_seed.py`` já normalizado pelas regras da API. A
migração só insere: produtos que já existem (mesma identidade ou mesmo
código de barras, inclusive excluídos) ficam como estão.
"""

import json
import secrets
from pathlib import Path

from alembic import op
import sqlalchemy as sa
from pwdlib import PasswordHash

revision = "0010_catalog_seed"
down_revision = "0009_product_image"
branch_labels = None
depends_on = None

SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "catalogo-inicial.json"
CURATOR_EMAIL = "catalogo@merchant-app.invalid"
CURATOR_NAME = "Catálogo Merchant"

_INSERT_PRODUCT = sa.text(
    """
    INSERT INTO produtos (
        criador_id, nome, marca, variante, quantidade, unidade, categoria,
        codigo_barras, chave_identidade, nome_busca, marca_busca, imagem_url
    ) VALUES (
        :curator_id, :name, :brand, :variant, CAST(:quantity AS numeric), :unit, :category,
        :barcode, :identity_key, :search_name, :search_brand, :image_url
    )
    ON CONFLICT DO NOTHING
    """
)


def curator_id(connection) -> int:
    """Conta dona do catálogo inicial; ninguém sabe a senha, então ninguém entra nela."""

    existing = connection.execute(
        sa.text("SELECT id FROM usuarios WHERE email = :email"), {"email": CURATOR_EMAIL}
    ).scalar()
    if existing is not None:
        return existing
    return connection.execute(
        sa.text(
            """
            INSERT INTO usuarios (nome_publico, email, senha_hash, email_verificado_em)
            VALUES (:name, :email, :password_hash, now())
            RETURNING id
            """
        ),
        {
            "name": CURATOR_NAME,
            "email": CURATOR_EMAIL,
            "password_hash": PasswordHash.recommended().hash(secrets.token_urlsafe(48)),
        },
    ).scalar_one()


def seed(connection, products: list[dict]) -> int:
    """Insere os produtos que ainda não existem e devolve quantos entraram."""

    owner = curator_id(connection)
    columns = ("name", "brand", "variant", "quantity", "unit", "category", "barcode",
               "identity_key", "search_name", "search_brand")
    before = connection.execute(
        sa.text("SELECT count(*) FROM produtos WHERE criador_id = :id"), {"id": owner}
    ).scalar_one()
    rows = [
        {"curator_id": owner, "image_url": product.get("image_url"), **{column: product[column] for column in columns}}
        for product in products
    ]
    if rows:
        connection.execute(_INSERT_PRODUCT, rows)
    after = connection.execute(
        sa.text("SELECT count(*) FROM produtos WHERE criador_id = :id"), {"id": owner}
    ).scalar_one()
    return after - before


def unseed(connection) -> None:
    """Remove só o que ninguém avaliou; a conta sai quando não sobra produto dela."""

    connection.execute(
        sa.text(
            """
            DELETE FROM produtos p
             USING usuarios u
             WHERE p.criador_id = u.id
               AND u.email = :email
               AND NOT EXISTS (SELECT 1 FROM avaliacoes a WHERE a.produto_id = p.id)
            """
        ),
        {"email": CURATOR_EMAIL},
    )
    connection.execute(
        sa.text(
            """
            DELETE FROM usuarios u
             WHERE u.email = :email
               AND NOT EXISTS (SELECT 1 FROM produtos p WHERE p.criador_id = u.id)
            """
        ),
        {"email": CURATOR_EMAIL},
    )


def upgrade() -> None:
    products = json.loads(SEED_FILE.read_text(encoding="utf-8"))["products"]
    seed(op.get_bind(), products)


def downgrade() -> None:
    unseed(op.get_bind())
