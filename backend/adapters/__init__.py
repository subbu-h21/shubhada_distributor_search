from .base import BaseAdapter, ExtractionOutcome
from .sunshop import SunshopAdapter
from .chethana import ChethanaAdapter
from .generic import GenericAdapter


def get_adapter(portal_type: str) -> BaseAdapter:
    pt = (portal_type or "").upper()
    if pt == "SUNSHOP":
        return SunshopAdapter()
    if pt == "CHETHANA":
        return ChethanaAdapter()
    return GenericAdapter()


__all__ = ["BaseAdapter", "ExtractionOutcome", "SunshopAdapter", "ChethanaAdapter", "GenericAdapter", "get_adapter"]
