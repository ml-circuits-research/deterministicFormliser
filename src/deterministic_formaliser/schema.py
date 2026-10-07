from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


def parse_feats(value: Any) -> dict[str, str]:
    if value is None or value == "_" or value == "":
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    out: dict[str, str] = {}
    for part in str(value).split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


@dataclass(slots=True)
class Token:
    id: int
    text: str
    lemma: str = ""
    upos: str = ""
    xpos: str = ""
    feats: dict[str, str] = field(default_factory=dict)
    head: int = 0
    deprel: str = ""
    start: int | None = None
    end: int | None = None
    misc: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Token":
        return cls(
            id=int(d["id"]),
            text=str(d.get("text", "")),
            lemma=str(d.get("lemma") or d.get("text") or ""),
            upos=str(d.get("upos") or ""),
            xpos=str(d.get("xpos") or ""),
            feats=parse_feats(d.get("feats")),
            head=int(d.get("head") or 0),
            deprel=str(d.get("deprel") or ""),
            start=d.get("start"),
            end=d.get("end"),
            misc=dict(d.get("misc") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Sentence:
    id: int
    text: str
    tokens: list[Token]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Sentence":
        return cls(
            id=int(d.get("id", 1)),
            text=str(d.get("text", "")),
            tokens=[Token.from_dict(x) for x in d.get("tokens", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text, "tokens": [t.to_dict() for t in self.tokens]}


@dataclass(slots=True)
class Document:
    parser: str
    lang: str
    text: str
    sentences: list[Sentence]
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Document":
        return cls(
            parser=str(d.get("parser", "unknown")),
            lang=str(d.get("lang", "en")),
            text=str(d.get("text", "")),
            sentences=[Sentence.from_dict(x) for x in d.get("sentences", [])],
            meta=dict(d.get("meta") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "parser": self.parser,
            "lang": self.lang,
            "text": self.text,
            "sentences": [s.to_dict() for s in self.sentences],
            "meta": self.meta,
        }
