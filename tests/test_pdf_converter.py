import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError
from src.dimension_extractor.pdf_converter import PDFConverter
from hypothesis import given, strategies as st

@pytest.fixture
def converter():
    return PDFConverter(dpi=300)

def test_file_not_found(converter):
    with pytest.raises(FileNotFoundError):
        converter.convert_pdf_to_images(Path("nonexistent_file_999.pdf"))

@patch('src.dimension_extractor.pdf_converter.convert_from_path')
def test_convert_success(mock_convert, converter, tmp_path):
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.touch()
    
    mock_image = MagicMock(spec=Image.Image)
    mock_convert.return_value = [mock_image, mock_image]
    
    images = converter.convert_pdf_to_images(dummy_pdf)
    assert len(images) == 2
    mock_convert.assert_called_once_with(dummy_pdf, dpi=300)

@patch('src.dimension_extractor.pdf_converter.convert_from_path')
def test_encrypted_pdf_handling(mock_convert, converter, tmp_path):
    dummy_pdf = tmp_path / "encrypted.pdf"
    dummy_pdf.touch()
    
    mock_convert.side_effect = PDFPageCountError("Unable to get page count.")
    
    with pytest.raises(ValueError, match="encrypted or corrupted"):
        converter.convert_pdf_to_images(dummy_pdf)

@patch('src.dimension_extractor.pdf_converter.convert_from_path')
def test_corrupted_pdf_handling(mock_convert, converter, tmp_path):
    dummy_pdf = tmp_path / "corrupted.pdf"
    dummy_pdf.touch()
    
    mock_convert.side_effect = PDFSyntaxError("Syntax Error")
    
    with pytest.raises(ValueError, match="Corrupted PDF file"):
        converter.convert_pdf_to_images(dummy_pdf)

# Feature: dimension-extraction-system, Property 11: Multi-Page PDF Completeness
# Feature: dimension-extraction-system, Property 18: Image Resolution Preservation
@given(st.integers(min_value=1, max_value=50))
def test_property_pdf_converter_completeness_and_resolution(num_pages):
    converter = PDFConverter(dpi=300)
    dummy_pdf = Path(f"dummy_{num_pages}.pdf")
    
    with patch.object(Path, 'exists', return_value=True):
        with patch('src.dimension_extractor.pdf_converter.convert_from_path') as mock_convert:
            mock_image = MagicMock(spec=Image.Image)
            mock_convert.return_value = [mock_image for _ in range(num_pages)]
            
            images = converter.convert_pdf_to_images(dummy_pdf)
            
            assert len(images) == num_pages
            mock_convert.assert_called_once_with(dummy_pdf, dpi=300)
