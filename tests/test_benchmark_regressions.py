"""Specific semantic regressions, using frozen outputs of all four real parsers."""
import gzip
import json
from pathlib import Path
import unittest

from deterministic_formaliser.cnl import render_cnl
from deterministic_formaliser.schema import Document

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "d04": "ASSERT: The technician may not be available tomorrow.",
    "d15": "COMMAND: Do not open the attachment unless you recognize the sender.",
    "d26": "ASSERT: The technician has inspected and repaired the faulty pump.",
    "d27": "ASSERT: The tenant did not sign or return the agreement.",
    "d28": "ASSERT: The engineer who inspected the bridge recommended an immediate closure.",
    "d29": "ASSERT: My brother, who lives in Rome, will visit us next week.",
    "d37": "EXPRESS: Ouch!",
    "d38": "GREET: Hello, Maria!",
    "d40": "EXCLAIM: What a wonderful surprise!",
    "d42": 'ASSERT: Maria said "Do not delete the file."',
    "d44": "ASK CONFIRM: You have received the package; TAG: haven't you.",
    "d46": "REQUEST: Two coffees, please.",
    "d56": "ASSERT: Neither the manager nor the assistant knew where the keys were.",
}


class BenchmarkRegressionTests(unittest.TestCase):
    def test_semantic_regressions_across_real_parsers(self):
        for parser in ["stanza", "spacy", "udpipe", "trankit"]:
            raw = gzip.decompress((ROOT / f"eval/benchmark/{parser}-dev-analyses.json.gz").read_bytes())
            for row in json.loads(raw)["rows"]:
                case = row["case"]["id"]
                if case not in EXPECTED:
                    continue
                with self.subTest(parser=parser, case=case):
                    output = render_cnl(Document.from_dict(row["document"]))
                    self.assertEqual(output.cnl, EXPECTED[case])

    def test_unparsed_proposition_is_explicit_fragment(self):
        raw = gzip.decompress((ROOT / "eval/benchmark/udpipe-dev-analyses.json.gz").read_bytes())
        doc = Document.from_dict(json.loads(raw)["rows"][0]["document"])
        result = render_cnl(doc)
        self.assertTrue(result.cnl.startswith("FRAGMENT:"))
        self.assertTrue(any("no main predicate" in w for w in result.warnings))
