import logging
from pathlib import Path
from typing import List
from PIL import Image
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError, PDFInfoNotInstalledError

logger = logging.getLogger(__name__)

class PDFConverter:
    """Converts PDF files to PIL Images for extraction."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def convert(self, pdf_path: Path) -> List[Image.Image]:
        """Pipeline-friendly alias used by DimensionExtractor."""
        return self.convert_pdf_to_images(pdf_path)

    def convert_pdf_to_images(self, pdf_path: Path) -> List[Image.Image]:
        """
        Convert a single or multi-page PDF to a list of images.
        """
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            raise FileNotFoundError(f"File not found: {pdf_path}")

        try:
            images = convert_from_path(pdf_path, dpi=self.dpi)
            return images
        except PDFInfoNotInstalledError:
            logger.error("poppler is not installed or not in PATH.")
            raise
        except PDFPageCountError as e:
            logger.warning(f"Cannot read {pdf_path}. It might be encrypted or corrupted. Details: {e}")
            raise ValueError(f"Failed to read PDF {pdf_path}. It might be encrypted or corrupted.")
        except PDFSyntaxError as e:
            logger.warning(f"Syntax error in {pdf_path}. It is likely corrupted. Details: {e}")
            raise ValueError(f"Corrupted PDF file: {pdf_path}")
        except Exception as e:
            logger.error(f"Unexpected error converting {pdf_path}: {e}")
            raise
