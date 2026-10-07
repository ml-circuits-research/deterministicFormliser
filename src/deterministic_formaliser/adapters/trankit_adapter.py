from __future__ import annotations

from pathlib import Path

from .base import ParserAdapter, BackendError
from ..schema import Document, Sentence, Token, parse_feats

TRANKIT_LANG = {
    "en": "english", "de": "german", "fr": "french", "es": "spanish", "it": "italian",
    "pt": "portuguese", "ro": "romanian", "nl": "dutch", "pl": "polish", "cs": "czech",
}


def _flatten(raw_tokens):
    out = []
    for t in raw_tokens or []:
        expanded = t.get("expanded") if isinstance(t, dict) else None
        if expanded:
            out.extend(expanded)
        else:
            out.append(t)
    return out


class TrankitAdapter(ParserAdapter):
    name = "trankit"

    def parse(self, text: str, lang: str = "en", **kwargs) -> Document:
        try:
            from trankit import Pipeline
        except ImportError as e:
            raise BackendError("Trankit is not installed. Run: scripts/setup_backend.py trankit --lang en") from e
        t_lang = kwargs.get("trankit_lang") or TRANKIT_LANG.get(lang, lang)
        cache = kwargs.get("trankit_cache")
        if cache is None:
            root = Path(kwargs.get("project_root") or Path.cwd())
            cache = str(root / "models" / "trankit")
        try:
            key = (t_lang, bool(kwargs.get("gpu", False)), cache)
            if getattr(self, "_model_key", None) != key:
                self._pipeline = Pipeline(t_lang, gpu=key[1], cache_dir=cache)
                self._model_key = key
            p = self._pipeline
            raw = p.posdep(text)
        except Exception as e:
            raise BackendError(
                f"Cannot initialize/run Trankit language {t_lang!r}. Run setup first. Original error: {e}"
            ) from e
        sentences: list[Sentence] = []
        for si, s in enumerate(raw.get("sentences", []), 1):
            toks: list[Token] = []
            for rt in _flatten(s.get("tokens", [])):
                rid = rt.get("id")
                if not isinstance(rid, int):
                    continue
                toks.append(Token(
                    id=rid,
                    text=rt.get("text", ""), lemma=rt.get("lemma") or rt.get("text", ""),
                    upos=rt.get("upos", ""), xpos=rt.get("xpos", ""), feats=parse_feats(rt.get("feats")),
                    head=int(rt.get("head") or 0), deprel=rt.get("deprel", ""),
                    start=(rt.get("dspan") or [None, None])[0] if isinstance(rt.get("dspan"), (list, tuple)) else None,
                    end=(rt.get("dspan") or [None, None])[1] if isinstance(rt.get("dspan"), (list, tuple)) else None,
                ))
            sentences.append(Sentence(si, s.get("text") or " ".join(t.text for t in toks), toks))
        return Document(parser=self.name, lang=lang, text=text, sentences=sentences,
                        meta={"language_package": t_lang, "cache_dir": cache})
