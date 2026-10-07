# CNL (benchmark revision 5)

The CNL is intentionally small. Its purpose is not to be elegant prose; its purpose is to make the syntactic proposition explicit enough for deterministic downstream processing and independent semantic comparison with the source.

## Speech acts

Each generated statement starts with one of:

```text
ASSERT: <clause>.
COMMAND: <clause>.
ASK WHETHER: <declarative clause>.
ASK WHO|WHAT|WHICH|WHERE|WHEN|WHY|HOW: <declarative clause>.
```

Examples:

```text
ASSERT: John did not send the report.
COMMAND: Send the report to Mary.
ASK WHETHER: Alice did approve the proposal.
ASK WHY: Alice did reject it.
```

The explicit prefix prevents a question or imperative from silently turning into an assertion during normalization.

## Clause policy

The renderer attempts to preserve:

- subject;
- surface predicate morphology;
- auxiliaries and modal verbs;
- negation;
- direct/indirect objects;
- predicative complements;
- prepositional/oblique modifiers;
- ordinary adverbs;
- passive constructions;
- copular constructions;
- basic complement clauses;
- basic adverbial clauses;
- verbal coordination.

A subordinate clause with a recognized marker is made explicit:

```text
If Alice approves the proposal, Bob will deploy it.
Because Mary arrived, John left.
Although John was tired, John continued.
```

For verbal coordination, the shared predicate group is retained to preserve auxiliary and negation scope:

```text
NL:  John reviewed and approved the draft.
CNL: John reviewed and approved the draft.
```

Expanding this group can change the meaning of constructions such as `did not sign or return`. No implicit argument is invented.

## Determinism

No LLM is called by the CNL renderer. Given the same normalized analysis JSON, the same CNL is produced.

## Fidelity diagnostics

Every CNL statement returns:

- `consumed_token_ids`;
- `coverage`;
- `unresolved` items;
- `warnings`.

Punctuation is excluded from token coverage. Discourse tokens are retained and counted. Every non-punctuation token is expected to be consumed or exposed as unresolved. Coverage is token accounting, not a semantic score. Relative clauses and quoted spans may retain their local surface form inside the controlled clause.

Strict mode rejects an output below a configured coverage threshold. It does not establish semantic equivalence or reject every misleading high-coverage output.

Additional speech acts introduced by the benchmark revisions:

```text
ASK CHOICE: <clause containing alternatives>.
ASK CONFIRM: <main clause>; TAG: <original confirmation tag>.
REQUEST: <polite modal clause or request fragment>.
EXPRESS: <interjection>!
GREET: <greeting and addressee>!
THANK: <thanks phrase>!
EXCLAIM: <exclamatory phrase>!
FRAGMENT: <material without a main predicate in the supplied parse>.
```

These rules are incomplete: `Thank you!` with a verbal root and some indirect requests still fail on the holdout benchmark. `FRAGMENT` is explicit retention of a non-propositional span, not successful inference of a missing predicate. See `BENCHMARK.md`.

## What CNL (benchmark revision 5) intentionally does not claim to solve

- quantifier scope;
- negation scope beyond dependency-local patterns;
- difficult pronoun/coreference resolution;
- ellipsis;
- implicit arguments;
- discourse relations not explicitly marked in the parse;
- lexical word-sense disambiguation;
- pragmatics and implicature;
- factual/world-knowledge inference.

These are exactly the kinds of failures the later `NL <-> CNL` semantic judge should detect.
