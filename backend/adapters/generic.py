"""Fallback generic adapter — same behavior as Sunshop but with no portal-specific overrides."""
from .sunshop import SunshopAdapter


class GenericAdapter(SunshopAdapter):
    portal_type = "GENERIC"
