#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deterministic_formaliser.adapters import get_adapter
from deterministic_formaliser.backend_manager import JSON_MARKER, ERROR_MARKER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", required=True, choices=["stanza", "spacy", "udpipe", "trankit"])
    ap.add_argument("--lang", default="en")
    ap.add_argument("--spacy-model")
    ap.add_argument("--udpipe-model")
    ap.add_argument("--trankit-cache")
    ap.add_argument("--gpu", action="store_true")
    args = ap.parse_args()
    text = sys.stdin.read()
    try:
        doc = get_adapter(args.parser).parse(
            text,
            lang=args.lang,
            spacy_model=args.spacy_model,
            udpipe_model=args.udpipe_model,
            trankit_cache=args.trankit_cache,
            gpu=args.gpu,
            project_root=str(ROOT),
        )
        print(JSON_MARKER + json.dumps(doc.to_dict(), ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as e:
        print(ERROR_MARKER + f"{type(e).__name__}: {e}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
