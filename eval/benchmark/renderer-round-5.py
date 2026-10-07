from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable
import re

from .schema import Document, Sentence, Token

SUBJECT_RELS = {"nsubj", "nsubj:pass", "nsubjpass", "csubj", "csubj:pass", "csubjpass"}
OBJECT_RELS = {"obj", "dobj", "iobj", "dative", "attr", "oprd", "acomp"}
AUX_RELS = {"aux", "aux:pass", "auxpass", "cop", "neg", "prt", "compound:prt"}
CLAUSE_RELS = {"advcl", "ccomp", "xcomp", "acl", "acl:relcl", "relcl"}
NOMINAL_SAFE_RELS = {
    "det", "amod", "compound", "compound:prt", "nummod", "poss", "nmod:poss",
    "case", "flat", "flat:name", "name", "fixed", "goeswith", "appos", "quantmod",
    "predet", "cc", "conj", "advmod", "nmod", "neg",
}
WH_WORDS = {"who", "whom", "whose", "what", "which", "where", "when", "why", "how"}
SUBORDINATORS = {"if", "unless", "because", "although", "though", "when", "while", "since", "as", "before", "after"}
IGNORABLE_RELS: set[str] = set()


@dataclass(slots=True)
class CNLStatement:
    sentence_id: int
    speech_act: str
    text: str
    coverage: float
    consumed_token_ids: list[int] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass(slots=True)
class CNLDocument:
    parser: str
    lang: str
    source_text: str
    cnl: str
    coverage: float
    statements: list[CNLStatement]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "parser": self.parser,
            "lang": self.lang,
            "source_text": self.source_text,
            "cnl": self.cnl,
            "coverage": self.coverage,
            "statements": [s.to_dict() for s in self.statements],
            "warnings": self.warnings,
        }


class SentenceView:
    def __init__(self, sentence: Sentence):
        self.sentence = sentence
        self.by_id = {t.id: t for t in sentence.tokens}
        self.children: dict[int, list[Token]] = {t.id: [] for t in sentence.tokens}
        self.children[0] = []
        for t in sentence.tokens:
            self.children.setdefault(t.head, []).append(t)
        for xs in self.children.values():
            xs.sort(key=lambda t: t.id)
        self.consumed: set[int] = set()
        self.suppressed: set[int] = set()
        self.warnings: list[str] = []

    def child_tokens(self, head: int, rels: Iterable[str] | None = None) -> list[Token]:
        xs = [t for t in self.children.get(head, []) if t.id not in self.suppressed]
        if rels is None:
            return xs
        relset = set(rels)
        return [x for x in xs if x.deprel.lower() in relset]

    def subtree(self, head: int, *, stop_at_clauses: bool = False, stop_at_conj_verbs: bool = False) -> set[int]:
        out: set[int] = set()
        stack = [head]
        while stack:
            i = stack.pop()
            if i in out or i not in self.by_id or i in self.suppressed:
                continue
            out.add(i)
            for c in self.children.get(i, []):
                rel = c.deprel.lower()
                if stop_at_clauses and (rel in CLAUSE_RELS or rel.startswith("acl") or rel == "advcl"):
                    continue
                if stop_at_conj_verbs and rel == "conj" and c.upos in {"VERB", "AUX"}:
                    continue
                stack.append(c.id)
        return out

    def mark(self, ids: Iterable[int]) -> None:
        self.consumed.update(ids)

    def ordered_text(self, ids: Iterable[int], *, mark: bool = True, keep_punct: bool = False) -> str:
        ids2 = sorted(set(ids))
        toks = [self.by_id[i] for i in ids2 if i in self.by_id and (keep_punct or self.by_id[i].upos != "PUNCT")]
        if mark:
            self.mark(t.id for t in toks)
        words = [t.text for t in toks]
        return clean_join(words)


