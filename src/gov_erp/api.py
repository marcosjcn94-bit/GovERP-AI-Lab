from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from psycopg import OperationalError as PsycopgOperationalError
from psycopg_pool import ConnectionPool
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from gov_erp.auth import (
    SessionClaims,
    create_session_token,
    verify_password,
    verify_session_token,
)
from gov_erp.database import AppSession, OwnerSession, tenant_session
from gov_erp.domain.audit import find_possible_duplicates
from gov_erp.models import (
    AssistantRun,
    AuditFinding,
    DemoSession,
    DemoUser,
    FinancialTransaction,
    MunicipalAccess,
    Municipality,
    PublicRankingSnapshot,
    TenantDocument,
)
from gov_erp.observability import (
    configure_observability,
    record_audit_run,
    record_http_request,
    record_model_outcome,
)
from gov_erp.schemas import AssistantRequest, LoginRequest, ReviewRequest
from gov_erp.services.explanations import compose_explanation
from gov_erp.services.reports import paid_department_comparison
from gov_erp.settings import settings
from gov_erp.workflow import build_question_graph

COOKIE_NAME = "goverp_session"
SESSION_MAX_AGE = 3600
DEMO_PASSWORD = "Local-Demo-Only-2026!"
logger = logging.getLogger(__name__)


def csrf_token_for(session_token: str, secret: str) -> str:
    return hmac.new(secret.encode(), ("csrf:" + session_token).encode(), hashlib.sha256).hexdigest()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(settings.session_secret.encode()) < 32:
        raise RuntimeError(
            "GOVERP_SESSION_SECRET must be at least 32 bytes; run scripts/bootstrap.ps1"
        )
    with AppSession() as session:
        session.execute(text("SELECT 1"))
    app_dsn = settings.app_database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    pool = ConnectionPool(
        app_dsn,
        kwargs={"autocommit": True, "prepare_threshold": 0, "connect_timeout": 3},
        timeout=5,
        min_size=1,
        max_size=4,
        check=ConnectionPool.check_connection,
    )
    from langgraph.checkpoint.postgres import PostgresSaver

    checkpointer = PostgresSaver(pool)
    app.state.checkpointer = checkpointer
    app.state.question_graph = build_question_graph(checkpointer)
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="GovERP AI Lab", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
configure_observability(app)


