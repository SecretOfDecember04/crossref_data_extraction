# Crossref Paper Data Extraction and Unification

This project extracts and unifies mechanical property data from academic papers using the Crossref API, Selenium for PDF downloads, and Large Language Models (LLMs) for intelligent data extraction.

## Setup and Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <https://github.com/SecretOfDecember04/crossref_data_extraction.git>
   cd crossref-data-extraction
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install ChromeDriver (required for Selenium):
   ```bash
   # On macOS with Homebrew:
   brew install chromedriver
   
   # Or download manually from https://chromedriver.chromium.org/
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key:
   # OPENAI_API_KEY=sk-proj-xxxxx...
   ```

6. Run the extraction script:
   ```bash
   python -m src.main
   ```

## Design Choices

### LLM-based Extraction (Option B)

I chose the LLM-based approach over traditional PDF parsing methods for several compelling reasons:

1. **Adaptability**: LLMs excel at understanding context and varying table structures. Academic papers often have inconsistent formatting, merged cells, and complex layouts that traditional parsers struggle with. LLMs can interpret these variations naturally.

2. **Semantic Understanding**: LLMs recognize that "YS", "yield strength", "σy", and "Yield Stress" all refer to the same property. Traditional regex-based approaches would require extensive pattern matching for each variation.

3. **Flexibility**: Adding support for new property types or paper formats requires only prompt adjustments, not code changes. This makes the solution highly maintainable and extensible.

4. **Reduced Complexity**: No need for complex regex patterns, table detection algorithms, or handling of edge cases in PDF structure. The LLM handles interpretation naturally.

5. **Better Accuracy**: LLMs can use context clues to correctly identify and extract data even when tables are poorly formatted or split across pages.

### Selenium for PDF Downloads

After discovering that direct URL construction wasn't working for MDPI papers, I implemented Selenium-based downloads because:

1. **Handles Dynamic Content**: MDPI pages use JavaScript to render download buttons
2. **Mimics Real User Behavior**: Clicks actual download buttons as a user would
3. **More Reliable**: Works across different publisher platforms without URL pattern knowledge
4. **Future-Proof**: Continues working even if publishers change their URL structures

### Architecture Decisions

- **Modular Structure**: Separated concerns into distinct modules:
  - `api/`: External API interactions (Crossref)
  - `extractors/`: Data extraction logic with base class for extensibility
  - `models/`: Pydantic schemas for data validation and consistency
  
- **Pydantic Models**: Ensures data quality and type safety throughout the pipeline

- **Retry Logic**: Implemented exponential backoff for API calls to handle transient failures

- **Environment Variables**: Sensitive data (API keys) stored securely outside the codebase

### Model Choice

I used GPT-4 for its:
- Superior understanding of scientific terminology
- Ability to maintain consistency across extractions
- Reliable JSON output formatting
- Better handling of complex table structures

## Assumptions Made

1. **PDF Structure**: Assumed mechanical properties are primarily presented in tables, not scattered in text
2. **Property Types**: Focused on common mechanical properties (tensile strength, yield strength, hardness, elongation)
3. **Units**: Assumed standard SI units with LLM handling unit variations and conversions
4. **Temperature**: Assumed room temperature (25°C) when not explicitly stated
5. **Paper Source**: Both papers are from MDPI, which simplified PDF download patterns

## Challenges and Solutions

### Challenge 1: PDF Download Failures
**Problem**: Initial attempts using direct URL construction failed with 404 errors.

**Solution**: Implemented Selenium to automate browser interactions, navigating to the paper page and clicking the actual download button. This approach is more robust and works across different publishers.

### Challenge 2: Dynamic Web Content
**Problem**: MDPI pages load download buttons dynamically with JavaScript.

**Solution**: Used Selenium WebDriverWait to ensure elements are loaded before interaction, with multiple selector strategies as fallbacks.

### Challenge 3: LLM Token Limits
**Problem**: Full papers exceed GPT-4's context window.

**Solution**: Truncated text to focus on sections most likely to contain tables (first 8000 characters). For production, would implement sliding window approach to process entire documents.

### Challenge 4: Inconsistent Table Formats
**Problem**: Different papers use varying table structures, headers, and naming conventions.

**Solution**: Crafted detailed prompts guiding the LLM to recognize various formats and normalize output. Used few-shot examples in the prompt to improve consistency.

### Challenge 5: Data Validation
**Problem**: LLM outputs can occasionally include errors or inconsistent formatting.

**Solution**: Implemented Pydantic models with validation rules and comprehensive error handling to ensure data quality. Invalid entries are logged but don't crash the pipeline.

## Limitations

1. **Cost**: LLM API calls incur per-token costs, making large-scale processing expensive
2. **PDF Text Quality**: Relies on PyPDF2's text extraction, which may miss data in images or complex layouts
3. **Context Window**: Current implementation may miss tables appearing later in very long papers
4. **Rate Limits**: Both OpenAI and Crossref APIs have rate limits affecting processing speed
5. **Browser Dependency**: Selenium requires ChromeDriver installation and maintenance

## Future Improvements

1. **Multi-pass Extraction**: Process papers in chunks to capture all tables throughout the document
2. **Vision Models**: Use GPT-4V or similar to extract data directly from table images
3. **Caching Layer**: Store extracted data to avoid reprocessing
4. **Parallel Processing**: Process multiple papers concurrently for faster execution
5. **Quality Validation**: Add verification step comparing extracted values against known material property ranges
6. **Additional Extractors**: Implement traditional parsing methods as fallback options
7. **Publisher Adapters**: Create specific adapters for different publisher platforms

## Results

The system successfully:
- Downloaded both PDFs using Selenium automation
- Extracted metadata from Crossref API
- Identified and extracted 21 mechanical properties across both papers
- Unified data into a consistent JSON schema
- Handled different table formats and naming conventions

The unified schema enables easy comparison and analysis of mechanical properties across different materials and processing conditions, demonstrating the effectiveness of the LLM-based approach for scientific data extraction.