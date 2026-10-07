from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from gov_erp.auth import hash_password
from gov_erp.database import OwnerSession
from gov_erp.models import (
    DemoUser,
    FinancialTransaction,
    MunicipalAccess,
    Municipality,
    TenantDocument,
)

DATASET_VERSION = "goverp-synthetic-pr-2025-v1"
SEED_NAMESPACE = uuid.UUID("7fcb4a56-508d-4b36-9a04-cedc6aa4972b")
PROFILES = {
    "small": {"cycles": 2_000, "documents": 30},
    "intermediate": {"cycles": 10_000, "documents": 100},
    "large": {"cycles": 50_000, "documents": 300},
}
IBGE_SNAPSHOT: dict[str, object] = {}
FIXED_CITIES = [
    ("4106902", "4106902", "Curitiba", "large"),
    ("4113700", "4113700", "Londrina", "large"),
    ("4115200", "4115200", "Maringá", "intermediate"),
    ("4104808", "4104808", "Cascavel", "intermediate"),
    ("4119905", "4119905", "Ponta Grossa", "intermediate"),
    ("4108304", "4108304", "Foz do Iguaçu", "intermediate"),
    ("4109401", "4109401", "Guarapuava", "small"),
    ("4104303", "4104303", "Campo Mourão", "small"),
    ("4110706", "4110706", "Irati", "small"),
    ("4107202", "4107202", "Dois Vizinhos", "small"),
]
DEPARTMENTS = ("Saude", "Educacao", "Administracao", "Obras", "Assistencia Social")


