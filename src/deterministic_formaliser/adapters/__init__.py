from .base import BackendError, ParserAdapter
from .stanza_adapter import StanzaAdapter
from .spacy_adapter import SpacyAdapter
from .udpipe_adapter import UDPipeAdapter
from .trankit_adapter import TrankitAdapter

ADAPTERS = {
    "stanza": StanzaAdapter,
    "spacy": SpacyAdapter,
    "udpipe": UDPipeAdapter,
    "trankit": TrankitAdapter,
}


def get_adapter(name: str) -> ParserAdapter:
    try:
        return ADAPTERS[name]()
    except KeyError as e:
        raise BackendError(f"Unknown parser {name!r}. Expected one of: {', '.join(ADAPTERS)}") from e

__all__ = ["BackendError", "ParserAdapter", "get_adapter", "ADAPTERS"]
