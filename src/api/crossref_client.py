"""This is the Client for interacting with the Crossref API."""

import os
import re
import time
from typing import Dict, Optional, List
import requests
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class CrossrefClient:
    """Client for fetching paper metadata and PDFs from Crossref."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: Optional[str] = None):
        """Initialize the client for crossref.

        Args:
            email: Email for use of the API
        """
        self.email = email or os.getenv("CROSSREF_EMAIL")
        self.session = requests.Session()

        # Set the user agent
        if self.email:
            self.session.headers.update({
                "User-Agent": f"CrossrefDataExtraction/1.0 (mailto:{self.email})"
            })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_metadata(self, doi: str) -> Dict:
        """Fetch metadata for one of the paper from Crossref.

        Args:
            doi: The DOI of the paper

        Returns:
            Dictionary containing paper metadata
        """
        # Clean DOI and remove https://doi.org/ prefix if present
        doi = doi.replace("https://doi.org/", "")

        url = f"{self.BASE_URL}/{doi}"
        response = self.session.get(url)
        response.raise_for_status()

        return response.json()["message"]

    def download_pdf(self, doi: str, output_dir: Path) -> Optional[Path]:
        """Download PDF for a paper by using Selenium.

        Args:
            doi: The DOI of the paper
            output_dir: Directory to save the PDF

        Returns:
            Path to the downloaded PDF, or None if not available
        """
        # Clean DOI
        doi_clean = doi.replace("https://doi.org/", "")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from DOI
        filename = doi_clean.replace("/", "_") + ".pdf"
        output_path = output_dir / filename

        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Set download directory
        prefs = {
            "download.default_directory": str(output_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        driver = None
        try:
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=chrome_options)

            # Navigate to the DOI URL
            doi_url = f"https://doi.org/{doi_clean}"
            print(f"Navigating to: {doi_url}")
            driver.get(doi_url)

            # Wait for the page to load and find the download button
            wait = WebDriverWait(driver, 10)

            # Try different selectors for the download button
            download_selectors = [
                "//button[contains(text(), 'Download PDF')]",
                "//a[contains(text(), 'Download PDF')]",
                "//button[contains(@class, 'download')]//span[contains(text(), 'PDF')]",
                "//div[@class='dropdown-menu show']//a[contains(text(), 'Download PDF')]",
                "//button[@id='download-button']"
            ]

            download_clicked = False

            # First try to click the Download dropdown if it exists
            try:
                download_dropdown = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Download')]"))
                )
                download_dropdown.click()
                time.sleep(1)  # Wait for dropdown to open

                # Now look for PDF option in dropdown
                pdf_option = driver.find_element(By.XPATH, "//a[contains(text(), 'Download PDF')]")
                pdf_option.click()
                download_clicked = True
                print("Clicked PDF download from dropdown")

            except:
                # Try direct download button
                for selector in download_selectors:
                    try:
                        download_button = wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        download_button.click()
                        download_clicked = True
                        print(f"Clicked download button with selector: {selector}")
                        break
                    except:
                        continue

            if not download_clicked:
                # If no download button found, try direct PDF URL
                current_url = driver.current_url
                if "mdpi.com" in current_url:
                    pdf_url = current_url.rstrip('/') + "/pdf"
                    print(f"Trying direct PDF URL: {pdf_url}")
                    driver.get(pdf_url)
                    download_clicked = True

            if download_clicked:
                # Wait for download to complete
                print("Waiting for download to complete...")
                time.sleep(5)

                # Check if file was downloaded (with temporary name)
                temp_files = list(output_dir.glob("*.crdownload")) + list(output_dir.glob("*.tmp"))
                max_wait = 30  # Maximum 30 seconds wait
                wait_time = 0

                while temp_files and wait_time < max_wait:
                    time.sleep(1)
                    wait_time += 1
                    temp_files = list(output_dir.glob("*.crdownload")) + list(output_dir.glob("*.tmp"))

                # Look for the downloaded PDF
                pdf_files = list(output_dir.glob("*.pdf"))

                # Find the most recently downloaded PDF
                if pdf_files:
                    latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)

                    # Rename to our expected filename if different
                    if latest_pdf.name != filename:
                        latest_pdf.rename(output_path)

                    print(f"Successfully downloaded PDF to: {output_path}")
                    return output_path
                else:
                    print("No PDF file found after download attempt")

        except Exception as e:
            print(f"Error downloading PDF with Selenium: {e}")

        finally:
            if driver:
                driver.quit()

        # Fallback to requests method for direct PDF URLs
        return self._download_pdf_requests_fallback(doi_clean, output_path)

    def _download_pdf_requests_fallback(self, doi: str, output_path: Path) -> Optional[Path]:
        """Fallback method using requests for direct PDF downloads.

        Args:
            doi: Clean DOI (without https://doi.org/)
            output_path: Path to save the PDF

        Returns:
            Path to downloaded PDF or None
        """
        # Try constructing direct MDPI URL
        if "10.3390" in doi:
            try:
                # Get metadata to find the actual URL
                metadata = self.get_metadata(doi)

                if "URL" in metadata:
                    base_url = metadata["URL"]
                    pdf_url = base_url.rstrip('/') + "/pdf"

                    print(f"Fallback: Trying direct download from {pdf_url}")

                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    }

                    response = self.session.get(pdf_url, stream=True, headers=headers)
                    response.raise_for_status()

                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    print(f"Successfully downloaded PDF to: {output_path}")
                    return output_path

            except Exception as e:
                print(f"Fallback download failed: {e}")

        return None

    def extract_paper_info(self, metadata: Dict) -> Dict:
        """Extract relevant information from Crossref metadata.

        Args:
            metadata: Raw metadata from Crossref

        Returns:
            Dictionary with extracted information
        """
        # Extract authors
        authors = []
        if "author" in metadata:
            for author in metadata["author"]:
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors.append(name)

        # Extract other information
        return {
            "doi": metadata.get("DOI", ""),
            "title": metadata.get("title", [""])[0] if metadata.get("title") else "",
            "authors": authors,
            "publication_date": metadata.get("published-print", {}).get("date-parts", [[None]])[0],
            "journal": metadata.get("container-title", [""])[0] if metadata.get("container-title") else "",
            "publisher": metadata.get("publisher", ""),
            "abstract": metadata.get("abstract", "")
        }