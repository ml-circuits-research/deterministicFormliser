#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
for backend in stanza spacy udpipe trankit; do
  echo "=== setup: $backend ==="
  "${DFORM_SETUP_PYTHON:-python3}" scripts/setup_backend.py "$backend" --lang "${1:-en}"
done
