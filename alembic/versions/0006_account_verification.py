"""Adiciona confirmação de conta, recuperação de senha e limites de cadastro."""

from alembic import op
import sqlalchemy as sa

revision = "0006_account_verification"
down_revision = "0005_runtime_role"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "merchant_app_runtime"


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("email_verificado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column("versao_sessao", sa.Integer(), server_default="0", nullable=False),
    )
    # Contas anteriores à confirmação por e-mail continuam ativas.
    op.execute(sa.text("UPDATE usuarios SET email_verificado_em = criado_em"))

    op.create_table(
        "codigos_verificacao",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("finalidade", sa.String(length=20), nullable=False),
        sa.Column("codigo_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "finalidade IN ('email_verification', 'password_reset')",
            name="ck_codigos_verificacao_finalidade",
        ),
        sa.CheckConstraint("tentativas >= 0", name="ck_codigos_verificacao_tentativas"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id", "finalidade"),
    )
    op.execute(sa.text('ALTER TABLE "codigos_verificacao" ENABLE ROW LEVEL SECURITY'))
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.codigos_verificacao FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL PRIVILEGES ON TABLE public.codigos_verificacao FROM authenticated;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                    GRANT SELECT, INSERT, UPDATE, DELETE
                        ON TABLE public.codigos_verificacao TO {RUNTIME_ROLE};
                    CREATE POLICY codigos_verificacao_runtime_access
                        ON public.codigos_verificacao FOR ALL TO {RUNTIME_ROLE}
                        USING (true) WITH CHECK (true);
                END IF;
            END $$
            """
        )
    )

    op.drop_constraint("ck_limites_login_escopo", "limites_login", type_="check")
    op.create_check_constraint(
        "ck_limites_login_escopo",
        "limites_login",
        "escopo IN ('account', 'ip', 'register', 'code', 'email')",
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM limites_login WHERE escopo NOT IN ('account', 'ip')")
    )
    op.drop_constraint("ck_limites_login_escopo", "limites_login", type_="check")
    op.create_check_constraint(
        "ck_limites_login_escopo", "limites_login", "escopo IN ('account', 'ip')"
    )
    op.drop_table("codigos_verificacao")
    # Sem a coluna, contas pendentes passariam a entrar sem confirmação.
    op.execute(sa.text("DELETE FROM usuarios WHERE email_verificado_em IS NULL"))
    op.drop_column("usuarios", "versao_sessao")
    op.drop_column("usuarios", "email_verificado_em")
    op.drop_column("usuarios", "criado_em")
