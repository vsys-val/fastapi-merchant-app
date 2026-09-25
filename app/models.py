"""Entidades persistidas do catálogo, contas e avaliações."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
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
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

from app.validation import identity_text


class Base(DeclarativeBase):
    pass


# Tipos nativos no PostgreSQL; JSON genérico nos testes que usam SQLite.
JsonObject = JSON().with_variant(JSONB(), "postgresql")
IntegerList = JSON().with_variant(ARRAY(Integer), "postgresql")


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    public_name: Mapped[str] = mapped_column("nome_publico", String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column("senha_hash", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Null enquanto o e-mail não foi confirmado; contas pendentes não entram.
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        "email_verificado_em", DateTime(timezone=True), nullable=True
    )
    # Incrementada na troca de senha; tokens com versão anterior deixam de valer.
    session_version: Mapped[int] = mapped_column(
        "versao_sessao", Integer, nullable=False, default=0, server_default="0"
    )

    products: Mapped[List["Product"]] = relationship(back_populates="responsible")
    reviews: Mapped[List["Review"]] = relationship(back_populates="author")


class LoginAttempt(Base):
    """Contador compartilhado entre workers para limitar operações sensíveis."""

    __tablename__ = "limites_login"
    __table_args__ = (
        CheckConstraint(
            "escopo IN ('account', 'ip', 'register', 'code', 'email', 'events')",
            name="ck_limites_login_escopo",
        ),
        CheckConstraint("tentativas > 0", name="ck_limites_login_tentativas_positivas"),
    )

    scope: Mapped[str] = mapped_column("escopo", String(8), primary_key=True)
    key_hash: Mapped[str] = mapped_column("chave_hash", String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column("tentativas", Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        "janela_iniciada_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VerificationCode(Base):
    """Código de uso único; só o HMAC é armazenado, nunca o código em si."""

    __tablename__ = "codigos_verificacao"
    __table_args__ = (
        CheckConstraint(
            "finalidade IN ('email_verification', 'password_reset')",
            name="ck_codigos_verificacao_finalidade",
        ),
        CheckConstraint("tentativas >= 0", name="ck_codigos_verificacao_tentativas"),
    )

    user_id: Mapped[int] = mapped_column(
        "usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    purpose: Mapped[str] = mapped_column("finalidade", String(20), primary_key=True)
    code_hash: Mapped[str] = mapped_column("codigo_hash", String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        "expira_em", DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column("tentativas", Integer, nullable=False, default=0)
    sent_at: Mapped[datetime] = mapped_column(
        "enviado_em", DateTime(timezone=True), nullable=False
    )


class ProductEvent(Base):
    """Evento de uso enviado pela interface; sem e-mail nem texto digitado."""

    __tablename__ = "eventos_produto"
    __table_args__ = (
        Index("ix_eventos_produto_criado_em", "criado_em"),
        Index("ix_eventos_produto_nome_criado_em", "nome", "criado_em"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(40), nullable=False)
    session_id: Mapped[str] = mapped_column("sessao", String(36), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        "usuario_id", ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    properties: Mapped[dict] = mapped_column("propriedades", JsonObject, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RequestMetric(Base):
    """Requisições agregadas por minuto, rota, método e classe de status."""

    __tablename__ = "metricas_requisicoes"
    __table_args__ = (
        CheckConstraint("classe BETWEEN 1 AND 5", name="ck_metricas_requisicoes_classe"),
    )

    minute: Mapped[datetime] = mapped_column("minuto", DateTime(timezone=True), primary_key=True)
    method: Mapped[str] = mapped_column("metodo", String(7), primary_key=True)
    route: Mapped[str] = mapped_column("rota", String(120), primary_key=True)
    status_class: Mapped[int] = mapped_column("classe", Integer, primary_key=True)
    count: Mapped[int] = mapped_column("contagem", Integer, nullable=False)
    total_ms: Mapped[float] = mapped_column("duracao_total_ms", Float, nullable=False)
    max_ms: Mapped[float] = mapped_column("duracao_max_ms", Float, nullable=False)
    # Contagens por faixa de duração; limites em app.observability.LATENCY_BUCKETS_MS.
    buckets: Mapped[list[int]] = mapped_column("faixas", IntegerList, nullable=False)


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
        Index("ix_produtos_criador_id", "criador_id"),
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
    quantity: Mapped[Decimal] = mapped_column("quantidade", Numeric(20, 3), nullable=False)
    unit: Mapped[str] = mapped_column("unidade", String(3), nullable=False)
    category: Mapped[str] = mapped_column("categoria", String(32), nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(
        "codigo_barras", String(14), nullable=True, unique=True
    )
    identity_key: Mapped[str] = mapped_column(
        "chave_identidade", Text, nullable=False, unique=True
    )
    # Nome e marca sem acentos e em minúsculas, mantidos pelo @validates abaixo,
    # para a busca filtrar e ordenar no banco (ADR-0013).
    search_name: Mapped[str] = mapped_column("nome_busca", Text, nullable=False)
    search_brand: Mapped[str] = mapped_column("marca_busca", Text, nullable=False)
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

    @validates("name")
    def _sync_search_name(self, _key: str, value: str) -> str:
        self.search_name = identity_text(value)
        return value

    @validates("brand")
    def _sync_search_brand(self, _key: str, value: str) -> str:
        self.search_brand = identity_text(value)
        return value


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
    quality: Mapped[str] = mapped_column("qualidade", String(8), nullable=False)
    expectation: Mapped[str] = mapped_column("expectativa", String(10), nullable=False)
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
