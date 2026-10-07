from __future__ import annotations

from .base import ParserAdapter, BackendError
from ..schema import Document, Sentence, Token

SPACY_MODELS = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
}


class SpacyAdapter(ParserAdapter):
    name = "spacy"

    def parse(self, text: str, lang: str = "en", **kwargs) -> Document:
        try:
            import spacy
        except ImportError as e:
            raise BackendError("spaCy is not installed. Run: scripts/setup_backend.py spacy --lang en") from e
        model = kwargs.get("spacy_model") or SPACY_MODELS.get(lang)
        if not model:
            raise BackendError(f"No default spaCy model is configured for language {lang!r}; pass --spacy-model.")
        try:
            if getattr(self, "_model_key", None) != model:
                self._pipeline = spacy.load(model)
                self._model_key = model
            nlp = self._pipeline
        except Exception as e:
            raise BackendError(
                f"Cannot load spaCy model {model!r}. Run setup first or pass --spacy-model. Original error: {e}"
            ) from e
        d = nlp(text)
        sentences: list[Sentence] = []
        for si, s in enumerate(d.sents, 1):
            base = s.start
            toks: list[Token] = []
            for tok in s:
                if tok.is_space:
                    continue
                local_id = tok.i - base + 1
                if tok.head.i == tok.i:
                    head = 0
                elif tok.head.i < s.start or tok.head.i >= s.end:
                    head = 0
                else:
                    head = tok.head.i - base + 1
                toks.append(Token(
                    id=local_id,
                    text=tok.text,
                    lemma=tok.lemma_ or tok.text,
                    upos=tok.pos_ or "",
                    xpos=tok.tag_ or "",
                    feats=tok.morph.to_dict(),
                    head=head,
                    deprel=("root" if head == 0 else (tok.dep_ or "").lower()),
                    start=tok.idx,
                    end=tok.idx + len(tok.text),
                ))
            sentences.append(Sentence(si, s.text, toks))
        return Document(parser=self.name, lang=lang, text=text, sentences=sentences,
                        meta={"model": model, "note": "spaCy native dependency labels are preserved; they are not UD labels."})
