"""Protege a tabela técnica do Alembic no schema público do Supabase."""

from alembic import op
import sqlalchemy as sa

revision = "0003_secure_alembic"
down_revision = "0002_product_owner_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM authenticated;
                END IF;
            END $$
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    GRANT ALL PRIVILEGES ON TABLE public.alembic_version TO anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    GRANT ALL PRIVILEGES ON TABLE public.alembic_version TO authenticated;
                END IF;
            END $$
            """
        )
    )
    op.execute(sa.text("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY"))
