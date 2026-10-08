import unittest

from pydantic import ValidationError

from gov_erp.schemas import AssistantRequest, ReviewRequest


class UserInputSchemaTest(unittest.TestCase):
    def test_assistant_request_trims_question_and_rejects_whitespace(self):
        self.assertEqual(
            AssistantRequest(question="  ISS em Curitiba?  ").question, "ISS em Curitiba?"
        )
        with self.assertRaises(ValidationError):
            AssistantRequest(question="   ")

    def test_review_request_requires_a_meaningful_trimmed_note(self):
        self.assertEqual(
            ReviewRequest(decision="confirmed", note="  Revisado e conferido.  ").note,
            "Revisado e conferido.",
        )
        with self.assertRaises(ValidationError):
            ReviewRequest(decision="confirmed", note=" " * 12)
