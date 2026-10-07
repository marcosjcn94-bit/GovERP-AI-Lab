import unittest
from decimal import Decimal

from gov_erp.seed import PROFILES, generate_financial_rows


class SyntheticDataTest(unittest.TestCase):
    def test_same_municipality_and_count_produce_identical_versioned_rows(self):
        first = list(generate_financial_rows("4106902", 3))
        second = list(generate_financial_rows("4106902", 3))
        self.assertEqual(first, second)
        self.assertEqual(first[0]["municipality_id"], "4106902")
        self.assertEqual(first[0]["source_kind"], "synthetic")
        self.assertIsInstance(first[0]["paid_amount"], Decimal)

    def test_city_profiles_are_explicit_and_scale_is_tenfold_per_city(self):
        self.assertEqual(PROFILES["small"], {"cycles": 2_000, "documents": 30})
        self.assertEqual(PROFILES["intermediate"], {"cycles": 10_000, "documents": 100})
        self.assertEqual(PROFILES["large"], {"cycles": 50_000, "documents": 300})
