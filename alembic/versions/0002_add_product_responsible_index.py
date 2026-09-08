"""Adiciona índice para a relação entre produto e responsável."""

from alembic import op

revision = "0002_product_owner_index"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_produtos_criador_id", "produtos", ["criador_id"])


def downgrade() -> None:
    op.drop_index("ix_produtos_criador_id", table_name="produtos")
