import unittest
from decimal import Decimal

from gov_erp.domain.audit import find_possible_duplicates


class PossibleDuplicateTest(unittest.TestCase):
    def test_duplicate_requires_same_document_vendor_amount_and_paid_status(self):
        rows = [
            {
                "id": "p1",
                "document": "NF-123",
                "vendor": "Vendor A",
                "amount": "50.00",
                "status": "paid",
            },
            {
                "id": "p2",
                "document": "NF-123",
                "vendor": "Vendor A",
                "amount": "50.00",
                "status": "paid",
            },
            {
                "id": "p3",
                "document": "NF-123",
                "vendor": "Vendor A",
                "amount": "50.00",
                "status": "canceled",
            },
        ]
        findings = find_possible_duplicates(rows)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].record_ids, ("p1", "p2"))
        self.assertEqual(findings[0].amount, Decimal("50.00"))

    def test_distinct_documents_are_not_flagged(self):
        rows = [
            {
                "id": "p1",
                "document": "NF-123-A",
                "vendor": "Vendor A",
                "amount": "50.00",
                "status": "paid",
            },
            {
                "id": "p2",
                "document": "NF-123-B",
                "vendor": "Vendor A",
                "amount": "50.00",
                "status": "paid",
            },
        ]
        self.assertEqual(find_possible_duplicates(rows), [])
