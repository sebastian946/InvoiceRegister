from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from controllers.invoice_controller import read_invoice, register_invoice
from models.models import Invoice, InvoiceItem

FILES = Path(__file__).resolve().parent / "fixtures"
DIGITAL_INVOICE = FILES / "01_factura_electronica_digital.pdf"

FAKE_INVOICE = Invoice(
    invoice_number="FE-10458",
    supplier_name="TECNOSOLUCIONES ANDINAS S.A.S.",
    subtotal=900,
    total=1071,
    items=[
        InvoiceItem(description="Portatil", quantity=1, unit_price=500, total=500),
        InvoiceItem(description="Monitor", quantity=2, unit_price=200, total=400),
    ],
)


def test_read_invoice_sends_the_pdf_text_to_the_llm():
    with patch("controllers.invoice_controller.extract_invoice", return_value=FAKE_INVOICE) as llm:
        invoice = read_invoice(DIGITAL_INVOICE)

    text_sent = llm.call_args.args[0]
    assert "FE-10458" in text_sent  # real text read from the PDF
    assert invoice is FAKE_INVOICE


def test_read_invoice_fails_when_the_pdf_has_no_text():
    with patch("controllers.invoice_controller.PDFReader") as reader:
        reader.return_value.read_pdf.return_value = None

        with pytest.raises(ValueError):
            read_invoice("empty.pdf")


def test_register_invoice_writes_one_row_per_item():
    sheet = MagicMock()

    with patch("controllers.invoice_controller.read_invoice", return_value=FAKE_INVOICE):
        register_invoice(DIGITAL_INVOICE, sheet=sheet)

    sheet.add_invoice.assert_called_once_with(FAKE_INVOICE)


def _offline_sheet():
    """A SyncGoogleSheet with both tabs mocked and no __init__ / network."""
    from utils.google_sheet_connection import SyncGoogleSheet

    sync = SyncGoogleSheet.__new__(SyncGoogleSheet)
    sync.sheet = MagicMock()
    sync._detail_sheet = MagicMock()
    return sync


def test_add_invoice_writes_one_row_in_the_header_order():
    from utils.google_sheet_connection import HEADERS

    sync = _offline_sheet()

    row = sync.add_invoice(FAKE_INVOICE)

    assert len(row) == len(HEADERS)
    sync.sheet.append_row.assert_called_once_with(
        [
            "FE-10458",
            "",  # FAKE_INVOICE carries no issue_date
            "",
            "TECNOSOLUCIONES ANDINAS S.A.S.",
            "",
            "",
            1071.0,
        ]
    )


def test_add_invoice_writes_empty_strings_for_missing_fields():
    from utils.google_sheet_connection import HEADERS

    sync = _offline_sheet()

    row = sync.add_invoice(Invoice(total=12))

    assert row == ["", "", "", "", "", "", 12]
    assert len(row) == len(HEADERS)


def test_add_invoice_writes_the_lines_into_the_detail_tab():
    from utils.google_sheet_connection import DETAIL_HEADERS

    sync = _offline_sheet()

    sync.add_invoice(FAKE_INVOICE)

    sync._detail_sheet.append_rows.assert_called_once_with(
        [
            ["FE-10458", "Portatil", 1.0, 500.0, 500.0],
            ["FE-10458", "Monitor", 2.0, 200.0, 400.0],
        ]
    )
    # Every detail row carries the invoice number that links it to the summary
    written = sync._detail_sheet.append_rows.call_args.args[0]
    assert all(len(r) == len(DETAIL_HEADERS) for r in written)
    assert all(r[0] == "FE-10458" for r in written)


def test_add_invoice_skips_the_detail_tab_without_lines():
    sync = _offline_sheet()

    sync.add_invoice(Invoice(invoice_number="X-1", total=5))

    assert not sync._detail_sheet.append_rows.called


@pytest.mark.integration
def test_real_extraction_from_a_pdf():
    """Calls the Claude API. Run with: uv run pytest -m integration"""
    invoice = read_invoice(DIGITAL_INVOICE)

    assert invoice.invoice_number == "FE-10458"
    assert invoice.supplier_name and "TECNOSOLUCIONES" in invoice.supplier_name.upper()
    assert invoice.total > 0
    assert invoice.items
