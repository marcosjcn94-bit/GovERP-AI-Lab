from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from gov_erp.domain.reports import _money


@dataclass(frozen=True, slots=True)
class DuplicateFinding:
    record_ids: tuple[str, ...]
    document: str
    vendor: str
    amount: Decimal
    rule: str = "duplicate_document_vendor_amount"


def find_possible_duplicates(rows: Iterable[Mapping[str, object]]) -> list[DuplicateFinding]:
    """Find exact duplicate paid records; this signals review, not fraud."""
    grouped: dict[tuple[str, str, Decimal], list[Mapping[str, object]]] = {}
    for row in rows:
        if str(row["status"]).lower() != "paid":
            continue
        document = " ".join(str(row["document"]).casefold().split())
        vendor = " ".join(str(row["vendor"]).casefold().split())
        if not document or not vendor:
            continue
        key = (document, vendor, _money(row["amount"]))
        grouped.setdefault(key, []).append(row)

    findings: list[DuplicateFinding] = []
    for (document, vendor, amount), matches in sorted(grouped.items()):
        if len(matches) < 2:
            continue
        ids = tuple(sorted(str(row["id"]) for row in matches))
        findings.append(DuplicateFinding(ids, document, vendor, amount))
    return findings