def generate_financial_rows(municipality_id: str, count: int) -> Iterator[dict[str, object]]:
    if not municipality_id.isdigit() or count < 0:
        raise ValueError("Municipality must be an IBGE code and count must be non-negative")
    for index in range(count):
        row_id = str(uuid.uuid5(SEED_NAMESPACE, f"{DATASET_VERSION}:{municipality_id}:{index}"))
        supplier_group = (index // 2) % 80
        amount = Decimal(100 + ((index // 2) % 700)).quantize(Decimal("0.01"))
        status = "canceled" if index % 31 == 0 else "committed" if index % 37 == 0 else "paid"
        invoice = f"SYN-{municipality_id}-{index:08d}"
        if index > 0 and index % 500 == 251:
            invoice = f"SYN-{municipality_id}-{index - 1:08d}"
        month = 1 + index % 12
        payment_date = date(2025, month, 1 + (index // 12) % 28)
        committed = amount if status != "canceled" else Decimal("0.00")
        liquidated = committed if status == "paid" else Decimal("0.00")
        paid = amount if status == "paid" else Decimal("0.00")
        yield {
            "id": row_id,
            "municipality_id": municipality_id,
            "department": DEPARTMENTS[index % len(DEPARTMENTS)],
            "supplier": f"Fornecedor sintetico {supplier_group + 1:03d}",
            "supplier_document": f"SYN{municipality_id[-4:]}{supplier_group:08d}",
            "invoice_reference": invoice,
            "committed_amount": committed,
            "liquidated_amount": liquidated,
            "paid_amount": paid,
            "status": status,
            "payment_date": payment_date,
            "installment_group": str(
                uuid.uuid5(SEED_NAMESPACE, f"installment:{municipality_id}:{index // 2}")
            ),
            "reversal_of": None,
            "source_kind": "synthetic",
        }


def fetch_parana_cities() -> list[tuple[str, str, str, str]]:
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios"
    response = httpx.get(url, timeout=20)
    response.raise_for_status()
    raw = response.content
    payload = json.loads(raw)
    if not isinstance(payload, list) or len(payload) != 399:
        raise RuntimeError("IBGE did not return the expected list of Paraná municipalities")
    digest = hashlib.sha256(raw).hexdigest()
    snapshot_dir = Path("data/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"ibge-parana-municipalities-{digest[:12]}.json"
    snapshot_path.write_bytes(raw)
    metadata = {
        "source_url": url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": digest,
        "municipality_count": len(payload),
    }
    snapshot_path.with_suffix(".manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    IBGE_SNAPSHOT.update(metadata)
    return [(str(item["id"]), str(item["id"]), item["nome"], "small") for item in payload[:100]]


def _document(
    city_id: str, title: str, body: str, source_url: str, kind: str, access: str, *, verified=False
):
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    document_id = str(uuid.uuid5(SEED_NAMESPACE, f"document:{city_id}:{title}"))
    return {
        "id": document_id,
        "municipality_id": city_id,
        "title": title,
        "body": body,
        "source_url": source_url,
        "source_kind": kind,
        "source_hash": digest,
        "access_class": access,
        "valid_from": None,
        "valid_until": None,
        "vigency_verified": verified,
    }


def documents_for_city(city_id: str, name: str, count: int) -> list[dict[str, object]]:
    service = _document(
        city_id,
        "Catalogo demonstrativo de servicos ao cidadao",
        f"Conteudo sintetico de demonstracao para {name}, no Parana. Este texto nao e um catalogo oficial. "
        "A solicitacao deve ser confirmada nos canais oficiais do municipio antes de qualquer uso.",
        "https://example.invalid/goverp/synthetic-service-catalog",
        "synthetic",
        "public",
    )
    manual = _document(
        city_id,
        "Manual demonstrativo do ERP sintetico",
        "Os dados da base sao inteiramente sinteticos. Despesas pagas, empenhadas e liquidadas sao campos distintos. "
        "Use a memoria de calculo e o identificador da consulta para conferir os relatorios.",
        "https://example.invalid/goverp/synthetic-erp-manual",
        "synthetic",
        "staff",
    )
    records = [service, manual]
    if city_id == "4106902":
        records.extend(
            [
                _document(
                    city_id,
                    "Curitiba 156: iluminacao publica",
                    "Fonte municipal consultada em 2026-10-07. O portal informa que pedidos de manutencao da "
                    "iluminacao publica, como troca de lampadas e inspecao das luminarias, sao recebidos pela Central 156. "
                    "Confirme os requisitos atualizados na pagina oficial antes de registrar a solicitacao.",
                    "https://156.curitiba.pr.gov.br/Servico/Ilumina%C3%A7%C3%A3o-p%C3%BAblica/58/Veja-todos-tipos-servicos-para-atender-cidadao-da-central-156-prefeitura-curitiba",
                    "official",
                    "public",
                ),
                _document(
                    city_id,
                    "Curitiba: Lei Complementar 40 de 2001, ISS (trecho de referencia)",
                    "A pagina oficial informa que a Lei Complementar Municipal 40 de 2001 dispoe sobre tributos municipais. "
                    "O artigo 2 descreve a hipotese de incidencia do ISS e remete a lista de servicos do Anexo I. "
                    "A lei possui alteracoes. Este recorte nao prova a redacao vigente para um caso ou data especifica.",
                    "https://legisladocexterno.curitiba.pr.gov.br/VisualizarHTML.aspx?id=41",
                    "official",
                    "staff",
                ),
            ]
        )
    for index in range(max(0, count - len(records))):
        records.append(
            _document(
                city_id,
                f"Procedimento de teste sintetico {index + 1:03d}",
                f"Documento gerado para teste de busca e isolamento do GovERP AI Lab na demonstracao de {name}. "
                f"Identificador de exemplo {index + 1:03d}; nao possui efeito administrativo.",
                "https://example.invalid/goverp/generated-test-document",
                "synthetic",
                "public" if index % 3 == 0 else "staff",
            )
        )
    return records


def load(mode: str = "functional") -> None:
    cities = FIXED_CITIES if mode == "functional" else fetch_parana_cities()
    user_specs = [
        (
            "demo-manager-curitiba",
            "gestor@demo.pr.gov.br",
            "Gestor demonstrativo",
            "manager",
            ["4106902"],
        ),
        (
            "demo-auditor-pr",
            "auditor@demo.pr.gov.br",
            "Controle interno demonstrativo",
            "auditor",
            [c[0] for c in cities],
        ),
        (
            "demo-citizen-pr",
            "cidadao@demo.pr.gov.br",
            "Atendimento demonstrativo",
            "citizen",
            [c[0] for c in cities],
        ),
    ]
    with OwnerSession.begin() as session:
        for city_id, ibge_id, city_name, profile in cities:
            session.execute(
                insert(Municipality)
                .values(
                    id=city_id, ibge_code=ibge_id, name=city_name, uf="PR", workload_profile=profile
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
        for user_id, email, display_name, role, _ in user_specs:
            session.execute(
                insert(DemoUser)
                .values(
                    id=user_id,
                    email=email,
                    display_name=display_name,
                    password_hash=hash_password("Local-Demo-Only-2026!"),
                    active=True,
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
        session.flush()
        for user_id, _, _, role, scopes in user_specs:
            for city_id in scopes:
                session.execute(
                    insert(MunicipalAccess)
                    .values(user_id=user_id, municipality_id=city_id, role=role)
                    .on_conflict_do_nothing(index_elements=["user_id", "municipality_id"])
                )

        for city_id, _, city_name, profile in cities:
            profile_name = profile if mode == "functional" else "small"
            count = int(PROFILES[profile_name]["cycles"])
            existing = (
                session.scalar(
                    select(func.count())
                    .select_from(FinancialTransaction)
                    .where(FinancialTransaction.municipality_id == city_id)
                )
                or 0
            )
            if existing < count:
                batch = []
                for row in generate_financial_rows(city_id, count):
                    batch.append(row)
                    if len(batch) >= 2_000:
                        session.execute(
                            insert(FinancialTransaction).on_conflict_do_nothing(
                                index_elements=["id"]
                            ),
                            batch,
                        )
                        batch.clear()
                if batch:
                    session.execute(
                        insert(FinancialTransaction).on_conflict_do_nothing(index_elements=["id"]),
                        batch,
                    )

            document_count = int(PROFILES[profile_name]["documents"])
            docs_exist = (
                session.scalar(
                    select(func.count())
                    .select_from(TenantDocument)
                    .where(TenantDocument.municipality_id == city_id)
                )
                or 0
            )
            if docs_exist == 0:
                docs = documents_for_city(city_id, city_name, document_count)
                for start in range(0, len(docs), 100):
                    session.execute(
                        insert(TenantDocument).on_conflict_do_nothing(index_elements=["id"]),
                        docs[start : start + 100],
                    )

    totals = {profile: sum(1 for city in cities if city[3] == profile) for profile in PROFILES}
    summary = {
        "dataset_version": DATASET_VERSION,
        "municipality_count": len(cities),
        "cycles_per_profile": {profile: PROFILES[profile]["cycles"] for profile in PROFILES},
        "municipalities_per_profile": totals,
        "synthetic_rows_total": sum(PROFILES[p]["cycles"] * n for p, n in totals.items()),
        "model_calls": 0,
        "official_snapshot": "https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios",
    }
    if IBGE_SNAPSHOT:
        summary["snapshot_sha256"] = IBGE_SNAPSHOT["sha256"]
        summary["snapshot_retrieved_at"] = IBGE_SNAPSHOT["retrieved_at"]
    print(json.dumps(summary, ensure_ascii=True, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("functional", "benchmark-100"), default="functional")
    mode = "functional" if parser.parse_args().mode == "functional" else "benchmark-100"
    load(mode)


if __name__ == "__main__":
    main()
