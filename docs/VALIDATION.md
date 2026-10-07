# Validation record

Date: 2026-10-07. All four real English models were installed and exercised on CPU.

| Backend | Installed stack |
|---|---|
| Stanza | Python 3.11.17, stanza 1.15.0, torch 2.14.1+cpu |
| spaCy | Python 3.11.17, spaCy 3.8.16, en_core_web_sm 3.8.0 |
| UDPipe | Python 3.11.17, ufal.udpipe 1.4.0.1, English-EWT UD 2.5 |
| Trankit | Python 3.11.17, source commit 54e863327391262cf72f6adc1b0ff104e972a1dc (1.1.2), adapters 0.1.2, transformers 4.36.2, torch 2.0.1+cpu, numpy 1.26.4 |

The system Python is 3.14.6; backend environments deliberately use 3.11. Full package versions are embedded in the frozen benchmark analysis files.

- 22 unittest methods passed, including 52 real-analysis benchmark subcases and 20 earlier live-regression subcases.
- Five core exact regression cases passed.
- All 1,600 archived NL/CNL results reproduced exactly from frozen analyses and six renderer snapshots; hashes and recorded outputs were checked.
- Missing-backend smoke returned exit status 1; the real four-backend smoke returned 0.
- `pip check` passed in all four backend environments.
- `scripts/smoke_live.sh` completed analysis and CNL execution with all four actual models.
- 80 authored inputs were parsed independently by each backend: 320 real case analyses, no simulated NLP outputs.
- 60 development cases were rendered at baseline and after five revisions; 20 holdout cases were rendered at baseline and final revision only after tuning was complete.
- Final holdout qualitative success: Stanza 15/20, spaCy 15/20, UDPipe 17/20, Trankit 15/20. See [the benchmark report](BENCHMARK.md) for criteria, failures and evaluator limitations.

The live smoke test now propagates failures. Backend interpreter selection no longer confuses a virtual environment symlink with the main Python environment. A successful smoke test demonstrates execution, not semantic correctness.

`.venvs/`, downloaded model paths, temporary downloads, caches and `artifacts/` are git-ignored. The small authored benchmark, compressed analyses, renderer snapshots and judgments are retained for review and reproducibility. Models are not redistributed.