@app.middleware("http")
async def correlate_request(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
    except (OperationalError, PsycopgOperationalError):
        status = 503
        response = JSONResponse({"detail": "Banco local indisponivel"}, status_code=status)
    except Exception:  # noqa: BLE001 - HTTP boundary must sanitize and measure every failure.
        response = JSONResponse({"detail": "Falha interna na requisicao"}, status_code=status)
    response.headers["X-Request-ID"] = request_id
    route = request.scope.get("route")
    route_path = route.path if route else "unmatched"
    duration = max(0, time.perf_counter() - started)
    record_http_request(request.method, route_path, status, duration)
    span = trace.get_current_span()
    span.set_attribute("goverp.request_id", request_id)
    span.set_attribute("http.response.status_code", status)
    logger.info(
        "http_request_completed",
        extra={
            "request_id": request_id,
            "http_method": request.method,
            "http_route": route_path,
            "http_status_code": status,
            "run_id": getattr(request.state, "run_id", ""),
            "trace_id": format(span.get_span_context().trace_id, "032x"),
            "duration_ms": round(duration * 1000, 2),
        },
    )
    return response


def _claims(request: Request) -> tuple[SessionClaims, str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sessao necessaria")
    try:
        return verify_session_token(token, settings.session_secret), token
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Sessao invalida ou expirada") from exc


def get_current_context(request: Request):
    claims, _ = _claims(request)
    with tenant_session(claims.municipality_id, claims.user_id) as session:
        user = session.get(DemoUser, claims.user_id)
        municipality = session.get(Municipality, claims.municipality_id)
        access = session.scalar(
            select(MunicipalAccess).where(
                MunicipalAccess.user_id == claims.user_id,
                MunicipalAccess.municipality_id == claims.municipality_id,
            )
        )
        demo_session = session.get(DemoSession, claims.nonce)
        if (
            not user
            or not user.active
            or not municipality
            or not access
            or not demo_session
            or demo_session.revoked_at is not None
            or demo_session.expires_at <= datetime.now(UTC)
        ):
            raise HTTPException(status_code=401, detail="Sessao invalida ou expirada")
        yield {
            "claims": claims,
            "user": user,
            "municipality": municipality,
            "role": access.role,
            "db": session,
        }


CurrentContext = Annotated[dict, Depends(get_current_context)]


def require_csrf(request: Request, token: str) -> None:
    _, cookie = _claims(request)
    expected = csrf_token_for(cookie, settings.session_secret)
    supplied = request.headers.get("x-csrf-token", "")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Token CSRF invalido")


def _require_role(context: dict, *roles: str) -> None:
    if context["role"] not in roles:
        raise HTTPException(status_code=403, detail="Perfil sem permissao para esta operacao")


@app.get("/health/live")
def live():
    return {"status": "live"}


@app.get("/health/ready")
def ready():
    try:
        with AppSession() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Banco local indisponivel") from exc


@app.get("/api/public/municipalities")
def public_municipalities():
    with OwnerSession() as session:
        rows = session.scalars(select(Municipality).order_by(Municipality.name)).all()
        return [{"id": row.id, "name": row.name, "uf": row.uf} for row in rows]


@app.get("/api/public/rankings/{municipality_id}")
def public_ranking(municipality_id: Annotated[str, PathParam(pattern=r"^\d{7}$")]):
    with AppSession() as session:
        row = session.scalar(
            select(PublicRankingSnapshot)
            .where(PublicRankingSnapshot.ibge_code == municipality_id)
            .order_by(PublicRankingSnapshot.edition_year.desc())
            .limit(1)
        )
    if row is None:
        return {
            "available": False,
            "municipality_id": municipality_id,
            "message": "Esta edicao do ranking cobre municipios acima do recorte populacional publicado.",
            "source_url": "https://conteudo.clp.org.br/relatorios-tecnicos-ranking-dos-estados-e-dos-municipios",
        }
    return {
        "available": True,
        "municipality_id": row.ibge_code,
        "municipality_name": row.municipality_name,
        "uf": row.uf,
        "edition_year": row.edition_year,
        "population": row.population,
        "overall_score": str(row.overall_score),
        "overall_rank": row.overall_rank,
        "rank_change": row.rank_change,
        "pillars": row.pillar_scores,
        "source_url": row.source_url,
        "source_sha256": row.source_sha256,
        "retrieved_at": row.retrieved_at.isoformat(),
        "calculation": "published_clp_result; not recalculated by this application",
    }


@app.post("/api/auth/login")
def login(data: LoginRequest, request: Request, response: Response):
    origin = request.headers.get("origin")
    if origin and origin not in {settings.allowed_origin, "http://127.0.0.1:8000"}:
        raise HTTPException(status_code=403, detail="Origem nao permitida")
    with OwnerSession() as owner:
        user = owner.scalar(
            select(DemoUser).where(func.lower(DemoUser.email) == data.email.casefold())
        )
        valid = bool(user and user.active and verify_password(data.password, user.password_hash))
        if not valid:
            raise HTTPException(status_code=401, detail="Credenciais invalidas")
        user_id = user.id
        display_name = user.display_name

    with tenant_session(data.municipality_id, user_id) as session:
        access = session.scalar(
            select(MunicipalAccess).where(
                MunicipalAccess.user_id == user_id,
                MunicipalAccess.municipality_id == data.municipality_id,
            )
        )
        municipality = session.get(Municipality, data.municipality_id)
        if not access or not municipality:
            raise HTTPException(status_code=403, detail="Municipio nao autorizado")
        role, name = access.role, municipality.name

    token = create_session_token(
        user_id, data.municipality_id, settings.session_secret, lifetime=SESSION_MAX_AGE
    )
    claims = verify_session_token(token, settings.session_secret)
    expires = datetime.fromtimestamp(claims.expires_at, tz=UTC)
    with tenant_session(data.municipality_id, user_id) as session:
        session.add(
            DemoSession(
                id=claims.nonce,
                user_id=user_id,
                municipality_id=data.municipality_id,
                expires_at=expires,
            )
        )
    csrf = csrf_token_for(token, settings.session_secret)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/",
    )
    return {
        "user_id": user_id,
        "display_name": display_name,
        "role": role,
        "municipality_id": data.municipality_id,
        "municipality_name": name,
        "csrf_token": csrf,
    }


@app.get("/api/auth/session")
def current_session(context: CurrentContext, request: Request):
    claims, token = _claims(request)
    return {
        "user_id": context["user"].id,
        "display_name": context["user"].display_name,
        "role": context["role"],
        "municipality_id": claims.municipality_id,
        "municipality_name": context["municipality"].name,
        "csrf_token": csrf_token_for(token, settings.session_secret),
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, context: CurrentContext):
    _, token = _claims(request)
    require_csrf(request, token)
    context["db"].get(DemoSession, context["claims"].nonce).revoked_at = datetime.now(UTC)
    context["db"].flush()
    try:
        app.state.checkpointer.delete_thread(context["claims"].nonce)
    except (OSError, RuntimeError) as exc:
        logger.warning("Falha ao remover checkpoint da sessao revogada: %s", type(exc).__name__)
    response.delete_cookie(COOKIE_NAME, path="/", samesite="strict")
    return {"status": "signed_out"}


@app.get("/api/municipalities")
def allowed_municipalities(context: CurrentContext):
    rows = (
        context["db"]
        .execute(
            select(Municipality.id, Municipality.name, Municipality.uf)
            .join(MunicipalAccess, MunicipalAccess.municipality_id == Municipality.id)
            .where(MunicipalAccess.user_id == context["user"].id)
            .order_by(Municipality.name)
        )
        .all()
    )
    return [{"id": row.id, "name": row.name, "uf": row.uf} for row in rows]


@app.get("/api/reports/paid-by-department")
def report_paid_by_department(
    context: CurrentContext,
    start: date = date(2025, 10, 1),
    end: date = date(2025, 12, 31),
):
    _require_role(context, "manager", "auditor")
    if end < start or (end - start).days > 366:
        raise HTTPException(status_code=422, detail="Periodo invalido; limite de 367 dias")
    return paid_department_comparison(context["db"], context["claims"].municipality_id, start, end)


@app.get("/api/documents/search")
def document_search(
    context: CurrentContext,
    query: str = Query(min_length=3, max_length=512),
    limit: int = Query(default=5, ge=1, le=10),
):
    return {
        "sources": search_documents(context, query, limit),
        "source": "versioned_municipal_documents",
    }


@app.get("/api/audits/findings")
def list_findings(context: CurrentContext, limit: int = 100):
    _require_role(context, "manager", "auditor")
    limit = min(max(limit, 1), 200)
    rows = (
        context["db"]
        .scalars(
            select(AuditFinding)
            .where(AuditFinding.municipality_id == context["claims"].municipality_id)
            .order_by(AuditFinding.created_at.desc())
            .limit(limit)
        )
        .all()
    )
    return [
        {
            "id": item.id,
            "rule_id": item.rule_id,
            "record_ids": item.record_ids,
            "evidence": item.evidence,
            "status": item.status,
            "review_note": item.review_note,
        }
        for item in rows
    ]


@app.post("/api/audits/run")
def run_audit(context: CurrentContext, request: Request):
    _, token = _claims(request)
    require_csrf(request, token)
    _require_role(context, "manager", "auditor")
    session: Session = context["db"]
    municipality_id = context["claims"].municipality_id
    rows = session.execute(
        select(
            FinancialTransaction.id,
            FinancialTransaction.invoice_reference,
            FinancialTransaction.supplier_document,
            FinancialTransaction.paid_amount,
            FinancialTransaction.status,
        ).where(
            FinancialTransaction.municipality_id == municipality_id,
            FinancialTransaction.source_kind == "synthetic",
        )
    ).all()
    matches = find_possible_duplicates(
        [
            {
                "id": r.id,
                "document": r.invoice_reference,
                "vendor": r.supplier_document,
                "amount": str(r.paid_amount),
                "status": r.status,
            }
            for r in rows
        ]
    )
    created = 0
    for finding in matches:
        finding_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{municipality_id}:{finding.rule}:{','.join(finding.record_ids)}",
            )
        )
        if session.get(AuditFinding, finding_id) is None:
            session.add(
                AuditFinding(
                    id=finding_id,
                    municipality_id=municipality_id,
                    rule_id=finding.rule,
                    record_ids=list(finding.record_ids),
                    evidence={
                        "invoice_reference": finding.document,
                        "supplier_document": finding.vendor,
                        "amount": str(finding.amount),
                        "rule_version": "possible-duplicate-v1",
                        "source": "synthetic_erp",
                    },
                    status="pending_review",
                )
            )
            created += 1
    session.flush()
    record_audit_run(len(matches))
    return {
        "run_id": request.state.request_id,
        "examined": len(rows),
        "possible_duplicates": len(matches),
        "new_findings": created,
    }