def clean_join(words: list[str]) -> str:
    if not words:
        return ""
    s = " ".join(w for w in words if w)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"\s+(n[’']t|[’'](?:s|re|ve|ll|d|m))\b", r"\1", s)
    s = re.sub(r'"\s*([^"\n]*?)\s*"', lambda m: '"' + m.group(1).strip() + '"', s)
    s = re.sub(r"([('“])\s+", r"\1", s)
    s = re.sub(r"\s+([)’”])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _decap(s: str) -> str:
    if len(s) >= 2 and s[0].isupper() and s[1:].islower():
        return s[0].lower() + s[1:]
    return s


def _finish(s: str) -> str:
    s = s.strip()
    if re.search(r'[.!?]["”]$', s):
        return s
    s = re.sub(r"[.?!]+$", "", s).strip()
    return (s + ".") if s else s


def _cap_first(s: str) -> str:
    return (s[:1].upper() + s[1:]) if s else s


class CNLRenderer:
    """Rule-based, deterministic renderer from dependency analyses to a small CNL.

    The output is deliberately explicit about speech act:
      ASSERT: ...
      ASK WHETHER: ...
      ASK <WH>: ...
      COMMAND: ...

    It is not intended to solve semantic ambiguity. It exposes coverage and unresolved
    tokens so an external semantic oracle can reject lossy formalizations.
    """

    def __init__(self, *, strict: bool = False, min_coverage: float = 0.90):
        if not 0 <= min_coverage <= 1:
            raise ValueError("min_coverage must be between 0 and 1")
        self.strict = strict
        self.min_coverage = min_coverage

    def render_document(self, doc: Document) -> CNLDocument:
        if doc.lang != "en":
            raise ValueError("CNL rendering currently supports English only; use analysis mode for other languages")
        if doc.text.strip() and (not doc.sentences or any(not s.tokens for s in doc.sentences)):
            raise ValueError("Nonempty input has an empty dependency analysis")
        statements: list[CNLStatement] = []
        warnings: list[str] = []
        weighted_num = 0.0
        weighted_den = 0
        for sentence in doc.sentences:
            st = self.render_sentence(sentence)
            statements.append(st)
            denom = len([t for t in sentence.tokens if t.upos != "PUNCT" and t.deprel.lower() not in IGNORABLE_RELS])
            weighted_num += st.coverage * denom
            weighted_den += denom
            warnings.extend(f"sentence {sentence.id}: {w}" for w in st.warnings)
        coverage = weighted_num / weighted_den if weighted_den else 1.0
        cnl = "\n".join(st.text for st in statements if st.text)
        if self.strict and coverage < self.min_coverage:
            raise ValueError(f"CNL coverage {coverage:.3f} below threshold {self.min_coverage:.3f}")
        return CNLDocument(
            parser=doc.parser,
            lang=doc.lang,
            source_text=doc.text,
            cnl=cnl,
            coverage=coverage,
            statements=statements,
            warnings=warnings,
        )

    def render_sentence(self, sentence: Sentence) -> CNLStatement:
        v = SentenceView(sentence)
        content = [t for t in sentence.tokens if t.upos != "PUNCT" and t.deprel.lower() not in IGNORABLE_RELS]
        roots = [t for t in sentence.tokens if t.head == 0 or t.deprel.lower() == "root"]
        root = roots[0] if roots else (content[0] if content else None)
        warnings: list[str] = []
        if root is None:
            return CNLStatement(sentence.id, "ASSERT", "", 1.0)

        tag = None
        if sentence.text.rstrip().endswith("?"):
            commas = [t.id for t in sentence.tokens if t.text == ","]
            if commas:
                tag_tokens = [t for t in sentence.tokens if t.id > commas[-1] and t.upos != "PUNCT"]
                candidate = clean_join([t.text for t in tag_tokens])
                if re.fullmatch(r"(?:am|is|are|was|were|do|does|did|have|has|had|can|could|will|would|should|must|might)(?:n't| not)? (?:I|you|he|she|it|we|they)", candidate, re.I):
                    tag = candidate
                    v.suppressed.update(t.id for t in tag_tokens)
                    v.mark(v.suppressed)
        speech, wh = self._speech_act(v, root)
        if tag:
            speech = "QUESTION_TAG"
        nonpropositional = root.upos not in {"VERB", "AUX"} and not v.child_tokens(root.id, {"cop"})
        if nonpropositional:
            clause = v.ordered_text(v.subtree(root.id), keep_punct=True)
            if speech == "FRAGMENT":
                warnings.append("fragment has no main predicate in the supplied analysis; no proposition inferred")
        else:
            clause = self._render_clause(v, root, inherited_subject=None)
        if not clause:
            clause = v.ordered_text(t.id for t in content)
            warnings.append("fell back to surface token order")

        if speech == "QUESTION_TAG":
            text = f"ASK CONFIRM: {clause.rstrip('.?!')}; TAG: {tag}."
        elif speech == "QUESTION_WH":
            label = (wh or "WHAT").upper()
            body = _finish(clause)
            text = f"ASK {label}: {body}"
        elif speech == "QUESTION_YN":
            text = f"ASK WHETHER: {_finish(clause)}"
        elif speech == "QUESTION_CHOICE":
            text = f"ASK CHOICE: {_finish(clause)}"
        elif speech in {"EXPRESS", "GREET", "THANK", "EXCLAIM", "FRAGMENT", "REQUEST"}:
            body = _finish(_cap_first(clause))
            if sentence.text.rstrip().endswith("!"):
                body = body.rstrip(".") + "!"
            text = f"{speech}: {body}"
        elif speech == "COMMAND":
            text = f"COMMAND: {_finish(_cap_first(clause))}"
        else:
            text = f"ASSERT: {_finish(clause)}"

        warnings.extend(v.warnings)
        content_ids = {t.id for t in content}
        unresolved_ids = sorted(content_ids - v.consumed)
        unresolved = [
            {"id": i, "text": v.by_id[i].text, "deprel": v.by_id[i].deprel, "upos": v.by_id[i].upos}
            for i in unresolved_ids
        ]
        coverage = len(v.consumed & content_ids) / len(content_ids) if content_ids else 1.0
        if unresolved:
            warnings.append("unresolved semantic material: " + ", ".join(f"{x['text']}/{x['deprel']}" for x in unresolved))
        if self.strict and coverage < self.min_coverage:
            raise ValueError(
                f"sentence {sentence.id}: CNL coverage {coverage:.3f} below threshold {self.min_coverage:.3f}; unresolved={unresolved}"
            )
        return CNLStatement(
            sentence_id=sentence.id,
            speech_act=speech,
            text=text,
            coverage=coverage,
            consumed_token_ids=sorted(v.consumed),
            unresolved=unresolved,
            warnings=warnings,
        )

    def _speech_act(self, v: SentenceView, root: Token) -> tuple[str, str | None]:
        text = v.sentence.text.strip()
        words = {t.text.lower() for t in v.sentence.tokens}
        has_predicate = root.upos in {"VERB", "AUX"} or bool(v.child_tokens(root.id, {"cop"}))
        if not has_predicate:
            if root.text.lower() in {"hello", "hi", "hey", "goodbye", "bye"}:
                return "GREET", None
            if root.text.lower() in {"thanks", "thank"}:
                return "THANK", None
            if "please" in words:
                return "REQUEST", None
            if root.upos == "INTJ" or root.text.lower() in {"ouch", "wow", "alas", "oops"}:
                return "EXPRESS", None
            if text.endswith("!"):
                return "EXCLAIM", None
            return "FRAGMENT", None
        if text.endswith("?"):
            main_ids = v.subtree(root.id, stop_at_clauses=True, stop_at_conj_verbs=True)
            wh = next(((t.lemma or t.text).lower() for t in v.sentence.tokens
                       if t.id in main_ids and (t.lemma or t.text).lower() in WH_WORDS), None)
            if "please" in words and any(t.text.lower() == "you" for t in v.child_tokens(root.id, SUBJECT_RELS)):
                return "REQUEST", None
            if wh:
                return "QUESTION_WH", wh
            if any(t.text.lower() == "or" and t.id in main_ids for t in v.sentence.tokens):
                return "QUESTION_CHOICE", None
            return "QUESTION_YN", None
        has_subject = bool(v.child_tokens(root.id, SUBJECT_RELS))
        mood = root.feats.get("Mood", "").lower()
        auxiliaries = v.child_tokens(root.id, {"aux", "mark"})
        bare_imperative = root.xpos == "VB" and all((t.lemma or t.text).lower() == "do" for t in auxiliaries)
        if root.upos in {"VERB", "AUX"} and not has_subject and (mood == "imp" or bare_imperative):
            return "COMMAND", None
        return "ASSERT", None

    def _render_np(self, v: SentenceView, head: Token, excluded: set[int] | None = None) -> str:
        # Follow licensed edges, not labels on arbitrary descendants. Otherwise a
        # subject's determiner can leak into a copular predicate.
        excluded = excluded or set()
        ids: set[int] = set()
        stack = [head.id]
        allowed = NOMINAL_SAFE_RELS | {"prep", "pobj", "preconj", "npadvmod", "det:predet", "cc:preconj"}
        while stack:
            i = stack.pop()
            if i in ids or i in excluded:
                continue
            ids.add(i)
            for c in v.child_tokens(i):
                rel = c.deprel.lower()
                if rel in {"acl", "acl:relcl", "relcl"}:
                    # Retain the embedded modifier in its original local order.
                    # This does not guess missing arguments or resolve coreference.
                    ids.update(v.subtree(c.id))
                    continue
                if rel in allowed or rel.startswith(("nmod", "flat")):
                    if rel == "conj" and c.upos in {"VERB", "AUX"}:
                        continue
                    stack.append(c.id)
        if ids:
            lo, hi = min(ids), max(ids)
            commas = {t.id for t in v.sentence.tokens if lo < t.id < hi and t.text == ","}
            if commas and hi + 1 in v.by_id and v.by_id[hi + 1].text == ",":
                commas.add(hi + 1)
            ids.update(commas)
        return v.ordered_text(ids, keep_punct=True)

    def _subject(self, v: SentenceView, root: Token) -> Token | None:
        for c in v.child_tokens(root.id):
            if c.deprel.lower() in SUBJECT_RELS:
                return c
        return None

    def _marker(self, v: SentenceView, root: Token) -> str | None:
        for c in v.child_tokens(root.id):
            if c.deprel.lower() == "mark" or (c.deprel == "advmod" and c.text.lower() in SUBORDINATORS | WH_WORDS | {"once"}):
                ids = {c.id} | {t.id for t in v.child_tokens(c.id, {"fixed"})}
                return v.ordered_text(ids).lower()
        return None

    def _cc(self, v: SentenceView, conj: Token) -> str:
        for c in v.children.get(conj.id, []):
            if c.deprel.lower() == "cc":
                v.mark([c.id])
                return (c.lemma or c.text).lower()
        # spaCy can attach cc to the first conjunct.
        for c in reversed(v.children.get(conj.head, [])):
            if c.deprel.lower() == "cc" and c.id < conj.id:
                v.mark([c.id])
                return (c.lemma or c.text).lower()
        # Some parsers attach the coordinator to a remnant in a gapped clause.
        candidates = [v.by_id[i] for i in v.subtree(conj.id)
                      if v.by_id[i].deprel == "cc" and i < conj.id]
        if candidates:
            c = max(candidates, key=lambda t: t.id)
            v.mark([c.id])
            return c.text.lower()
        v.warnings.append("coordination has no explicit connector; relation not inferred")
        return ""

    def _render_clause(self, v: SentenceView, root: Token, inherited_subject: str | None) -> str:
        pragmatic = []
        pragmatic_ids = set()
        inline_politeness = []
        has_explicit_subject = bool(self._subject(v, root))
        for c in v.child_tokens(root.id):
            next_token = v.by_id.get(c.id + 1)
            separated_prefix = c.id < root.id and next_token and next_token.text == ","
            if c.deprel in {"discourse", "intj", "vocative"} or (separated_prefix and c.deprel in {"advmod", "npadvmod"}):
                if c.id not in v.consumed:
                    if c.text.lower() == "please" and has_explicit_subject:
                        inline_politeness.append(c)
                        v.mark([c.id])
                    else:
                        pragmatic.append(self._render_np(v, c))
                    pragmatic_ids.update(v.subtree(c.id))
        subject_tok = self._subject(v, root)
        embedded_wh = (root.lemma or root.text).lower() in WH_WORDS and root.head != 0 and bool(v.child_tokens(root.id, {"cop"}))
        if embedded_wh and subject_tok is None:
            for cop in v.child_tokens(root.id, {"cop"}):
                subject_tok = self._subject(v, cop)
                if subject_tok:
                    break
        if subject_tok and subject_tok.deprel.startswith("csubj"):
            marker = self._marker(v, subject_tok)
            subject = clean_join([marker or "", self._render_clause(v, subject_tok, None)])
        else:
            subject = self._render_np(v, subject_tok) if subject_tok else inherited_subject

        focus = [c for c in v.child_tokens(root.id) if subject_tok and c.id < subject_tok.id
                 and c.text.lower() in {"only", "even", "neither", "either"}]
        if focus:
            subject = clean_join([v.ordered_text(c.id for c in focus), subject or ""])
        auxiliaries = [c for c in v.child_tokens(root.id) if c.deprel.lower() in AUX_RELS
                       or (c.deprel == "advmod" and c.text.lower() in {"not", "n't", "never"})]
        prefix_neg = [c for c in auxiliaries if subject_tok and c.id < subject_tok.id and c.text.lower() in {"not", "never"}]
        auxiliaries = [c for c in auxiliaries if c not in prefix_neg]
        if prefix_neg:
            subject = clean_join([v.ordered_text(c.id for c in prefix_neg), subject or ""])
        aux_ids = {c.id for c in auxiliaries}
        v.mark(aux_ids)
        v.mark([root.id])
        predicate_tokens = sorted(auxiliaries + inline_politeness + ([] if embedded_wh else [root]), key=lambda x: x.id)
        predicate = clean_join([_decap(self._render_np(v, t, aux_ids | pragmatic_ids | {x.id for x in v.child_tokens(root.id, {"cc"})}))
                                if t.id == root.id and t.upos not in {"VERB", "AUX"}
                                else _decap(t.text) for t in predicate_tokens if t.upos != "PUNCT"])

        conjs = [c for c in v.child_tokens(root.id, {"conj"})
                 if c.upos in {"VERB", "AUX", "ADJ"} or root.upos in {"VERB", "AUX"}]
        deferred_objects: list[tuple[int, str]] = []
        objects: list[str] = []
        obliques: list[str] = []
        adverbs: list[str] = []
        complements: list[str] = []

        for c in v.child_tokens(root.id):
            rel = c.deprel.lower()
            if rel in SUBJECT_RELS or rel in AUX_RELS or c.id in aux_ids or c.id in v.consumed or rel in {"punct", "cc", "mark"}:
                continue
            if rel in OBJECT_RELS:
                if c.upos == "ADV" and v.child_tokens(c.id, {"cop"}):
                    phrase = self._render_clause(v, c, None)
                else:
                    phrase = self._render_np(v, c)
                if any(k.id < c.id and not self._subject(v, k) for k in conjs):
                    deferred_objects.append((c.id, phrase))
                else:
                    objects.append(phrase)
            elif rel in {"prep", "agent"}:  # spaCy-style PP head
                obliques.append(v.ordered_text(v.subtree(c.id, stop_at_clauses=True, stop_at_conj_verbs=True)))
            elif rel.startswith("obl") or rel in {"npadvmod", "tmod"}:
                obliques.append(v.ordered_text(v.subtree(c.id, stop_at_clauses=True, stop_at_conj_verbs=True)))
            elif rel == "advmod":
                lemma = (c.lemma or c.text).lower()
                if lemma not in WH_WORDS or c.head != next((t.id for t in v.sentence.tokens if t.head == 0), None):
                    adverbs.append(v.ordered_text(v.subtree(c.id, stop_at_clauses=True, stop_at_conj_verbs=True)))
                else:
                    v.mark([c.id])
            elif rel in {"ccomp", "xcomp"}:
                subtree = v.subtree(c.id)
                quote_ids = [t.id for t in v.sentence.tokens if t.text in {'"', '“', '”'}]
                if len(quote_ids) >= 2 and quote_ids[0] < c.id < quote_ids[-1]:
                    quoted = {t.id for t in v.sentence.tokens if quote_ids[0] <= t.id <= quote_ids[-1]}
                    if subtree - quoted <= {t.id for t in v.sentence.tokens if t.upos == "PUNCT"}:
                        complements.append(v.ordered_text(quoted, keep_punct=True))
                        continue
                marker = self._marker(v, c)
                cc = self._render_clause(v, c, inherited_subject=None)
                complements.append(clean_join([marker or "", cc]))
            elif rel == "expl":
                expletive = self._render_np(v, c)
                if subject:
                    objects.insert(0, subject)
                subject = expletive
            elif rel in {"discourse", "vocative"}:
                # Intentionally not part of core proposition; left unresolved for fidelity accounting.
                continue
            elif rel.startswith("nmod") and root.upos in {"NOUN", "PROPN", "ADJ"}:
                obliques.append(v.ordered_text(v.subtree(c.id, stop_at_clauses=True, stop_at_conj_verbs=True)))

        base = clean_join([p for p in [subject or "", predicate, *objects, *complements, *obliques, *adverbs] if p])

        # Adverbial clauses: preserve explicit discourse marker and nesting.
        advcls = [c for c in v.child_tokens(root.id) if c.deprel.lower() == "advcl"]
        prefixes = []
        for c in advcls:
            marker = self._marker(v, c)
            sub = self._render_clause(v, c, inherited_subject=None)
            if marker:
                if c.id < root.id:
                    prefixes.append(f"{marker} {sub}")
                else:
                    base = f"{base} {marker} {sub}"
            else:
                base = f"{base}, {sub}"
        if prefixes:
            base = _cap_first(", ".join(prefixes)) + ", " + base

        # Keep shared auxiliary/negation scope by retaining a predicate group.
        # Repeating a subject would turn "did not A or B" into a different claim.
        tail = [(c.id, c) for c in conjs] + deferred_objects
        for _, item in sorted(tail, key=lambda pair: pair[0]):
            if isinstance(item, str):
                base = f"{base} {item}"
                continue
            cc = self._cc(v, item)
            if item.upos not in {"VERB", "AUX", "ADJ"}:
                ids = v.subtree(item.id) - v.consumed
                rhs = v.ordered_text(ids)
            else:
                rhs = self._render_clause(v, item, inherited_subject=None)
            base = f"{base} {cc} {rhs}"

        if embedded_wh:
            base = root.text.lower() + " " + base
        for prefix in reversed(pragmatic):
            base = prefix + (" " if prefix.lower() == "please" else ", ") + base
        return base.strip()


def render_cnl(doc: Document, *, strict: bool = False, min_coverage: float = 0.90) -> CNLDocument:
    return CNLRenderer(strict=strict, min_coverage=min_coverage).render_document(doc)
