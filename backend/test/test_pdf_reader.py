from pathlib import Path
from unittest.mock import patch

import pdfplumber
import pytest

from utils.pdf_reader import PDFReader

FILES = Path(__file__).resolve().parent.parent / "files_upload"
DIGITAL_INVOICE = FILES / "01_factura_electronica_digital.pdf"
SCANNED_INVOICE = FILES / "02_factura_escaneada_imagen.pdf"
EXPENSE_REFUND_FORM = FILES / "03_formulario_reembolso_gastos.pdf"


def test_digital_invoice_returns_text():
    text = PDFReader(DIGITAL_INVOICE).read_pdf()
    assert isinstance(text, str)
    # Only check that fragments are present, regardless of order
    for fragment in ("FACTURA ELECTRÓNICA DE VENTA", "FE-10458", "TECNOSOLUCIONES ANDINAS"):
        assert fragment in text


def test_expense_refund_form_returns_text():
    text = PDFReader(EXPENSE_REFUND_FORM).read_pdf()

    assert isinstance(text, str)
    for fragment in ("REEMBOLSO DE GASTOS", "RG-2026-0419", "Laura Camila Restrepo"):
        assert fragment in text


def test_identifies_content_type():
    with pdfplumber.open(DIGITAL_INVOICE) as pdf:
        assert PDFReader.identify_type_content(pdf) == "plain_text"
    with pdfplumber.open(SCANNED_INVOICE) as pdf:
        assert PDFReader.identify_type_content(pdf) == "image"


def test_scanned_invoice_uses_ocr():
    # Mock tesseract so the test does not depend on the binary being installed
    with patch("utils.pdf_reader.pytesseract.image_to_string", return_value="FACTURA 123") as ocr:
        text = PDFReader(SCANNED_INVOICE).read_pdf()

    assert ocr.called
    assert ocr.call_args.kwargs["lang"] == "spa"
    assert "FACTURA 123" in text


def test_missing_pdf_raises_error():
    with pytest.raises(FileNotFoundError):
        PDFReader(FILES / "does_not_exist.pdf").read_pdf()
