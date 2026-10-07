#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TEXT='Although John was tired, he did not send the report because Mary had not approved it yet.'
status=0
for backend in stanza spacy udpipe trankit; do
  echo
  echo "=== $backend / analysis ==="
  ./deterministicFormaliser --parser "$backend" --mode analysis --text "$TEXT" || status=1
  echo "=== $backend / cnl ==="
  ./deterministicFormaliser --parser "$backend" --mode cnl --diagnostics --text "$TEXT" || status=1
done
exit "$status"
