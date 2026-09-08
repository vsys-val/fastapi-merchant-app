"""Adiciona contadores atômicos para limitação de login.

Revision ID: 0004_login_rate_limits
Revises: 0003_secure_alembic
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_login_rate_limits"
down_revision = "0003_secure_alembic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "limites_login",
        sa.Column("escopo", sa.String(length=8), nullable=False),
        sa.Column("chave_hash", sa.String(length=64), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column(
            "janela_iniciada_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("escopo IN ('account', 'ip')", name="ck_limites_login_escopo"),
        sa.CheckConstraint("tentativas > 0", name="ck_limites_login_tentativas_positivas"),
        sa.PrimaryKeyConstraint("escopo", "chave_hash"),
    )
    op.execute(sa.text('ALTER TABLE "limites_login" ENABLE ROW LEVEL SECURITY'))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.limites_login FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.limites_login FROM authenticated;
                END IF;
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    op.drop_table("limites_login")
