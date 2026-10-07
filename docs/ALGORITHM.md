# Deterministic formalisation algorithm

## 1. Parse

One of the four adapters receives raw text and returns a common document representation.

```text
Document
  parser
  lang
  text
  sentences[]
    text
    tokens[]
      id text lemma upos xpos feats head deprel
```

Stanza, UDPipe and Trankit are naturally close to Universal Dependencies. spaCy's native English dependency labels are not UD, so they are preserved rather than pretending a lossy one-to-one conversion exists. The renderer recognizes both common UD and common spaCy relations.

## 2. Locate proposition roots

For each sentence the renderer identifies the dependency root. It then detects the speech act:

- terminal `?` -> question, with WH phrases located in the main-clause structure;
- root verb with no explicit subject and imperative morphology -> command;
- otherwise -> assertion.

## 3. Reconstruct noun phrases

A noun phrase is reconstructed from the head plus deterministic nominal dependents such as:

```text
det amod compound nummod poss nmod case flat appos quantmod
```

Relative and adjectival clauses are retained locally with their punctuation. They are not interpreted as independent assertions and no implicit arguments are inferred.

## 4. Reconstruct the predicate

The renderer keeps surface verb morphology and ordered auxiliaries/negation:

```text
John + did + not + send + the report
Alice + may + not + approve + the proposal
The report + was + approved + by Mary
```

Keeping surface morphology avoids requiring another statistical inflection model merely to regenerate English.

## 5. Add arguments and modifiers

The current rule set handles common relations including:

```text
nsubj nsubj:pass nsubjpass csubj
obj dobj iobj dative attr oprd acomp
obl prep advmod
ccomp xcomp
aux aux:pass auxpass cop neg
```

## 6. Make subordinate relations explicit

`advcl` clauses are reconstructed separately. Recognized markers include:

```text
if unless because although though when while since as before after
```

The subordinate relation is then deterministically placed in the CNL.

## 7. Preserve coordination scope

Verbal conjuncts without their own subject retain shared auxiliaries and negation through a predicate group. Explicit subjects remain explicit. The renderer preserves the actual conjunction rather than inventing `either` or `and`.

## 8. Account for information

All non-punctuation tokens, including discourse material, form the token-coverage denominator. Every rule marks the token IDs it consumes.

```text
coverage = consumed semantic token IDs / semantic token IDs
```

Unconsumed items are returned verbatim in `unresolved` with token ID, text, POS and dependency relation.

These diagnostics expose some losses but cannot prevent every case of:

```text
source contains important modifier -> renderer drops it -> output still looks fluent
```

## 9. External semantic check

Coverage is not semantic equivalence. The intended experiment adds a separate oracle after CNL generation, for example the previously discussed ensemble of embedding similarity, cross-encoder, bidirectional NLI and deterministic semantic-difference checks.

The five benchmark revisions and known remaining failures are recorded in `BENCHMARK.md`. Speech-act labeling also covers non-propositional forms; unsupported nominal-root propositions are exposed as fragments.
