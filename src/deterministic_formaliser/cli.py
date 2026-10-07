from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .backend_manager import parse_text
from .adapters import BackendError
from .cnl import render_cnl

PARSERS = ["stanza", "spacy", "udpipe", "trankit"]


def _read_text(args) -> str:
    if args.text is not None:
        return args.text
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        raise SystemExit("No input text. Use --text, --file, or pipe text on stdin.")
    return sys.stdin.read()


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="deterministicFormaliser",
        description="Deterministic analysis/CNL frontend over Stanza, spaCy, UDPipe and Trankit.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--parser", choices=PARSERS + ["all"], default="stanza",
                    help="NLP backend. 'all' runs all four backends on the same text.")
    ap.add_argument("--mode", "--output", dest="mode", choices=["analysis", "cnl"], default="cnl")
    ap.add_argument("--lang", default="en", help="Language code, default: en")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", help="Input text")
    src.add_argument("--file", help="UTF-8 input file")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    ap.add_argument("--strict", action="store_true",
                    help="Reject CNL if deterministic coverage is below --min-coverage")
    ap.add_argument("--min-coverage", type=float, default=0.90)
    ap.add_argument("--diagnostics", action="store_true", help="Print CNL coverage/warnings to stderr")
    ap.add_argument("--require-all", action="store_true", help="With --parser all, fail if any backend fails")
    ap.add_argument("--gpu", action="store_true", help="Allow a backend to use GPU (default is CPU)")
    ap.add_argument("--backend-python", help="Python interpreter for a single selected backend")
    ap.add_argument("--spacy-model", help="Override spaCy model, e.g. en_core_web_sm")
    ap.add_argument("--udpipe-model", help="Path to a .udpipe model")
    ap.add_argument("--trankit-cache", help="Trankit cache directory")
    return ap


def _one(parser_name: str, text: str, args):
    doc = parse_text(
        parser_name, text, lang=args.lang, backend_python=args.backend_python,
        spacy_model=args.spacy_model, udpipe_model=args.udpipe_model,
        trankit_cache=args.trankit_cache, gpu=args.gpu,
    )
    if args.mode == "analysis":
        return doc.to_dict()
    return render_cnl(doc, strict=args.strict, min_coverage=args.min_coverage).to_dict()


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.parser == "all" and args.backend_python:
        print("--backend-python is only valid for a single parser", file=sys.stderr)
        return 2
    text = _read_text(args)
    selected = PARSERS if args.parser == "all" else [args.parser]
    results = {}
    failures = {}
    for name in selected:
        try:
            results[name] = _one(name, text, args)
        except Exception as e:
            failures[name] = f"{type(e).__name__}: {e}"
            if args.parser != "all":
                print(failures[name], file=sys.stderr)
                return 2

    if args.parser == "all":
        if args.json or args.mode == "analysis":
            print(json.dumps({"results": results, "errors": failures}, ensure_ascii=False, indent=2))
        else:
            for name in selected:
                print(f"=== {name} ===")
                if name in results:
                    print(results[name]["cnl"])
                    print(f"# coverage={results[name]['coverage']:.3f}")
                    if results[name].get("warnings"):
                        for w in results[name]["warnings"]:
                            print(f"# warning: {w}")
                else:
                    print(f"# ERROR: {failures[name]}")
        if args.require_all and failures:
            return 2
        return 0 if results else 2

    result = results[args.parser]
    if args.json or args.mode == "analysis":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["cnl"])
        if args.diagnostics:
            print(f"coverage={result['coverage']:.3f}", file=sys.stderr)
            for w in result.get("warnings", []):
                print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
