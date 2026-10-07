# Evaluation design

The experiment should separate **renderer quality** from **parser quality**.

## A. Renderer regression

Input is a known dependency structure; therefore parser errors are removed from the experiment.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/eval_core.py
```

The regression set covers basic phenomena such as negation, modality, questions, commands, passive voice, copula, causal/conditional clauses and coordination.

This answers:

> Given a sufficiently correct parse, does our deterministic algorithm preserve the intended structure?

## B. Live parser comparison

After all four backends are installed:

```bash
./scripts/smoke_live.sh
```

For a real benchmark, create an NL corpus and run the same texts through:

```text
Stanza -> common IR -> CNL
spaCy  -> common IR -> CNL
UDPipe -> common IR -> CNL
Trankit -> common IR -> CNL
```

Collect at least:

| field | meaning |
|---|---|
| parser | backend |
| source | original NL |
| cnl | generated CNL |
| coverage | deterministic token coverage |
| unresolved_count | unconsumed semantic tokens |
| semantic_equivalent | independent oracle/human label |
| semantic_score | optional confidence |
| failure_tags | negation/scope/coreference/etc. |

## C. Semantic oracle

The semantic oracle must be downstream and identical for every parser. It should not be allowed to repair the CNL before scoring, otherwise parser/formaliser failures are hidden.

The intended direction is:

```text
1. small embedding model
2. small cross-encoder
3. small NLI model, bidirectional
4. deterministic semantic-difference detector
5. larger LLM only for uncertain cases
```

The central evaluation variable is not BLEU or textual similarity. It is whether the generated CNL is semantically equivalent to the original while being structurally more regular.

## D. Useful acceptance policy

A practical first policy is:

```text
accept only if:
    coverage >= 0.95
    AND unresolved_count == 0
    AND semantic_oracle == equivalent
```

The exact threshold should later be calibrated against a human-labelled benchmark.

## E. Do not compare parsers by one aggregate score only

Track failures by linguistic phenomenon. A parser that is slightly worse overall but much better on negation, conditionals or attachment may be preferable for the formalisation task.

## Completed local benchmark

See [BENCHMARK.md](BENCHMARK.md) for 80 real-model inputs, five renderer revisions, per-case assistant judgments and holdout results. `python3 scripts/report_benchmark.py` verifies archived hashes and aggregates recorded verdicts; it does not automatically judge meaning.
