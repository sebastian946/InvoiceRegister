from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from llm.llm import MODEL, PROMPT, extract_invoice, get_chain
from models.models import Invoice, InvoiceItem

FAKE_INVOICE = Invoice(
    invoice_number="FE-10458",
    issue_date=date(2026, 8, 14),
    supplier_name="TECNOSOLUCIONES ANDINAS S.A.S.",
    total=1000,
    items=[InvoiceItem(description="Portatil", quantity=1, unit_price=1000, total=1000)],
)


@pytest.fixture(autouse=True)
def clear_chain_cache():
    """get_chain is cached, so drop it between tests."""
    get_chain.cache_clear()
    yield
    get_chain.cache_clear()


def test_uses_a_current_model():
    # claude-2 and other retired ids would fail at call time
    assert MODEL == "claude-opus-5"


def test_prompt_asks_for_the_pdf_text():
    assert "pdf_text" in PROMPT.input_variables


def test_extract_invoice_returns_the_parsed_model():
    chain = MagicMock()
    chain.invoke.return_value = FAKE_INVOICE

    with patch("llm.llm.get_chain", return_value=chain):
        invoice = extract_invoice("texto de la factura")

    chain.invoke.assert_called_once_with({"pdf_text": "texto de la factura"})
    assert invoice.invoice_number == "FE-10458"
    assert invoice.items[0].total == 1000


def test_extract_invoice_rejects_empty_text():
    with pytest.raises(ValueError):
        extract_invoice("   ")


def test_chain_is_built_once():
    with patch("llm.llm.ChatAnthropic") as chat:
        chat.return_value.with_structured_output.return_value = MagicMock()
        get_chain()
        get_chain()

    assert chat.call_count == 1


def test_chain_is_configured_for_deterministic_extraction():
    with patch("llm.llm.ChatAnthropic") as chat:
        chat.return_value.with_structured_output.return_value = MagicMock()
        get_chain()

    kwargs = chat.call_args.kwargs
    assert kwargs["model"] == MODEL
    # Sampling parameters are rejected with a 400 on this model
    assert "temperature" not in kwargs
    assert "top_p" not in kwargs
    # json_schema avoids the forced tool call, which clashes with thinking
    chat.return_value.with_structured_output.assert_called_once_with(
        Invoice, method="json_schema"
    )


def test_sends_the_workspace_header_when_configured(monkeypatch):
    monkeypatch.setattr("llm.llm.settings.anthropic_workspace_id", "wrkspc_123")

    with patch("llm.llm.ChatAnthropic") as chat:
        chat.return_value.with_structured_output.return_value = MagicMock()
        get_chain()

    assert chat.call_args.kwargs["default_headers"] == {"anthropic-workspace-id": "wrkspc_123"}


def test_omits_the_workspace_header_when_not_configured(monkeypatch):
    monkeypatch.setattr("llm.llm.settings.anthropic_workspace_id", "")

    with patch("llm.llm.ChatAnthropic") as chat:
        chat.return_value.with_structured_output.return_value = MagicMock()
        get_chain()

    assert chat.call_args.kwargs["default_headers"] is None
