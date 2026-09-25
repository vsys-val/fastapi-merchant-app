"""Busca no banco: nome e marca normalizados e índices de trigrama."""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "0008_database_search"
down_revision = "0007_observability"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "merchant_app_runtime"
_WHITESPACE = re.compile(r"\s+")


def _identity_text(value: str) -> str:
    # Cópia congelada de app.validation.identity_text: a migração não deve
    # mudar de comportamento se a aplicação mudar depois.
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _WHITESPACE.sub(" ", without_accents.casefold()).strip()


def upgrade() -> None:
    op.add_column("produtos", sa.Column("nome_busca", sa.Text(), nullable=True))
    op.add_column("produtos", sa.Column("marca_busca", sa.Text(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, nome, marca FROM produtos")).all()
    for product_id, name, brand in rows:
        connection.execute(
            sa.text("UPDATE produtos SET nome_busca = :nome, marca_busca = :marca WHERE id = :id"),
            {"id": product_id, "nome": _identity_text(name), "marca": _identity_text(brand)},
        )
    op.alter_column("produtos", "nome_busca", nullable=False)
    op.alter_column("produtos", "marca_busca", nullable=False)

    # No Supabase as extensões ficam no schema "extensions"; num PostgreSQL
    # comum, em "public". O papel da API precisa usar o schema escolhido.
    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE
                target text := CASE
                    WHEN EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'extensions')
                    THEN 'extensions' ELSE 'public' END;
                installed text;
            BEGIN
                EXECUTE format('CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA %I', target);
                SELECT n.nspname INTO installed
                  FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
                 WHERE e.extname = 'pg_trgm';
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                    EXECUTE format('GRANT USAGE ON SCHEMA %I TO {RUNTIME_ROLE}', installed);
                END IF;
                EXECUTE format(
                    'CREATE INDEX ix_produtos_nome_busca_trgm ON produtos USING gin (nome_busca %I.gin_trgm_ops)',
                    installed
                );
                EXECUTE format(
                    'CREATE INDEX ix_produtos_marca_busca_trgm ON produtos USING gin (marca_busca %I.gin_trgm_ops)',
                    installed
                );
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_produtos_marca_busca_trgm", table_name="produtos")
    op.drop_index("ix_produtos_nome_busca_trgm", table_name="produtos")
    op.drop_column("produtos", "marca_busca")
    op.drop_column("produtos", "nome_busca")
    # A extensão e o GRANT ficam: outros objetos podem depender deles.
