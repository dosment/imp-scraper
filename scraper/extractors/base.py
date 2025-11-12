"""
Base extractor class.
All extractors inherit from this to ensure consistent interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from playwright.async_api import Page

from ..browser import DealerContext
from ..models import ConfidenceLevel
from ..utils import get_logger


class ExtractionResult:
    """Result of an extraction attempt."""

    def __init__(
        self,
        data: Any,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        source: Optional[str] = None,
        evidence: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.data = data
        self.confidence = confidence
        self.source = source
        self.evidence = evidence
        self.error = error

    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return self.data is not None and self.confidence != ConfidenceLevel.UNSURE

    def __repr__(self):
        return (
            f"ExtractionResult(data={self.data}, confidence={self.confidence}, "
            f"source={self.source}, success={self.success})"
        )


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    Provides common functionality and enforces interface.
    """

    def __init__(self):
        self.logger = get_logger()

    @abstractmethod
    async def extract(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """
        Extract data from dealer website.

        Args:
            dealer_context: Browser context for the dealer
            page: Current page (if available)

        Returns:
            ExtractionResult with extracted data
        """
        pass

    async def extract_with_fallback(
        self,
        dealer_context: DealerContext,
        page: Optional[Page] = None
    ) -> ExtractionResult:
        """
        Extract with automatic fallback strategies.
        Default implementation just calls extract(), but can be overridden.
        """
        return await self.extract(dealer_context, page)

    def _create_result(
        self,
        data: Any,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        source: Optional[str] = None,
        evidence: Optional[str] = None,
        error: Optional[str] = None
    ) -> ExtractionResult:
        """Helper to create ExtractionResult."""
        return ExtractionResult(
            data=data,
            confidence=confidence,
            source=source,
            evidence=evidence,
            error=error
        )

    def _unsure_result(self, reason: str) -> ExtractionResult:
        """Helper to create an 'unsure' result."""
        return ExtractionResult(
            data=None,
            confidence=ConfidenceLevel.UNSURE,
            error=reason
        )
