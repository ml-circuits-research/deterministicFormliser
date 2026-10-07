# deterministicFormaliser

`deterministicFormaliser` is a small experimental CLI that puts four syntactic NLP backends behind one interface:

- **Stanza**
- **spaCy**
- **UDPipe**
- **Trankit**

The tool has two outputs:

1. `analysis`: a common JSON dependency-analysis schema;
2. `cnl`: a deterministic controlled-language paraphrase intended to be compared semantically with the original NL text.

The key experimental constraint is that **the parser changes, but the CNL algorithm does not**. This makes backend comparisons meaningful.

## Architecture

```text
NL text
  |
  +--> Stanza ---+
  +--> spaCy ----+--> common analysis schema --> deterministic CNL renderer --> CNL candidate
  +--> UDPipe ---+
  +--> Trankit --+
                                                          |
                                                          +--> semantic judge (external)
```

The project does **not** claim that dependency parsing proves semantic equivalence. Instead it returns a CNL candidate plus deterministic `coverage` and unresolved material. An external semantic oracle can then compare `NL <-> CNL`.

## Quick start

The four NLP stacks are optional and are installed in separate virtual environments to avoid dependency conflicts. All four were validated with **Python 3.11**; use `--python /path/to/python3.11` when the system Python differs:

```bash
cd deterministicFormaliser
python3.11 scripts/setup_backend.py stanza --lang en
python3.11 scripts/setup_backend.py spacy --lang en
python3.11 scripts/setup_backend.py udpipe --lang en
python3.11 scripts/setup_backend.py trankit --lang en
```

Or:

```bash
DFORM_SETUP_PYTHON=python3.11 ./scripts/setup_all.sh en
```

Models and environments are **not committed**: `.gitignore` excludes `.venvs/`, downloaded models, caches and local runtime artifacts. CNL generation currently supports English; other languages can use `--mode analysis`. Setup installs CPU PyTorch and a pinned compatible Trankit stack. For GPU usage, supply a separately configured compatible environment.

### Analysis

```bash
./deterministicFormaliser \
  --parser stanza \
  --mode analysis \
  --text "John did not send the report."
```

The JSON schema contains, per token:

```json
{
  "id": 4,
  "text": "send",
  "lemma": "send",
  "upos": "VERB",
  "xpos": "...",
  "feats": {},
  "head": 0,
  "deprel": "root"
}
```

### CNL

```bash
./deterministicFormaliser \
  --parser stanza \
  --mode cnl \
  --text "John did not send the report."
```

Output:

```text
ASSERT: John did not send the report.
```

Questions and commands are explicit:

```text
ASK WHETHER: Alice did approve the proposal.
ASK WHY: Alice did reject it.
COMMAND: Send the report to Mary.
```

### Structured CNL output

```bash
./deterministicFormaliser --parser stanza --mode cnl --json --text "John left."
```

This includes:

- generated CNL;
- coverage ratio;
- consumed token IDs;
- unresolved token/dependency material;
- warnings.

### Compare all four parsers

```bash
./deterministicFormaliser --parser all --mode cnl --text "John did not send the report."
```

Use `--require-all` if a missing or failing backend should make the command fail.

## Input

Exactly one of these patterns is used:

```bash
./deterministicFormaliser --parser spacy --mode cnl --text "..."
./deterministicFormaliser --parser spacy --mode cnl --file examples/input.txt
cat examples/input.txt | ./deterministicFormaliser --parser spacy --mode cnl
```

A thin Node.js wrapper is also provided for `.mjs` workflows:

```bash
node deterministicFormaliser.mjs --parser stanza --mode cnl --text "John left."
```

## Strict mode

A fluent-looking CNL can still be wrong if important parse material was not consumed. Strict mode rejects low-coverage outputs:

```bash
./deterministicFormaliser \
  --parser stanza --mode cnl \
  --strict --min-coverage 0.95 \
  --text "..."
```

`coverage` is syntactic coverage, not semantic accuracy. It is designed as a guardrail, not as an equivalence score.

## Tests

The core renderer has no third-party dependencies:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/eval_core.py
```

Full self-test:

```bash
./scripts/selftest.sh
```

After installing backend models, run a live smoke comparison:

```bash
./scripts/smoke_live.sh
```

## Backend isolation

By default, `scripts/setup_backend.py` creates:

```text
.venvs/stanza/
.venvs/spacy/
.venvs/udpipe/
.venvs/trankit/
```

The main CLI detects these automatically. You can override an interpreter with an environment variable:

```bash
export DFORM_STANZA_PYTHON=/path/to/python
```

or, for one invocation:

```bash
./deterministicFormaliser --parser stanza --backend-python /path/to/python --mode cnl --text "..."
```

This design is deliberate: Trankit/Transformers/PyTorch and other NLP stacks can have version constraints that need not be forced into one environment.

## UDPipe note

The adapter uses the official `ufal.udpipe` Python binding (UDPipe 1.x). For English, the setup script can fetch the English-EWT UD 2.5 model into `models/udpipe/en.udpipe`. That model is external and is not part of this repository. Review its **CC BY-NC-SA** model license before commercial use. For another language, download a compatible `.udpipe` model and pass:

```bash
./deterministicFormaliser --parser udpipe --udpipe-model /path/model.udpipe --mode cnl --text "..."
```

## Important experimental limitation

This is a **deterministic syntactic formaliser**, not a complete semantic parser. Dependency parsers are useful for subject/object structure, modifiers, negation, auxiliaries, passive, basic clause links and many common constructions. They do not by themselves reliably solve quantifier scope, implicit arguments, deep coreference, pragmatics, ellipsis, lexical ambiguity or world knowledge.

For the intended experiment the correct evaluation pipeline is therefore:

```text
NL -> parser -> common analysis -> deterministic CNL
                         |
                         +-> coverage / unresolved diagnostics

NL -------------------------------> semantic equivalence judge <--- CNL
```

## Real benchmark and five improvement rounds

All four actual parsers were run on 80 authored English inputs: 60 development cases and 20 holdout cases. Five renderer-only revisions used the same frozen parser outputs. Final assistant-reviewed holdout success was Stanza 15/20, spaCy 15/20, UDPipe 17/20 and Trankit 15/20. These are small-sample qualitative judgments, not guaranteed semantic accuracy or a general ranking.

Read [the full benchmark, rates and failures](docs/BENCHMARK.md). Every input, output, verdict and renderer revision is retained under `eval/benchmark/`; model weights are not included.

```bash
python3 scripts/report_benchmark.py
# Open artifacts/benchmark/report.html to filter NL/CNL pairs and judgments.
```

CNL now retains discourse material and relative clauses, preserves shared negation/auxiliaries in coordination, and distinguishes requests, interjections, greetings, thanks, exclamations and fragments. `FRAGMENT` does not claim a successfully reconstructed proposition. Strict mode still checks token coverage, not semantic equivalence.

See `docs/ALGORITHM.md`, `docs/CNL_SPEC.md`, `docs/BACKENDS.md` and `docs/EVALUATION.md`.
