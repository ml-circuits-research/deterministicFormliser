#!/usr/bin/env python3
"""Freeze real parser outputs, then compare renderer revisions on identical inputs."""
import argparse
import hashlib
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import time
import subprocess
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from deterministic_formaliser.backend_manager import _venv_python
from deterministic_formaliser.adapters import get_adapter
from deterministic_formaliser.schema import Document


def canonical(text):
    return "".join(text.split())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["parse", "render"])
    ap.add_argument("--parser", choices=["stanza", "spacy", "udpipe", "trankit"], required=True)
    ap.add_argument("--split", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--round", type=int, default=0)
    ap.add_argument("--directory", type=Path, default=ROOT / "artifacts/benchmark")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    cases = [c for c in json.loads((ROOT / "eval/benchmark_cases.json").read_text()) if c["split"] == args.split]
    args.directory.mkdir(parents=True, exist_ok=True)
    frozen = args.directory / f"{args.parser}-{args.split}-analyses.json"
    if args.phase == "parse":
        if frozen.exists() or frozen.with_suffix(".json.gz").exists():
            raise SystemExit(f"Refusing to overwrite frozen analyses: {frozen}")
        if not args.worker:
            py = _venv_python(args.parser, ROOT)
            if py is None:
                raise SystemExit(f"Missing interpreter for {args.parser}")
            return subprocess.run([str(py), str(Path(__file__).resolve()), "parse", "--parser", args.parser,
                                   "--split", args.split, "--directory", str(args.directory), "--worker"]).returncode
        start = time.monotonic()
        adapter = get_adapter(args.parser)
        results = []
        for case in cases:
            print(f"Parsing {args.parser} {case['id']}...", flush=True)
            case_start = time.monotonic()
            try:
                doc = adapter.parse(case["source"], project_root=str(ROOT))
                # Each case is sent independently; models cannot join neighboring cases.
                if canonical("".join(s.text for s in doc.sentences)) != canonical(case["source"]):
                    raise ValueError("Sentence text does not reconstruct input")
                results.append({"case": case, "document": doc.to_dict(), "seconds": time.monotonic() - case_start})
            except Exception as exc:
                results.append({"case": case, "error": f"{type(exc).__name__}: {exc}"})
        versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
        frozen.write_text(json.dumps({"parser": args.parser, "versions": versions,
                                     "parse_seconds": time.monotonic() - start, "rows": results}, indent=2) + "\n")
        print(f"Frozen {len(results)} real analyses: {frozen}")
    else:
        snapshot = args.directory / f"renderer-round-{args.round}.py"
        if not snapshot.exists():
            snapshot.write_bytes((ROOT / "src/deterministic_formaliser/cnl.py").read_bytes())
        name = "deterministic_formaliser._benchmark_renderer"
        spec = importlib.util.spec_from_file_location(name, snapshot)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        raw = frozen.read_bytes() if frozen.exists() else gzip.decompress(frozen.with_suffix(".json.gz").read_bytes())
        data = json.loads(raw)
        out = {"parser": args.parser, "split": args.split, "round": args.round,
               "analysis_sha256": hashlib.sha256(raw).hexdigest(),
               "renderer_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(), "rows": []}
        for row in data["rows"]:
            result = {"case": row["case"]}
            try:
                if "error" in row:
                    raise ValueError(row["error"])
                result["output"] = module.render_cnl(Document.from_dict(row["document"])).to_dict()
            except Exception as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
            out["rows"].append(result)
        target = args.directory / f"{args.parser}-{args.split}-round-{args.round}.json"
        target.write_text(json.dumps(out, indent=2) + "\n")
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
