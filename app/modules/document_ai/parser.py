import hashlib
import io
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pdfplumber
import fitz  # PyMuPDF
import pandas as pd
from PIL import Image

logger = logging.getLogger(__name__)

# Check Tesseract availability safely
try:
    import pytesseract
    # Test if tesseract is accessible
    _TESSERACT_AVAILABLE = True
except Exception:
    _TESSERACT_AVAILABLE = False


def compute_sha256(file_bytes: bytes) -> str:
    """Calculates the SHA-256 cryptographic hash of a file's raw bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def extract_from_digital_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Extracts text page-by-page from digital PDFs using PyMuPDF and pdfplumber."""
    pages_data = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        # Fallback to pdfplumber if PyMuPDF returns minimal or empty layout text
        if not text.strip():
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    if page_num < len(pdf.pages):
                        text = pdf.pages[page_num].extract_text() or ""
            except Exception as e:
                logger.warning(f"pdfplumber fallback failed on page {page_num}: {e}")

        pages_data.append(
            {
                "page_number": page_num + 1,
                "text": text.strip(),
                "is_ocr": False,
            }
        )
    return pages_data


def extract_from_scanned_image(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Applies Tesseract OCR to extract text from scanned image formats (PNG, JPEG, TIFF)."""
    ocr_text = ""
    try:
        if _TESSERACT_AVAILABLE:
            image = Image.open(io.BytesIO(file_bytes))
            ocr_text = pytesseract.image_to_string(image)
    except Exception as e:
        logger.warning(f"Tesseract OCR not accessible: {e}. Falling back to metadata.")
        ocr_text = "[Scanned image detected. OCR engine not found on host system PATH.]"

    return [
        {
            "page_number": 1,
            "text": ocr_text.strip(),
            "is_ocr": True,
        }
    ]


def extract_from_spreadsheet(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Reads Excel (.xlsx, .xls) or CSV files into structured string representations."""
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))

    # Convert dataframe to a readable text representation for field extraction
    structured_text = df.to_string(index=False)
    return [
        {
            "page_number": 1,
            "text": structured_text,
            "is_ocr": False,
        }
    ]


def parse_document(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Master entrypoint for multi-format document ingestion."""
    sha256_hash = compute_sha256(file_bytes)
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        pages = extract_from_digital_pdf(file_bytes)
        # If no text was found on any page, fall back to OCR on rendered pages
        if not any(p["text"] for p in pages):
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            ocr_pages = []
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = ""
                try:
                    if _TESSERACT_AVAILABLE:
                        text = pytesseract.image_to_string(img)
                except Exception as e:
                    logger.warning(f"OCR failed for rendered page {page_num}: {e}")
                    text = f"[Scanned page {page_num + 1} - OCR unavailable]"

                ocr_pages.append(
                    {
                        "page_number": page_num + 1,
                        "text": text.strip(),
                        "is_ocr": True,
                    }
                )
            pages = ocr_pages
    elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
        pages = extract_from_scanned_image(file_bytes)
    elif ext in [".csv", ".xlsx", ".xls"]:
        pages = extract_from_spreadsheet(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return sha256_hash, pages