@app.post("/api/audits/findings/{finding_id}/review")
def review_finding(finding_id: str, data: ReviewRequest, request: Request, context: CurrentContext):
    _, token = _claims(request)
    require_csrf(request, token)
    _require_role(context, "auditor")
    session: Session = context["db"]
    finding = session.scalar(
        select(AuditFinding)
        .where(
            AuditFinding.id == finding_id,
            AuditFinding.municipality_id == context["claims"].municipality_id,
        )
        .with_for_update()
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="Achado nao encontrado")
    if finding.status != "pending_review":
        raise HTTPException(status_code=409, detail="Este achado ja foi revisado")
    finding.status, finding.review_note, finding.reviewed_by = (
        data.decision,
        data.note.strip(),
        context["user"].id,
    )
    session.flush()
    return {"id": finding.id, "status": finding.status, "reviewed_by": finding.reviewed_by}


def search_documents(context: dict, query: str, limit: int = 5) -> list[dict[str, object]]:
    cleaned = " ".join(query.split())
    if not cleaned:
        return []
    db: Session = context["db"]
    tenant_id = context["claims"].municipality_id
    today = datetime.now(UTC).date()
    result = db.execute(
        select(
            TenantDocument,
            func.ts_rank_cd(
                TenantDocument.search_vector, func.websearch_to_tsquery("portuguese", cleaned)
            ).label("rank"),
        )
        .where(
            TenantDocument.municipality_id == tenant_id,
            TenantDocument.access_class.in_(
                ["public", "staff"] if context["role"] != "citizen" else ["public"]
            ),
            TenantDocument.search_vector.op("@@")(func.websearch_to_tsquery("portuguese", cleaned)),
            or_(TenantDocument.valid_from.is_(None), TenantDocument.valid_from <= today),
            or_(TenantDocument.valid_until.is_(None), TenantDocument.valid_until >= today),
        )
        .order_by(text("rank DESC"))
        .limit(min(limit, 10))
    ).all()
    return [
        {
            "title": doc.title,
            "excerpt": doc.body[:800],
            "source_url": doc.source_url,
            "source_kind": doc.source_kind,
            "source_hash": doc.source_hash,
            "vigency_verified": doc.vigency_verified,
            "valid_from": doc.valid_from.isoformat() if doc.valid_from else None,
            "valid_until": doc.valid_until.isoformat() if doc.valid_until else None,
            "score": float(rank),
        }
        for doc, rank in result
    ]


