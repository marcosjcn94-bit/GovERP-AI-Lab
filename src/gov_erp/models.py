from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Municipality(Base):
    __tablename__ = "municipalities"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    ibge_code: Mapped[str] = mapped_column(String(7), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    uf: Mapped[str] = mapped_column(String(2), default="PR")
    workload_profile: Mapped[str] = mapped_column(String(20))


class DemoUser(Base):
    __tablename__ = "demo_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(140))
    display_name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MunicipalAccess(Base):
    __tablename__ = "municipal_access"
    __table_args__ = (UniqueConstraint("user_id", "municipality_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("demo_users.id"))
    municipality_id: Mapped[str] = mapped_column(ForeignKey("municipalities.id"))
    role: Mapped[str] = mapped_column(String(20))


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    __table_args__ = (Index("ix_sessions_expiry", "expires_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("demo_users.id"), nullable=False)
    municipality_id: Mapped[str] = mapped_column(String(12), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["municipality_id"], ["municipalities.id"], name="fk_financial_transaction_tenant"
        ),
        Index("ix_financial_tenant_date", "municipality_id", "payment_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    municipality_id: Mapped[str] = mapped_column(String(12), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier: Mapped[str] = mapped_column(String(120), nullable=False)
    supplier_document: Mapped[str] = mapped_column(String(20), nullable=False)
    invoice_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    liquidated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date)
    installment_group: Mapped[str] = mapped_column(String(36), nullable=False)
    reversal_of: Mapped[str | None] = mapped_column(String(36))
    source_kind: Mapped[str] = mapped_column(String(20), default="synthetic")


class TenantDocument(Base):
    __tablename__ = "tenant_documents"
    __table_args__ = (
        Index("ix_documents_tenant_class", "municipality_id", "access_class"),
        Index("ix_documents_search", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    municipality_id: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    access_class: Mapped[str] = mapped_column(String(20), default="public")
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    vigency_verified: Mapped[bool] = mapped_column(default=False)
    search_vector = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('portuguese'::regconfig, coalesce(title, '') || ' ' || coalesce(body, ''))",
            persisted=True,
        ),
    )
    embedding = mapped_column(Vector(384), nullable=True)


class AuditFinding(Base):
    __tablename__ = "audit_findings"
    __table_args__ = (Index("ix_findings_tenant_status", "municipality_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    municipality_id: Mapped[str] = mapped_column(String(12), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(80), nullable=False)
    record_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending_review")
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("demo_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssistantRun(Base):
    __tablename__ = "assistant_runs"
    __table_args__ = (Index("ix_runs_tenant_created", "municipality_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    municipality_id: Mapped[str] = mapped_column(String(12), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("demo_users.id"), nullable=False)
    intent: Mapped[str] = mapped_column(String(20), nullable=False)
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    model_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicRankingSnapshot(Base):
    __tablename__ = "public_ranking_snapshots"
    __table_args__ = (UniqueConstraint("edition_year", "ibge_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    edition_year: Mapped[int] = mapped_column(Integer, nullable=False)
    ibge_code: Mapped[str] = mapped_column(String(7), nullable=False)
    municipality_name: Mapped[str] = mapped_column(String(120), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    overall_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_change: Mapped[int | None] = mapped_column(Integer)
    pillar_scores: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
