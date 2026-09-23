import json
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from utils.config_env import settings

CREDENTIALS_FILE = Path(__file__).resolve().parent / "invoicesheets-509421-a2d663b71839.json"
NAME_GOOGLE_SHEET = "Invoice Register"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Summary tab: one row per invoice. Must match row 1 of the first worksheet.
HEADERS = ["Número", "Emisión", "Vencimiento", "Proveedor", "NIT", "Cliente", "Total"]

# Detail tab: one row per invoice line, linked to the summary by "Número".
DETAIL_SHEET_TITLE = "Detalle"
DETAIL_HEADERS = ["Número", "Descripción", "Cantidad", "Precio unitario", "Total"]


class SyncGoogleSheet:
    def __init__(self):
        self.client = self.get_client()
        self.spreadsheet = self.open_spreadsheet()
        self.sheet = self.spreadsheet.get_worksheet(0)
        self._detail_sheet = None

    @staticmethod
    def get_client():
        creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
        return gspread.authorize(creds)

    @staticmethod
    def service_account_email() -> str:
        """Email the spreadsheet must be shared with."""
        return json.loads(CREDENTIALS_FILE.read_text()).get("client_email", "")

    def open_spreadsheet(self):
        if settings.google_sheet_id:
            # Only needs the Sheets API
            return self.client.open_by_key(settings.google_sheet_id)
        # Looking the spreadsheet up by name also requires the Drive API
        return self.client.open(NAME_GOOGLE_SHEET)

    @property
    def detail_sheet(self):
        """The detail tab, created with its headers the first time it is needed."""
        if self._detail_sheet is None:
            try:
                self._detail_sheet = self.spreadsheet.worksheet(DETAIL_SHEET_TITLE)
            except WorksheetNotFound:
                self._detail_sheet = self.spreadsheet.add_worksheet(
                    title=DETAIL_SHEET_TITLE, rows=1000, cols=len(DETAIL_HEADERS)
                )
                self._detail_sheet.append_row(DETAIL_HEADERS)
        return self._detail_sheet

    def check_connection(self) -> dict:
        """Read-only probe. Returns basic worksheet info without modifying anything."""
        return {
            "service_account": self.service_account_email(),
            "title": self.sheet.title,
            "rows": self.sheet.row_count,
            "cols": self.sheet.col_count,
        }

    def add_new_row(self, items: str, price: int, ammount: int):
        row_data = [items, price, ammount]
        self.sheet.append_row(row_data)

    def add_invoice(self, invoice) -> list:
        """Write the invoice summary, plus one detail row per line.

        The two tabs are linked by the invoice number. Returns the summary row.
        """
        row = [
            invoice.invoice_number or "",
            invoice.issue_date.isoformat() if invoice.issue_date else "",
            invoice.due_date.isoformat() if invoice.due_date else "",
            invoice.supplier_name or "",
            invoice.supplier_tax_id or "",
            invoice.customer_name or "",
            invoice.total,
        ]
        self.sheet.append_row(row)

        if invoice.items:
            self.detail_sheet.append_rows(
                [
                    [
                        invoice.invoice_number or "",
                        item.description,
                        item.quantity,
                        item.unit_price,
                        item.total,
                    ]
                    for item in invoice.items
                ]
            )

        return row
