"""Adiciona eventos de uso e métricas técnicas para o painel administrativo."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_observability"
down_revision = "0006_account_verification"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "merchant_app_runtime"
TABLES = ("eventos_produto", "metricas_requisicoes")


def upgrade() -> None:
    op.create_table(
        "eventos_produto",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("nome", sa.String(length=40), nullable=False),
        sa.Column("sessao", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("propriedades", postgresql.JSONB(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_produto_criado_em", "eventos_produto", ["criado_em"])
    op.create_index(
        "ix_eventos_produto_nome_criado_em", "eventos_produto", ["nome", "criado_em"]
    )
    op.create_table(
        "metricas_requisicoes",
        sa.Column("minuto", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metodo", sa.String(length=7), nullable=False),
        sa.Column("rota", sa.String(length=120), nullable=False),
        sa.Column("classe", sa.Integer(), nullable=False),
        sa.Column("contagem", sa.Integer(), nullable=False),
        sa.Column("duracao_total_ms", sa.Float(), nullable=False),
        sa.Column("duracao_max_ms", sa.Float(), nullable=False),
        sa.Column("faixas", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.CheckConstraint("classe BETWEEN 1 AND 5", name="ck_metricas_requisicoes_classe"),
        sa.PrimaryKeyConstraint("minuto", "metodo", "rota", "classe"),
    )
    for table in TABLES:
        op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM anon;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM authenticated;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table} TO {RUNTIME_ROLE};
                        CREATE POLICY {table}_runtime_access ON public.{table}
                            FOR ALL TO {RUNTIME_ROLE} USING (true) WITH CHECK (true);
                    END IF;
                END $$
                """
            )
        )
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE};
                END IF;
            END $$
            """
        )
    )
    op.drop_constraint("ck_limites_login_escopo", "limites_login", type_="check")
    op.create_check_constraint(
        "ck_limites_login_escopo",
        "limites_login",
        "escopo IN ('account', 'ip', 'register', 'code', 'email', 'events')",
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM limites_login WHERE escopo = 'events'"))
    op.drop_constraint("ck_limites_login_escopo", "limites_login", type_="check")
    op.create_check_constraint(
        "ck_limites_login_escopo",
        "limites_login",
        "escopo IN ('account', 'ip', 'register', 'code', 'email')",
    )
    op.drop_table("metricas_requisicoes")
    op.drop_index("ix_eventos_produto_nome_criado_em", table_name="eventos_produto")
    op.drop_index("ix_eventos_produto_criado_em", table_name="eventos_produto")
    op.drop_table("eventos_produto")
