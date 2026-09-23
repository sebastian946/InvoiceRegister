"""Extraction of structured invoice data from raw PDF text.

This is a single structured-output call, not an agent: the model reads the text
and fills the Invoice schema directly. There is nothing for it to decide between
steps, so a tool-calling agent would only add cost and failure modes.
"""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from models.models import Invoice
from utils.config_env import settings

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You extract structured data from invoices written in Spanish or English.

Rules:
- Copy values exactly as they appear in the document. Do not invent data.
- Leave a field empty when the document does not contain it.
- Numbers must not carry thousand separators or currency symbols.
- Dates use the ISO format YYYY-MM-DD. Colombian invoices usually write DD/MM/YYYY.
- 'total' is the final amount to pay, taxes included."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Extract the invoice data from the following text:\n\n{pdf_text}"),
    ]
)


@lru_cache(maxsize=1)
def get_chain():
    """Build the extraction chain once and reuse it.

    Built lazily so importing this module does not require a valid API key.
    """
    # An org-level key needs the workspace stated explicitly; a workspace-scoped
    # key carries it already and needs no header.
    headers = (
        {"anthropic-workspace-id": settings.anthropic_workspace_id}
        if settings.anthropic_workspace_id
        else None
    )

    # No temperature: sampling parameters were removed on this model and the
    # API rejects them with a 400. Determinism comes from the JSON schema.
    llm = ChatAnthropic(
        model=MODEL,
        api_key=settings.anthropic_api_key.get_secret_value(),
        max_tokens=4096,
        default_headers=headers,
    )
    # json_schema uses structured outputs instead of a forced tool call,
    # which keeps it compatible with extended thinking.
    return PROMPT | llm.with_structured_output(Invoice, method="json_schema")


def extract_invoice(pdf_text: str) -> Invoice:
    """Turn the raw text of an invoice into a validated Invoice object."""
    if not pdf_text or not pdf_text.strip():
        raise ValueError("pdf_text is empty: the PDF produced no readable text")

    return get_chain().invoke({"pdf_text": pdf_text})
