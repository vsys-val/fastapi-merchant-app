"""Cria o modelo relacional inicial do MVP."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("nome_publico", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("criador_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("marca", sa.String(length=80), nullable=False),
        sa.Column("variante", sa.String(length=80), nullable=True),
        sa.Column("quantidade", sa.Numeric(precision=20, scale=3), nullable=False),
        sa.Column("unidade", sa.String(length=3), nullable=False),
        sa.Column("categoria", sa.String(length=32), nullable=False),
        sa.Column("codigo_barras", sa.String(length=14), nullable=True),
        sa.Column("chave_identidade", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("excluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantidade > 0", name="ck_produtos_quantidade_positiva"),
        sa.CheckConstraint("unidade IN ('g', 'ml', 'un')", name="ck_produtos_unidade"),
        sa.CheckConstraint(
            "categoria IN ('food', 'beverages', 'cleaning', 'personal_hygiene', 'household_utilities', 'other')",
            name="ck_produtos_categoria",
        ),
        sa.ForeignKeyConstraint(["criador_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_barras"),
        sa.UniqueConstraint("chave_identidade"),
    )
    op.create_index("ix_produtos_nome", "produtos", ["nome"])
    op.create_index("ix_produtos_marca", "produtos", ["marca"])
    op.create_table(
        "avaliacoes",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("intencao_recompra", sa.String(length=8), nullable=False),
        sa.Column("qualidade", sa.String(length=8), nullable=False),
        sa.Column("expectativa", sa.String(length=10), nullable=False),
        sa.Column("custo_beneficio", sa.String(length=5), nullable=False),
        sa.Column("comentario", sa.String(length=1000), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("intencao_recompra IN ('yes', 'maybe', 'no')", name="ck_avaliacoes_intencao_recompra"),
        sa.CheckConstraint("qualidade IN ('low', 'adequate', 'high')", name="ck_avaliacoes_qualidade"),
        sa.CheckConstraint("expectativa IN ('not_met', 'met', 'exceeded')", name="ck_avaliacoes_expectativa"),
        sa.CheckConstraint("custo_beneficio IN ('poor', 'fair', 'good')", name="ck_avaliacoes_custo_beneficio"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "produto_id", name="uq_avaliacoes_usuario_produto"),
    )
    op.create_index("ix_avaliacoes_produto_id", "avaliacoes", ["produto_id"])
    op.create_index("ix_avaliacoes_usuario_id", "avaliacoes", ["usuario_id"])
    op.create_table(
        "motivos_avaliacao",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("aspecto", sa.String(length=32), nullable=False),
        sa.Column("percepcao", sa.String(length=8), nullable=False),
        sa.CheckConstraint(
            "aspecto IN ('taste', 'fragrance', 'texture_consistency', 'effectiveness_performance', 'quantity_yield', 'ease_of_use_preparation', 'packaging', 'durability_preservation', 'composition_ingredients', 'safety_tolerance', 'price', 'other')",
            name="ck_motivos_aspecto",
        ),
        sa.CheckConstraint("percepcao IN ('positive', 'negative')", name="ck_motivos_percepcao"),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("avaliacao_id", "aspecto", name="uq_motivos_avaliacao_aspecto"),
    )


def downgrade() -> None:
    op.drop_table("motivos_avaliacao")
    op.drop_index("ix_avaliacoes_usuario_id", table_name="avaliacoes")
    op.drop_index("ix_avaliacoes_produto_id", table_name="avaliacoes")
    op.drop_table("avaliacoes")
    op.drop_index("ix_produtos_marca", table_name="produtos")
    op.drop_index("ix_produtos_nome", table_name="produtos")
    op.drop_table("produtos")
    op.drop_table("usuarios")
