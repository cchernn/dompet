from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class BillPayment(BaseModel):
    id: UUID = Field(
        ...,
        title="Bill Payment ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    bill_id: UUID = Field(
        ...,
        title="Bill ID",
    )
    transaction_id: Optional[UUID] = Field(
        None,
        title="Linked Transaction ID",
        description="Optional -- a payment can be recorded without tying it to a real ledger transaction",
    )
    amount_paid: Decimal = Field(
        ...,
        title="Amount Paid",
        description="The slice of a linked transaction's amount attributed to this bill, or simply what was paid if unlinked",
    )
    paid_date: date = Field(
        ...,
        title="Paid Date",
    )
    notes: Optional[str] = Field(
        None,
        title="Notes",
    )
    created_at: datetime
