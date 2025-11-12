"""
Data extraction modules.
Each extractor handles a specific type of data extraction.
"""

from .base import BaseExtractor, ExtractionResult
from .phone import PhoneExtractor
from .address import AddressExtractor
from .hours import HoursExtractor
from .url_discoverer import URLDiscoverer
from .provider_detector import ProviderDetector, CreditAppProviderDetector

__all__ = [
    'BaseExtractor',
    'ExtractionResult',
    'PhoneExtractor',
    'AddressExtractor',
    'HoursExtractor',
    'URLDiscoverer',
    'ProviderDetector',
    'CreditAppProviderDetector',
]
