"""Pipeline: PDF file -> text -> structured invoice -> Google Sheet row."""

from pathlib import Path

from llm.llm import extract_invoice
from models.models import Invoice
from utils.google_sheet_connection import SyncGoogleSheet
from utils.pdf_reader import PDFReader


def read_invoice(file_path: str | Path) -> Invoice:
    """Read a PDF and return its data as a validated Invoice, without storing it."""
    text = PDFReader(file_path).read_pdf()
    if not text:
        raise ValueError(f"No readable text found in {file_path}")

    return extract_invoice(text)


def register_invoice(file_path: str | Path, sheet: SyncGoogleSheet | None = None) -> Invoice:
    """Read a PDF and append its lines to the Google Sheet.

    Pass an existing `sheet` to reuse one connection across several invoices.
    """
    invoice = read_invoice(file_path)
    (sheet or SyncGoogleSheet()).add_invoice(invoice)
    return invoice
