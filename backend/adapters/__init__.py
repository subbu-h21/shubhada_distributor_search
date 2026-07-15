from .base import BaseAdapter, ExtractionOutcome
from .sunshop import SunshopAdapter
from .chethana import ChethanaAdapter
from .liveconnect import LiveconnectAdapter
from .vardhaman import VardhamanAdapter
from .retailio import RetailioAdapter
from .yashika import YashikaAdapter
from .generic import GenericAdapter


def get_adapter(portal_type: str, **kwargs) -> BaseAdapter:
    pt = (portal_type or "").upper()
    if pt == "SUNSHOP":
        return SunshopAdapter()
    if pt == "CHETHANA":
        return ChethanaAdapter()
    if pt == "LIVECONNECT":
        return LiveconnectAdapter(cookies=kwargs.get("liveconnect_cookies"))
    if pt == "VARDHAMAN":
        return VardhamanAdapter()
    if pt == "RETAILIO":
        return RetailioAdapter(
            cookies=kwargs.get("retailio_cookies"),
            local_storage=kwargs.get("retailio_local_storage"),
        )
    if pt == "YASHIKA":
        return YashikaAdapter()
    return GenericAdapter()


__all__ = ["BaseAdapter", "ExtractionOutcome", "SunshopAdapter", "ChethanaAdapter", "LiveconnectAdapter", "VardhamanAdapter", "RetailioAdapter", "YashikaAdapter", "GenericAdapter", "get_adapter"]
