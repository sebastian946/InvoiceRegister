import json
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from utils.config_env import settings

CREDENTIALS_FILE = Path(__file__).resolve().parent / "invoicesheets-509421-a2d663b71839.json"
NAME_GOOGLE_SHEET = "Invoice Register"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SyncGoogleSheet:
    def __init__(self):
        self.client = self.get_client()
        self.sheet = self.open_sheet()

    @staticmethod
    def get_client():
        creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
        return gspread.authorize(creds)

    @staticmethod
    def service_account_email() -> str:
        """Email the spreadsheet must be shared with."""
        return json.loads(CREDENTIALS_FILE.read_text()).get("client_email", "")

    def open_sheet(self):
        if settings.google_sheet_id:
            # Only needs the Sheets API
            spreadsheet = self.client.open_by_key(settings.google_sheet_id)
        else:
            # Looking the spreadsheet up by name also requires the Drive API
            spreadsheet = self.client.open(NAME_GOOGLE_SHEET)
        return spreadsheet.get_worksheet(0)

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
