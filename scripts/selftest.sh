#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHONPATH=src python3 -m unittest discover -s tests -v
./deterministicFormaliser --version
./deterministicFormaliser --help >/dev/null
PYTHONPATH=src python3 scripts/eval_core.py
