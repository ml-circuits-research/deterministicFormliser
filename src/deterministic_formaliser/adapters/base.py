from __future__ import annotations
from abc import ABC, abstractmethod
from ..schema import Document


class BackendError(RuntimeError):
    pass


class ParserAdapter(ABC):
    name: str

    @abstractmethod
    def parse(self, text: str, lang: str = "en", **kwargs) -> Document:
        raise NotImplementedError
