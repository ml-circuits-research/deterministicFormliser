#!/usr/bin/env python3
"""Run actual NLP models; retain analyses and CNL for independent human review.

The corpus is parsed as a batch per backend to load each model only once.
Sentence alignment is checked, never assumed. No semantic score is fabricated.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from deterministic_formaliser.backend_manager import parse_text
from deterministic_formaliser.schema import Document
from deterministic_formaliser.cnl import render_cnl


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parser", choices=["all", "stanza", "spacy", "udpipe", "trankit"], default="all")
    ap.add_argument("--cases", type=Path, default=ROOT / "eval/live_cases.json")
    ap.add_argument("--output", type=Path, default=ROOT / "artifacts/live-comparison.json")
    args = ap.parse_args()
    cases = json.loads(args.cases.read_text())
    source = "\n\n".join(c["source"] for c in cases)
    report = {"cases": cases, "results": {}, "errors": {}, "semantic_evaluation": "Requires independent review; coverage is not semantic accuracy."}
    parsers = ["stanza", "spacy", "udpipe", "trankit"] if args.parser == "all" else [args.parser]
    for parser in parsers:
        print(f"Running {parser} on {len(cases)} real inputs...", flush=True)
        try:
            doc = parse_text(parser, source)
            if len(doc.sentences) != len(cases):
                raise ValueError(f"Sentence alignment failed: expected {len(cases)}, got {len(doc.sentences)}")
            rows = []
            for case, sentence in zip(cases, doc.sentences):
                if " ".join(sentence.text.split()) != " ".join(case["source"].split()):
                    raise ValueError(f"Sentence text mismatch for {case['name']}: {sentence.text!r}")
                result = render_cnl(Document(parser, doc.lang, case["source"], [sentence], doc.meta))
                rows.append({"name": case["name"], "analysis": sentence.to_dict(), **result.to_dict()})
                print(f"  {case['name']}: {result.cnl} [coverage={result.coverage:.3f}]", flush=True)
            report["results"][parser] = {"meta": doc.meta, "rows": rows}
        except Exception as exc:
            report["errors"][parser] = f"{type(exc).__name__}: {exc}"
            print(f"  ERROR: {exc}", file=sys.stderr, flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
