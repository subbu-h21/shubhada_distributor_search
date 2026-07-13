from .base import BaseAdapter, ExtractionOutcome
from .sunshop import SunshopAdapter
from .generic import GenericAdapter


def get_adapter(portal_type: str) -> BaseAdapter:
    pt = (portal_type or "").upper()
    if pt == "SUNSHOP":
        return SunshopAdapter()
    return GenericAdapter()


__all__ = ["BaseAdapter", "ExtractionOutcome", "SunshopAdapter", "GenericAdapter", "get_adapter"]
