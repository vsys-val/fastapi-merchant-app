"""Foto da embalagem do produto (endereço público, sem armazenamento próprio)."""

from alembic import op
import sqlalchemy as sa

revision = "0009_product_image"
down_revision = "0008_database_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("produtos", sa.Column("imagem_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("produtos", "imagem_url")
