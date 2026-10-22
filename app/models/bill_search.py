from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date
from decimal import Decimal
from uuid import UUID


class BillSearchResult(BaseModel):
    id: UUID = Field(..., title="Bill ID")
    name: str = Field(..., title="Bill Name")
    bill_date: date = Field(..., title="Bill Date")
    due_date: date = Field(..., title="Due Date")
    amount: Decimal = Field(..., title="Bill Amount")
    currency: str = Field(..., title="Currency Code")
    category: Optional[str] = Field(None, title="Category Name")
    account: Optional[str] = Field(None, title="Expected Payment Account Name")
    is_recurring: bool = Field(..., title="Is Recurring")
    paid_amount: Decimal = Field(..., title="Amount Paid So Far")
    status: Literal["unpaid", "partial", "paid"] = Field(
        ...,
        title="Status",
        description="Derived from bill_payments vs. amount, not stored",
    )
    is_overdue: bool = Field(..., title="Is Overdue")
    attachment_count: int = Field(..., title="Attachment Count")
