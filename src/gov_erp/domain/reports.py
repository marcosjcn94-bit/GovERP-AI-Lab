from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class PeriodComparison:
    previous: Decimal
    current: Decimal
    absolute_change: Decimal
    percentage_change: Decimal | None


def _money(value: object) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("Valor monetário inválido")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Valor monetário inválido") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Valor monetário deve ser finito e não negativo")
    return amount.quantize(Decimal("0.01"))


def compare_periods(
    previous: Mapping[str, object], current: Mapping[str, object]
) -> dict[str, PeriodComparison]:
    """Compare totais de despesas pagas; percentual sem base positiva é indefinido."""
    result: dict[str, PeriodComparison] = {}
    for department in sorted(previous.keys() | current.keys()):
        before = _money(previous.get(department, Decimal(0)))
        after = _money(current.get(department, Decimal(0)))
        change = (after - before).quantize(Decimal("0.01"))
        percentage = (
            (change * Decimal(100) / before).quantize(Decimal("0.01")) if before > 0 else None
        )
        result[department] = PeriodComparison(before, after, change, percentage)
    return result


def paid_totals(rows: Iterable[Mapping[str, object]]) -> dict[str, Decimal]:
    """Aggregate only paid payments. Pending, canceled and reversed rows are excluded."""
    totals: dict[str, Decimal] = {}
    for row in rows:
        department = str(row["department"]).strip()
        if not department:
            raise ValueError("Secretaria obrigatória")
        status = str(row["status"]).lower()
        if status != "paid":
            continue
        amount = _money(row["amount"])
        totals[department] = totals.get(department, Decimal("0.00")) + amount
    return {key: value.quantize(Decimal("0.01")) for key, value in sorted(totals.items())}
