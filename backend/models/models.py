from datetime import date

from pydantic import BaseModel, Field


class InvoiceItem(BaseModel):
    """A single line of the invoice."""

    description: str = Field(..., description="Description of the product or service")
    quantity: float = Field(1, description="Number of units billed")
    unit_price: float = Field(0, description="Price of a single unit, without taxes")
    total: float = Field(0, description="Total for this line: quantity * unit_price")


class Invoice(BaseModel):
    """Structured invoice data extracted from the text of a PDF."""

    invoice_number: str | None = Field(
        None, description="Invoice number or consecutive identifier, e.g. FE-10458"
    )
    issue_date: date | None = Field(None, description="Date the invoice was issued")
    due_date: date | None = Field(None, description="Date the invoice is due")
    supplier_name: str | None = Field(None, description="Name of the company issuing the invoice")
    supplier_tax_id: str | None = Field(None, description="Tax id of the supplier, e.g. NIT")
    customer_name: str | None = Field(None, description="Name of the company being billed")
    currency: str = Field("COP", description="ISO currency code, e.g. COP or USD")
    subtotal: float = Field(0, description="Total before taxes")
    tax: float = Field(0, description="Total taxes, e.g. IVA")
    total: float = Field(0, description="Final amount to pay, taxes included")
    items: list[InvoiceItem] = Field(
        default_factory=list, description="Lines detailing what is being billed"
    )
