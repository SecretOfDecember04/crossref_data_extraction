"""Data Models for the crossref data extraction project."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class MechanicalProperty(BaseModel):
    """Stands for a single mechanical property measurement"""

    material: str = Field(..., description="Material or alloy composition")
    condition: Optional[str] = Field(None, description="Processing condition or treatment")
    property_name: str = Field(..., description="Name of the mechanical property")
    value: float = Field(..., description="Numerical value of the property")
    unit: str = Field(..., description="Unit of measurement")
    temperature: Optional[float] = Field(None, description="Test temperature if applicable")
    temperature_unit: Optional[str] = Field(None, description="Temperature unit")
    strain_rate: Optional[float] = Field(None, description="Strain rate if applicable")
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any additional parameters")


class PaperMetadata(BaseModel):
    """Metadata about the source paper."""

    doi : str
    title: str
    authors: List[str]
    publication_date: Optional[str] = None
    journal: Optional[str] = None

class ExtractedData(BaseModel):
    """Complete extracted data from a paper."""

    paper_metadata: PaperMetadata
    mechanical_properties: List[MechanicalProperty]
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    extraction_method: str = "llm"

class UnifiedResults(BaseModel):
    """Final unified results from all papers."""
    extraction_date: datetime = Field(default_factory=datetime.now)
    papers_processed: int
    total_properties_extracted: int
    data: List[ExtractedData]

