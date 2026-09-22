from unittest.mock import MagicMock, patch

import pytest

from utils.google_sheet_connection import (
    CREDENTIALS_FILE,
    NAME_GOOGLE_SHEET,
    SCOPES,
    SyncGoogleSheet,
)


@pytest.fixture
def fake_google():
    """Replace Google credentials and gspread so no test touches the network."""
    with (
        patch("utils.google_sheet_connection.Credentials") as credentials,
        patch("utils.google_sheet_connection.gspread") as gspread,
    ):
        worksheet = MagicMock(name="worksheet")
        worksheet.title = "Hoja 1"
        worksheet.row_count = 100
        worksheet.col_count = 20
        spreadsheet = MagicMock(name="spreadsheet")
        spreadsheet.get_worksheet.return_value = worksheet
        client = gspread.authorize.return_value
        client.open.return_value = spreadsheet
        client.open_by_key.return_value = spreadsheet
        yield {
            "credentials": credentials,
            "gspread": gspread,
            "client": client,
            "spreadsheet": spreadsheet,
            "worksheet": worksheet,
        }


@pytest.fixture
def sheet_id(monkeypatch):
    """Force the id-based path (Sheets API only)."""
    monkeypatch.setattr("utils.google_sheet_connection.settings.google_sheet_id", "SHEET-123")


@pytest.fixture
def no_sheet_id(monkeypatch):
    """Force the name-based path (also needs the Drive API)."""
    monkeypatch.setattr("utils.google_sheet_connection.settings.google_sheet_id", "")


def test_credentials_file_exists():
    assert CREDENTIALS_FILE.is_file(), f"Missing service account file: {CREDENTIALS_FILE}"


def test_service_account_email_is_readable():
    assert "@" in SyncGoogleSheet.service_account_email()


def test_get_client_uses_service_account_and_scopes(fake_google, no_sheet_id):
    SyncGoogleSheet()

    fake_google["credentials"].from_service_account_file.assert_called_with(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    assert fake_google["gspread"].authorize.called


def test_opens_by_name_when_no_sheet_id(fake_google, no_sheet_id):
    sync = SyncGoogleSheet()

    fake_google["client"].open.assert_called_once_with(NAME_GOOGLE_SHEET)
    fake_google["spreadsheet"].get_worksheet.assert_called_once_with(0)
    assert sync.sheet is fake_google["worksheet"]


def test_opens_by_key_when_sheet_id_is_set(fake_google, sheet_id):
    SyncGoogleSheet()

    fake_google["client"].open_by_key.assert_called_once_with("SHEET-123")
    assert not fake_google["client"].open.called


def test_add_new_row_appends_items_price_and_ammount(fake_google, sheet_id):
    sync = SyncGoogleSheet()

    sync.add_new_row("jamon", 1000, 1)

    fake_google["worksheet"].append_row.assert_called_once_with(["jamon", 1000, 1])


def test_check_connection_reports_worksheet_info(fake_google, sheet_id):
    info = SyncGoogleSheet().check_connection()

    assert info["title"] == "Hoja 1"
    assert info["rows"] == 100
    assert "@" in info["service_account"]


def test_authorizes_only_once_per_instance(fake_google, sheet_id):
    SyncGoogleSheet()

    # open_sheet must reuse self.client instead of building a second client
    assert fake_google["gspread"].authorize.call_count == 1


@pytest.mark.integration
def test_real_connection_is_alive():
    """Read-only check against Google. Run with: uv run pytest -m integration"""
    try:
        info = SyncGoogleSheet().check_connection()
    except Exception as error:  # noqa: BLE001 - we want a readable diagnosis
        pytest.fail(
            f"Could not connect: {type(error).__name__}: {error}\n"
            f"Check that: (1) the Sheets API is enabled, (2) GOOGLE_SHEET_ID is set in .env "
            f"or the Drive API is enabled, (3) the spreadsheet is shared with "
            f"{SyncGoogleSheet.service_account_email()}"
        )

    assert info["title"]
    assert info["rows"] > 0


@pytest.mark.integration
def test_real_add_new_row():
    """Writes a real row in Google Sheets. Run with: uv run pytest -m integration"""
    sheet = SyncGoogleSheet()
    sheet.add_new_row("jamon", 1000, 1)
