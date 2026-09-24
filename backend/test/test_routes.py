from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from models.models import Invoice, InvoiceItem

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DIGITAL_INVOICE = FIXTURES / "01_factura_electronica_digital.pdf"

FAKE_INVOICE = Invoice(
    invoice_number="FE-10458",
    supplier_name="TECNOSOLUCIONES ANDINAS S.A.S.",
    total=1071,
    items=[InvoiceItem(description="Portatil", quantity=1, unit_price=500, total=500)],
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Redirect uploads to a temporary folder so tests never write into the repo."""
    monkeypatch.setattr("routes.routes.PATH_FOLDER", tmp_path)
    return tmp_path


def pdf_payload(name="factura.pdf"):
    return {"file": (name, DIGITAL_INVOICE.read_bytes(), "application/pdf")}


def test_health_endpoint(client):
    response = client.get("/Health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_extracts_and_registers_the_invoice(client, upload_dir):
    with patch("routes.routes.register_invoice", return_value=FAKE_INVOICE) as register:
        response = client.post("/invoices/upload", files=pdf_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["registered"] is True
    assert body["filename"] == "factura.pdf"
    assert body["invoice"]["invoice_number"] == "FE-10458"
    assert (upload_dir / "factura.pdf").is_file()
    assert register.called


def test_upload_can_skip_registering(client, upload_dir):
    with (
        patch("routes.routes.read_invoice", return_value=FAKE_INVOICE) as read,
        patch("routes.routes.register_invoice") as register,
    ):
        response = client.post("/invoices/upload?register=false", files=pdf_payload())

    assert response.status_code == 201
    assert response.json()["registered"] is False
    assert read.called
    assert not register.called


def test_upload_rejects_non_pdf(client, upload_dir):
    response = client.post(
        "/invoices/upload", files={"file": ("nota.txt", b"hola", "text/plain")}
    )

    assert response.status_code == 415
    assert "Only PDF" in response.json()["detail"]
    # Nothing is written when the type is refused
    assert list(upload_dir.iterdir()) == []


def test_upload_strips_directory_traversal_from_the_filename(client, upload_dir):
    with patch("routes.routes.register_invoice", return_value=FAKE_INVOICE):
        response = client.post(
            "/invoices/upload", files=pdf_payload("../../../evil.pdf")
        )

    assert response.status_code == 201
    assert response.json()["filename"] == "evil.pdf"
    assert (upload_dir / "evil.pdf").is_file()
    assert not (upload_dir.parent.parent.parent / "evil.pdf").exists()


def test_upload_returns_422_when_the_pdf_has_no_text(client, upload_dir):
    with patch("routes.routes.register_invoice", side_effect=ValueError("No readable text")):
        response = client.post("/invoices/upload", files=pdf_payload())

    assert response.status_code == 422
    assert "No readable text" in response.json()["detail"]


def test_upload_returns_502_when_an_external_service_fails(client, upload_dir):
    with patch("routes.routes.register_invoice", side_effect=RuntimeError("API down")):
        response = client.post("/invoices/upload", files=pdf_payload())

    assert response.status_code == 502
    assert "API down" in response.json()["detail"]
