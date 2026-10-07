"""Regression inputs captured from real spaCy/UDPipe models, not invented parses."""
import json
from pathlib import Path
import unittest

from deterministic_formaliser.schema import Document
from deterministic_formaliser.cnl import render_cnl

EXPECTED = {
    "negation": "ASSERT: John did not send the report.",
    "modal_negation": "ASSERT: Alice may not approve the proposal.",
    "prohibition": "ASSERT: Alice must not open the door.",
    "passive": "ASSERT: The report was approved by Mary.",
    "embedded_question": "ASSERT: I know why John left.",
    "imperative": "COMMAND: Send the report to Mary.",
    "temporal_once": "ASSERT: John left once Mary arrived.",
    "infinitive": "ASSERT: John wants to leave.",
    "object_control": "ASSERT: Mary persuaded John to leave.",
    "quantifier": "ASSERT: Not every student passed the exam.",
}


class LiveRegressionTests(unittest.TestCase):
    def test_recorded_real_analyses(self):
        rows = json.loads((Path(__file__).parent / "fixtures/live_analyses.json").read_text())
        for row in rows:
            if row["case"] not in EXPECTED:
                continue
            with self.subTest(parser=row["parser"], case=row["case"]):
                doc = Document.from_dict(row)
                # Older spaCy adapter included whitespace. Current adapter omits it.
                for sentence in doc.sentences:
                    sentence.tokens = [t for t in sentence.tokens if t.upos != "SPACE"]
                result = render_cnl(doc, strict=True)
                self.assertEqual(result.cnl, EXPECTED[row["case"]])
                self.assertEqual(result.coverage, 1.0)

    def test_empty_analysis_is_not_success(self):
        with self.assertRaisesRegex(ValueError, "empty dependency"):
            render_cnl(Document("broken", "en", "John left.", []), strict=True)

    def test_invalid_threshold(self):
        for value in [-0.1, 1.1, float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_cnl(Document("test", "en", "", []), min_coverage=value)

    def test_unsupported_cnl_language(self):
        with self.assertRaisesRegex(ValueError, "English only"):
            render_cnl(Document("test", "ro", "", []))
