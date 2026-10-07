import unittest
from decimal import Decimal

from gov_erp.domain.reports import compare_periods, paid_totals


class ComparePeriodsTest(unittest.TestCase):
    def test_compares_only_paid_values_and_keeps_zero_baseline_percent_undefined(self):
        previous = {"Health": Decimal("0.00"), "Education": Decimal("25.00")}
        current = {"Health": Decimal("50.00"), "Education": Decimal("30.00")}

        result = compare_periods(previous, current)

        self.assertEqual(result["Health"].absolute_change, Decimal("50.00"))
        self.assertIsNone(result["Health"].percentage_change)
        self.assertEqual(result["Education"].absolute_change, Decimal("5.00"))
        self.assertEqual(result["Education"].percentage_change, Decimal("20.00"))

    def test_rejects_negative_money_values(self):
        with self.assertRaises(ValueError):
            compare_periods({"Health": Decimal("-1.00")}, {"Health": Decimal("1.00")})

    def test_paid_totals_exclude_committed_and_canceled_rows(self):
        result = paid_totals(
            [
                {"department": "Health", "amount": "125.50", "status": "paid"},
                {"department": "Health", "amount": "200.00", "status": "committed"},
                {"department": "Health", "amount": "30.00", "status": "canceled"},
            ]
        )
        self.assertEqual(result, {"Health": Decimal("125.50")})


if __name__ == "__main__":
    unittest.main()
