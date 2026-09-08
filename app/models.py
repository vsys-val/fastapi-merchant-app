"""Entidades persistidas do catálogo, contas e avaliações."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    public_name: Mapped[str] = mapped_column("nome_publico", String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column("senha_hash", Text, nullable=False)

    products: Mapped[List["Product"]] = relationship(back_populates="responsible")
    reviews: Mapped[List["Review"]] = relationship(back_populates="author")


class Product(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_produtos_quantidade_positiva"),
        CheckConstraint("unidade IN ('g', 'ml', 'un')", name="ck_produtos_unidade"),
        CheckConstraint(
            "categoria IN ('food', 'beverages', 'cleaning', 'personal_hygiene', "
            "'household_utilities', 'other')",
            name="ck_produtos_categoria",
        ),
        Index("ix_produtos_nome", "nome"),
        Index("ix_produtos_marca", "marca"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    responsible_id: Mapped[int] = mapped_column(
        "criador_id", ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    brand: Mapped[str] = mapped_column("marca", String(80), nullable=False)
    variant: Mapped[Optional[str]] = mapped_column("variante", String(80), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(3), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(
        "codigo_barras", String(14), nullable=True, unique=True
    )
    identity_key: Mapped[str] = mapped_column(
        "chave_identidade", Text, nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        "excluido_em", DateTime(timezone=True), nullable=True
    )

    responsible: Mapped[User] = relationship(back_populates="products")
    reviews: Mapped[List["Review"]] = relationship(back_populates="product")


class Review(Base):
    __tablename__ = "avaliacoes"
    __table_args__ = (
        UniqueConstraint("usuario_id", "produto_id", name="uq_avaliacoes_usuario_produto"),
        CheckConstraint(
            "intencao_recompra IN ('yes', 'maybe', 'no')",
            name="ck_avaliacoes_intencao_recompra",
        ),
        CheckConstraint(
            "qualidade IN ('low', 'adequate', 'high')",
            name="ck_avaliacoes_qualidade",
        ),
        CheckConstraint(
            "expectativa IN ('not_met', 'met', 'exceeded')",
            name="ck_avaliacoes_expectativa",
        ),
        CheckConstraint(
            "custo_beneficio IN ('poor', 'fair', 'good')",
            name="ck_avaliacoes_custo_beneficio",
        ),
        Index("ix_avaliacoes_produto_id", "produto_id"),
        Index("ix_avaliacoes_usuario_id", "usuario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    author_id: Mapped[int] = mapped_column(
        "usuario_id", ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        "produto_id", ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    repurchase_intent: Mapped[str] = mapped_column("intencao_recompra", String(8), nullable=False)
    quality: Mapped[str] = mapped_column(String(8), nullable=False)
    expectation: Mapped[str] = mapped_column(String(10), nullable=False)
    value_for_money: Mapped[str] = mapped_column("custo_beneficio", String(5), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column("comentario", String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    author: Mapped[User] = relationship(back_populates="reviews")
    product: Mapped[Product] = relationship(back_populates="reviews")
    reasons: Mapped[List["ReviewReason"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReviewReason(Base):
    __tablename__ = "motivos_avaliacao"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "aspecto", name="uq_motivos_avaliacao_aspecto"),
        CheckConstraint(
            "aspecto IN ('taste', 'fragrance', 'texture_consistency', "
            "'effectiveness_performance', 'quantity_yield', 'ease_of_use_preparation', "
            "'packaging', 'durability_preservation', 'composition_ingredients', "
            "'safety_tolerance', 'price', 'other')",
            name="ck_motivos_aspecto",
        ),
        CheckConstraint(
            "percepcao IN ('positive', 'negative')",
            name="ck_motivos_percepcao",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    review_id: Mapped[int] = mapped_column(
        "avaliacao_id",
        ForeignKey("avaliacoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    aspect: Mapped[str] = mapped_column("aspecto", String(32), nullable=False)
    perception: Mapped[str] = mapped_column("percepcao", String(8), nullable=False)

    review: Mapped[Review] = relationship(back_populates="reasons")
