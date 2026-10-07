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
IGNORABLE_RELS = {"discourse"}


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

    def child_tokens(self, head: int, rels: Iterable[str] | None = None) -> list[Token]:
        xs = self.children.get(head, [])
        if rels is None:
            return xs
        relset = set(rels)
        return [x for x in xs if x.deprel.lower() in relset]

    def subtree(self, head: int, *, stop_at_clauses: bool = False, stop_at_conj_verbs: bool = False) -> set[int]:
        out: set[int] = set()
        stack = [head]
        while stack:
            i = stack.pop()
            if i in out or i not in self.by_id:
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

    def ordered_text(self, ids: Iterable[int], *, mark: bool = True) -> str:
        ids2 = sorted(set(ids))
        toks = [self.by_id[i] for i in ids2 if i in self.by_id and self.by_id[i].upos != "PUNCT"]
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
    s = re.sub(r"([('“])\s+", r"\1", s)
    s = re.sub(r"\s+([)’”])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _decap(s: str) -> str:
    if len(s) >= 2 and s[0].isupper() and s[1:].islower():
        return s[0].lower() + s[1:]
    return s


def _finish(s: str) -> str:
    s = s.strip()
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

        speech, wh = self._speech_act(v, root)
        clause = self._render_clause(v, root, inherited_subject=None)
        if not clause:
            clause = v.ordered_text(t.id for t in content)
            warnings.append("fell back to surface token order")

        if speech == "QUESTION_WH":
            label = (wh or "WHAT").upper()
            body = _finish(clause)
            text = f"ASK {label}: {body}"
        elif speech == "QUESTION_YN":
            text = f"ASK WHETHER: {_finish(clause)}"
        elif speech == "COMMAND":
            text = f"COMMAND: {_finish(_cap_first(clause))}"
        else:
            text = f"ASSERT: {_finish(clause)}"

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
        wh = next(((t.lemma or t.text).lower() for t in v.child_tokens(root.id)
                   if (t.lemma or t.text).lower() in WH_WORDS), None)
        if text.endswith("?") or wh:
            return ("QUESTION_WH", wh) if wh else ("QUESTION_YN", None)
        has_subject = any(c.deprel.lower() in SUBJECT_RELS for c in v.children.get(root.id, []))
        mood = root.feats.get("Mood", "").lower()
        bare_imperative = root.xpos == "VB" and not v.child_tokens(root.id, {"aux", "mark"})
        if root.upos in {"VERB", "AUX"} and not has_subject and (mood == "imp" or bare_imperative):
            return "COMMAND", None
        return "ASSERT", None

    def _render_np(self, v: SentenceView, head: Token, excluded: set[int] | None = None) -> str:
        # Follow licensed edges, not labels on arbitrary descendants. Otherwise a
        # subject's determiner can leak into a copular predicate.
        excluded = excluded or set()
        ids: set[int] = set()
        stack = [head.id]
        allowed = NOMINAL_SAFE_RELS | {"prep", "pobj", "preconj", "npadvmod"}
        while stack:
            i = stack.pop()
            if i in ids or i in excluded:
                continue
            ids.add(i)
            for c in v.child_tokens(i):
                rel = c.deprel.lower()
                if rel in allowed or rel.startswith(("nmod", "flat")):
                    if rel == "conj" and c.upos in {"VERB", "AUX"}:
                        continue
                    stack.append(c.id)
        return v.ordered_text(ids)

    def _subject(self, v: SentenceView, root: Token) -> Token | None:
        for c in v.children.get(root.id, []):
            if c.deprel.lower() in SUBJECT_RELS:
                return c
        return None

    def _marker(self, v: SentenceView, root: Token) -> str | None:
        for c in v.children.get(root.id, []):
            if c.deprel.lower() == "mark" or (c.deprel == "advmod" and c.text.lower() in SUBORDINATORS | WH_WORDS | {"once"}):
                v.mark([c.id])
                return (c.lemma or c.text).lower()
        return None

    def _cc(self, v: SentenceView, conj: Token) -> str:
        for c in v.children.get(conj.id, []):
            if c.deprel.lower() == "cc":
                v.mark([c.id])
                return (c.lemma or c.text).lower()
        # spaCy can attach cc to the first conjunct.
        for c in v.children.get(conj.head, []):
            if c.deprel.lower() == "cc" and c.id < conj.id:
                v.mark([c.id])
                return (c.lemma or c.text).lower()
        return "and"

    def _render_clause(self, v: SentenceView, root: Token, inherited_subject: str | None) -> str:
        subject_tok = self._subject(v, root)
        if subject_tok and subject_tok.deprel.startswith("csubj"):
            marker = self._marker(v, subject_tok)
            subject = clean_join([marker or "", self._render_clause(v, subject_tok, None)])
        else:
            subject = self._render_np(v, subject_tok) if subject_tok else inherited_subject

        auxiliaries = [c for c in v.children.get(root.id, []) if c.deprel.lower() in AUX_RELS
                       or (c.deprel == "advmod" and c.text.lower() in {"not", "n't", "never"})]
        prefix_neg = [c for c in auxiliaries if subject_tok and c.id < subject_tok.id and c.text.lower() in {"not", "never"}]
        auxiliaries = [c for c in auxiliaries if c not in prefix_neg]
        if prefix_neg:
            subject = clean_join([v.ordered_text(c.id for c in prefix_neg), subject or ""])
        aux_ids = {c.id for c in auxiliaries}
        v.mark(aux_ids)
        v.mark([root.id])
        predicate_tokens = sorted(auxiliaries + [root], key=lambda x: x.id)
        predicate = clean_join([_decap(self._render_np(v, t, aux_ids))
                                if t.id == root.id and t.upos not in {"VERB", "AUX"}
                                else _decap(t.text) for t in predicate_tokens if t.upos != "PUNCT"])

        objects: list[str] = []
        obliques: list[str] = []
        adverbs: list[str] = []
        complements: list[str] = []

        for c in v.children.get(root.id, []):
            rel = c.deprel.lower()
            if rel in SUBJECT_RELS or rel in AUX_RELS or c.id in aux_ids or c.id in v.consumed or rel in {"punct", "cc", "mark"}:
                continue
            if rel in OBJECT_RELS:
                objects.append(self._render_np(v, c))
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
        advcls = [c for c in v.children.get(root.id, []) if c.deprel.lower() == "advcl"]
        for c in advcls:
            marker = self._marker(v, c)
            sub = self._render_clause(v, c, inherited_subject=None)
            if marker:
                base = f"{marker.capitalize()} {sub}, {base}"
            else:
                base = f"{base}, {sub}"

        # Clause-level coordination. Nominal coordination is handled inside _render_np.
        conjs = [c for c in v.children.get(root.id, []) if c.deprel.lower() == "conj" and c.upos in {"VERB", "AUX", "ADJ"}]
        for c in conjs:
            cc = self._cc(v, c)
            rhs = self._render_clause(v, c, inherited_subject=subject)
            if cc == "or":
                base = f"either {base} or {rhs}"
            elif cc == "but":
                base = f"{base} but {rhs}"
            else:
                base = f"{base} and {rhs}"

        return base.strip()


def render_cnl(doc: Document, *, strict: bool = False, min_coverage: float = 0.90) -> CNLDocument:
    return CNLRenderer(strict=strict, min_coverage=min_coverage).render_document(doc)
