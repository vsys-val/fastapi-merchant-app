"""Cria o papel de mínimo privilégio usado pela aplicação em produção."""

from alembic import op
import sqlalchemy as sa

revision = "0005_runtime_role"
down_revision = "0004_login_rate_limits"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "merchant_app_runtime"
RUNTIME_TABLES = (
    "usuarios",
    "produtos",
    "avaliacoes",
    "motivos_avaliacao",
    "limites_login",
)


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}'
                ) THEN
                    CREATE ROLE {RUNTIME_ROLE}
                        NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                        NOREPLICATION NOBYPASSRLS;
                END IF;
            END $$
            """
        )
    )
    op.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}"))

    for table_name in RUNTIME_TABLES:
        op.execute(
            sa.text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE "
                f"ON TABLE public.{table_name} TO {RUNTIME_ROLE}"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY {table_name}_runtime_access "
                f"ON public.{table_name} FOR ALL TO {RUNTIME_ROLE} "
                "USING (true) WITH CHECK (true)"
            )
        )

    op.execute(
        sa.text(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE}"
        )
    )
    op.execute(
        sa.text(
            f"REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM {RUNTIME_ROLE}"
        )
    )


def downgrade() -> None:
    for table_name in RUNTIME_TABLES:
        op.execute(
            sa.text(
                f"DROP POLICY IF EXISTS {table_name}_runtime_access "
                f"ON public.{table_name}"
            )
        )
        op.execute(
            sa.text(f"REVOKE ALL PRIVILEGES ON TABLE public.{table_name} FROM {RUNTIME_ROLE}")
        )

    op.execute(
        sa.text(
            f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {RUNTIME_ROLE}"
        )
    )
    op.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {RUNTIME_ROLE}"))
    # O papel coletivo permanece caso um login de produção seja membro dele.
    # Removê-lo automaticamente poderia interromper credenciais externas.
