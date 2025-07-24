"""LLM-based extractor for mechanical properties from PDFs."""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import PyPDF2
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_extractor import BaseExtractor
from ..models.schemas import MechanicalProperty, PaperMetadata, ExtractedData


class LLMExtractor(BaseExtractor):
    """Extract mechanical properties from PDFs using Large Language Models."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the LLM extractor.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo-preview)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        text = ""

        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)

            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"

        return text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def extract_properties(self, text: str, paper_info: Dict) -> List[Dict]:
        """Use LLM to extract mechanical properties from text.

        Args:
            text: Full text of the paper
            paper_info: Metadata about the paper

        Returns:
            List of extracted mechanical properties
        """
        # Create a focused prompt for mechanical property extraction
        system_prompt = """You are an expert materials scientist tasked with extracting mechanical property data from academic papers. 
        Focus on finding tabular data that reports mechanical properties such as:
        - Tensile strength (UTS, YS)
        - Hardness (HV, HB, etc.)
        - Elongation
        - Young's modulus
        - Yield strength
        - Other mechanical properties

        Extract ONLY data that appears in tables, not from the text discussion.
        For each property found, provide:
        1. Material/alloy composition
        2. Processing condition or treatment (if mentioned)
        3. Property name
        4. Numerical value
        5. Unit of measurement
        6. Test temperature (if mentioned)
        7. Any other relevant parameters

        Return the data as a JSON array of objects."""

        user_prompt = f"""Paper Title: {paper_info.get('title', 'Unknown')}

Please extract all mechanical property data from the tables in this paper. Focus on finding structured tabular data.

Paper text:
{text[:8000]}  # Limit text to avoid token limits

Return the extracted data as a JSON array. Each object should have these fields:
- material: string (material or alloy composition)
- condition: string or null (processing condition)
- property_name: string
- value: number
- unit: string
- temperature: number or null
- temperature_unit: string or null
- strain_rate: number or null
- additional_info: object (any other parameters)
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                response_format={"type": "json_object"}
            )

            # Parse the response
            content = response.choices[0].message.content
            data = json.loads(content)

            # Handle different response formats
            if isinstance(data, dict):
                # If the LLM wrapped the array in an object
                if "properties" in data:
                    return data["properties"]
                elif "data" in data:
                    return data["data"]
                else:
                    # Try to find the first array value
                    for value in data.values():
                        if isinstance(value, list):
                            return value
            elif isinstance(data, list):
                return data

            return []

        except Exception as e:
            print(f"Error in LLM extraction: {e}")
            return []

    def extract_from_paper(self, pdf_path: Path, paper_metadata: PaperMetadata) -> ExtractedData:
        """Extract mechanical properties from a single paper.

        Args:
            pdf_path: Path to the PDF file
            paper_metadata: Metadata about the paper

        Returns:
            ExtractedData object with all extracted properties
        """
        # Extract text from PDF
        print(f"Extracting text from {pdf_path.name}...")
        text = self.extract_text_from_pdf(pdf_path)

        # Use LLM to extract properties
        print(f"Extracting mechanical properties using {self.model}...")
        raw_properties = self.extract_properties(
            text,
            paper_metadata.model_dump()
        )

        # Convert to MechanicalProperty objects
        properties = []
        for prop in raw_properties:
            try:
                # Clean up the data
                if isinstance(prop.get("value"), str):
                    # Try to extract numeric value
                    prop["value"] = float(prop["value"].replace(",", ""))

                mechanical_property = MechanicalProperty(**prop)
                properties.append(mechanical_property)
            except Exception as e:
                print(f"Error parsing property: {prop}, Error: {e}")
                continue

        print(f"Extracted {len(properties)} mechanical properties")

        return ExtractedData(
            paper_metadata=paper_metadata,
            mechanical_properties=properties,
            extraction_method="llm"
        )