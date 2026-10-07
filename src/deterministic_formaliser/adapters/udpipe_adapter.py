from __future__ import annotations

from pathlib import Path
import re

from .base import ParserAdapter, BackendError
from ..schema import Document, Sentence, Token, parse_feats


def _parse_conllu(data: str) -> list[Sentence]:
    sentences: list[Sentence] = []
    comments: list[str] = []
    rows: list[list[str]] = []

    def flush():
        nonlocal comments, rows
        if not rows:
            comments = []
            return
        text = ""
        for c in comments:
            if c.startswith("# text ="):
                text = c.split("=", 1)[1].strip()
        toks: list[Token] = []
        for cols in rows:
            if len(cols) < 10:
                continue
            raw_id = cols[0]
            if "-" in raw_id or "." in raw_id or not raw_id.isdigit():
                continue
            misc = {}
            if cols[9] not in {"_", ""}:
                for p in cols[9].split("|"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        misc[k] = v
            toks.append(Token(
                id=int(raw_id), text=cols[1], lemma=cols[2] if cols[2] != "_" else cols[1],
                upos=cols[3] if cols[3] != "_" else "", xpos=cols[4] if cols[4] != "_" else "",
                feats=parse_feats(cols[5]), head=int(cols[6]) if cols[6].isdigit() else 0,
                deprel=cols[7] if cols[7] != "_" else "", misc=misc,
            ))
        if not text:
            text = " ".join(t.text for t in toks)
        sentences.append(Sentence(len(sentences) + 1, text, toks))
        comments, rows = [], []

    for line in data.splitlines() + [""]:
        line = line.rstrip("\n")
        if not line.strip():
            flush()
        elif line.startswith("#"):
            comments.append(line)
        else:
            rows.append(line.split("\t"))
    return sentences


class UDPipeAdapter(ParserAdapter):
    name = "udpipe"

    def parse(self, text: str, lang: str = "en", **kwargs) -> Document:
        try:
            from ufal.udpipe import Model, Pipeline
        except ImportError as e:
            raise BackendError("ufal.udpipe is not installed. Run: scripts/setup_backend.py udpipe --lang en") from e
        model_path = kwargs.get("udpipe_model")
        if not model_path:
            root = Path(kwargs.get("project_root") or Path.cwd())
            candidate = root / "models" / "udpipe" / f"{lang}.udpipe"
            if candidate.exists():
                model_path = str(candidate)
        if not model_path or not Path(model_path).exists():
            raise BackendError(
                "UDPipe requires a .udpipe model. Pass --udpipe-model PATH or run scripts/setup_backend.py udpipe --lang en."
            )
        if getattr(self, "_model_key", None) != str(model_path):
            model = Model.load(str(model_path))
            if not model:
                raise BackendError(f"Cannot load UDPipe model: {model_path}")
            self._model = model  # The native pipeline borrows this model's memory.
            self._pipeline = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
            self._model_key = str(model_path)
        pipeline = self._pipeline
        conllu = pipeline.process(text)
        if not conllu:
            raise BackendError("UDPipe returned no output")
        return Document(parser=self.name, lang=lang, text=text, sentences=_parse_conllu(conllu),
                        meta={"model": str(model_path)})
