from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gov_erp.domain.reports import compare_periods
from gov_erp.models import FinancialTransaction


def _previous_period(start: date, end: date) -> tuple[date, date]:
    day_count = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    return previous_end - timedelta(days=day_count - 1), previous_end


def paid_department_comparison(
    session: Session, municipality_id: str, start: date, end: date
) -> dict[str, object]:
    previous_start, previous_end = _previous_period(start, end)

    def totals(period_start: date, period_end: date) -> dict[str, Decimal]:
        rows = session.execute(
            select(FinancialTransaction.department, func.sum(FinancialTransaction.paid_amount))
            .where(
                FinancialTransaction.municipality_id == municipality_id,
                FinancialTransaction.status == "paid",
                FinancialTransaction.payment_date.between(period_start, period_end),
                FinancialTransaction.source_kind == "synthetic",
            )
            .group_by(FinancialTransaction.department)
        ).all()
        return {
            department: Decimal(amount).quantize(Decimal("0.01")) for department, amount in rows
        }

    current, previous = totals(start, end), totals(previous_start, previous_end)
    comparison = compare_periods(previous, current)
    return {
        "metric": "paid_expenses_by_department",
        "current_period": {"start": start.isoformat(), "end": end.isoformat()},
        "previous_period": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
        "departments": {
            name: {
                "previous": str(row.previous),
                "current": str(row.current),
                "absolute_change": str(row.absolute_change),
                "percentage_change": str(row.percentage_change)
                if row.percentage_change is not None
                else None,
            }
            for name, row in comparison.items()
        },
        "source": "synthetic_erp",
        "municipality_id": municipality_id,
    }
