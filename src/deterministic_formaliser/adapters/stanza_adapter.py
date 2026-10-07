from __future__ import annotations

from .base import ParserAdapter, BackendError
from ..schema import Document, Sentence, Token, parse_feats


class StanzaAdapter(ParserAdapter):
    name = "stanza"

    def parse(self, text: str, lang: str = "en", **kwargs) -> Document:
        try:
            import stanza
            from stanza.pipeline.core import DownloadMethod
        except ImportError as e:
            raise BackendError("Stanza is not installed. Run: scripts/setup_backend.py stanza --lang en") from e
        processors = kwargs.get("processors", "tokenize,mwt,pos,lemma,depparse")
        try:
            key = (lang, processors, bool(kwargs.get("gpu", False)))
            if getattr(self, "_model_key", None) != key:
                self._pipeline = stanza.Pipeline(
                    lang=lang, processors=processors, use_gpu=key[2], verbose=False,
                    download_method=DownloadMethod.REUSE_RESOURCES,
                )
                self._model_key = key
            nlp = self._pipeline
        except Exception as e:
            raise BackendError(
                f"Cannot load Stanza model for {lang!r}. Run setup first. Original error: {e}"
            ) from e
        doc = nlp(text)
        sentences: list[Sentence] = []
        for si, s in enumerate(doc.sentences, 1):
            toks: list[Token] = []
            for w in s.words:
                toks.append(Token(
                    id=int(w.id),
                    text=w.text,
                    lemma=w.lemma or w.text,
                    upos=w.upos or "",
                    xpos=w.xpos or "",
                    feats=parse_feats(w.feats),
                    head=int(w.head or 0),
                    deprel=w.deprel or "",
                ))
            sent_text = getattr(s, "text", None) or " ".join(t.text for t in toks)
            sentences.append(Sentence(si, sent_text, toks))
        return Document(parser=self.name, lang=lang, text=text, sentences=sentences,
                        meta={"processors": processors})