@app.post("/api/assistant")
async def assistant(data: AssistantRequest, request: Request, context: CurrentContext):
    _, token = _claims(request)
    require_csrf(request, token)
    question = data.question.strip()
    if data.start_date and data.end_date:
        start, end = data.start_date, data.end_date
    elif data.start_date or data.end_date:
        raise HTTPException(status_code=422, detail="Informe inicio e fim do periodo")
    else:
        start, end = date(2025, 10, 1), date(2025, 12, 31)
    if end < start or (end - start).days > 366:
        raise HTTPException(status_code=422, detail="Periodo invalido; limite de 367 dias")

    started = time.perf_counter()
    run_id = request.state.request_id
    graph = getattr(app.state, "question_graph", None) or build_question_graph()
    routed = graph.invoke(
        {"question": question},
        {
            "configurable": {"thread_id": context["claims"].nonce},
            "run_id": uuid.UUID(run_id),
            "metadata": {"request_id": run_id, "intent_scope": "local_demo"},
        },
    )
    intent = routed["intent"]
    if intent == "report":
        _require_role(context, "manager", "auditor")
        result: dict[str, object] = paid_department_comparison(
            context["db"], context["claims"].municipality_id, start, end
        )
        summary = "Valores calculados a partir de despesas sintéticas pagas. Consulte a tabela e a memória de cálculo."
    elif intent == "audit":
        _require_role(context, "manager", "auditor")
        rows = list_findings(context, 10)
        result = {"items": rows, "source": "synthetic_erp", "meaning": "possible_review_items_only"}
        summary = f"Há {len(rows)} achado(s) demonstrativo(s) nesta consulta; revise cada evidência antes de qualquer conclusão."
    else:
        result = {
            "sources": search_documents(context, question),
            "source": "versioned_municipal_documents",
        }
        summary = "Não encontrei fonte municipal que sustente uma resposta para esta pergunta."
        if result["sources"]:
            summary = (
                "Encontrei material para revisão; veja a fonte, o escopo e a vigência indicada."
            )

    can_explain = intent == "report" or (intent == "documents" and bool(result.get("sources")))
    explanation = await compose_explanation(intent, result, summary, settings)
    model = explanation.model
    if can_explain and explanation.status != "deterministic":
        record_model_outcome(explanation.status == "model_fallback")
    trace.get_current_span().set_attribute("goverp.run_id", run_id)
    request.state.run_id = run_id
    result_json = json.dumps(result, sort_keys=True, ensure_ascii=True, default=str)
    session = context["db"]
    session.add(
        AssistantRun(
            id=run_id,
            municipality_id=context["claims"].municipality_id,
            user_id=context["user"].id,
            intent=intent,
            question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest(),
            result_hash=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
            model_name=model,
            model_fallback=explanation.status == "model_fallback",
            elapsed_ms=max(0, round((time.perf_counter() - started) * 1000)),
        )
    )
    session.flush()
    return {
        "run_id": run_id,
        "intent": intent,
        "answer": explanation.answer,
        "explanation_status": explanation.status,
        "fallback_reason": explanation.reason,
        "model": model,
        "model_fallback": explanation.status == "model_fallback",
        "result": result,
        "human_review_required": intent == "audit" and bool(result.get("items")),
    }
