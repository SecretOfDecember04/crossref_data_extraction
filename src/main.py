"""Main script for extracting and unifying mechanical property data from papers."""

import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from .api.crossref_client import CrossrefClient
from .extractors.llm_extractor import LLMExtractor
from .models.schemas import PaperMetadata, ExtractedData, UnifiedResults

# Load environment variables
load_dotenv()

# Define the papers to process
PAPERS = [
    {
        "doi": "https://doi.org/10.3390/cryst9110586",
        "title": "Effect of ECAP on the Microstructure and Mechanical Properties of a Rolled Mg-2Y-0.6Nd-0.6Zr Magnesium Alloy"
    },
    {
        "doi": "https://doi.org/10.3390/met14111217",
        "title": "Investigation of Mechanical Properties and Microstructural Evolution in Pure Copper with Dual Heterostructures Produced by Surface Mechanical Attrition Treatment"
    }
]


def process_papers() -> List[ExtractedData]:
    """Process all papers and extract mechanical properties.

    Returns:
        List of ExtractedData objects
    """
    # Initialize clients
    crossref_client = CrossrefClient()
    llm_extractor = LLMExtractor()

    # Create directories
    pdf_dir = Path("data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for paper_info in PAPERS:
        print(f"\n{'=' * 60}")
        print(f"Processing paper: {paper_info['title'][:50]}...")
        print(f"DOI: {paper_info['doi']}")

        try:
            # Fetch metadata from Crossref
            print("\nFetching metadata from Crossref...")
            metadata = crossref_client.get_metadata(paper_info['doi'])
            extracted_info = crossref_client.extract_paper_info(metadata)

            # Create PaperMetadata object
            paper_metadata = PaperMetadata(
                doi=extracted_info['doi'],
                title=extracted_info['title'],
                authors=extracted_info['authors'],
                publication_date=str(extracted_info['publication_date'][0]) if extracted_info[
                    'publication_date'] else None,
                journal=extracted_info['journal']
            )

            # Download PDF
            print("\nDownloading PDF...")
            pdf_path = crossref_client.download_pdf(paper_info['doi'], pdf_dir)

            if not pdf_path:
                print(f"Failed to download PDF for {paper_info['doi']}")
                continue

            # Extract mechanical properties
            print("\nExtracting mechanical properties...")
            extracted_data = llm_extractor.extract_from_paper(pdf_path, paper_metadata)

            results.append(extracted_data)

        except Exception as e:
            print(f"Error processing paper {paper_info['doi']}: {e}")
            continue

    return results


def save_results(results: List[ExtractedData], output_path: Path):
    """Save the unified results to a JSON file.

    Args:
        results: List of extracted data
        output_path: Path to save the results
    """
    # Calculate statistics
    total_properties = sum(len(r.mechanical_properties) for r in results)

    # Create unified results
    unified = UnifiedResults(
        papers_processed=len(results),
        total_properties_extracted=total_properties,
        data=results
    )

    # Save to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unified.model_dump(), f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")
    print(f"Papers processed: {unified.papers_processed}")
    print(f"Total properties extracted: {unified.total_properties_extracted}")


def main():
    """Main entry point."""
    print("Starting Crossref Data Extraction and Unification")
    print("=" * 60)

    # Process papers
    results = process_papers()

    # Save results
    output_path = Path("output/results.json")
    save_results(results, output_path)

    print("\nExtraction complete!")


if __name__ == "__main__":
    main()