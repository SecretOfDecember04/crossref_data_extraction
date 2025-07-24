"""Base class for all extractors."""

from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path

from ..models.schemas import PaperMetadata, ExtractedData


class BaseExtractor(ABC):
    """Abstract base class for mechanical property extractors.

    This class defines the interface that all extractors must implement,
    allowing for different extraction methods (LLM, traditional parsing, etc.)
    while maintaining a consistent API.
    """

    @abstractmethod
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        pass

    @abstractmethod
    def extract_properties(self, text: str, paper_info: Dict) -> List[Dict]:
        """Extract mechanical properties from text.

        Args:
            text: Full text of the paper
            paper_info: Metadata about the paper

        Returns:
            List of extracted mechanical properties as dictionaries
        """
        pass

    @abstractmethod
    def extract_from_paper(self, pdf_path: Path, paper_metadata: PaperMetadata) -> ExtractedData:
        """Extract mechanical properties from a single paper.

        Args:
            pdf_path: Path to the PDF file
            paper_metadata: Metadata about the paper

        Returns:
            ExtractedData object with all extracted properties
        """
        pass