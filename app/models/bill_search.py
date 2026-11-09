from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date, datetime as DateTime
from decimal import Decimal
from uuid import UUID

from .transaction_search import AttachmentRef


class BillAttachmentRef(AttachmentRef):
    """AttachmentRef plus provenance -- a bill's attachments now merge
    attachments linked to the bill itself with attachments on any
    transaction linked via a payment. linked_via tells the frontend which
    unlink endpoint applies: DELETE /bills/{id}/attachments/{attachment_id}
    only removes a 'bill' link, not a 'transaction' one."""

    linked_via: List[Literal["bill", "transaction"]] = Field(
        ...,
        title="Linked Via",
        description="How this attachment reaches the bill -- directly, via a linked transaction, or both",
    )


class TransactionRef(BaseModel):
    """A minimal transaction reference, same spirit as AttachmentRef --
    enough for the frontend to show the linked transaction inline and
    navigate to GET /transactions/{id}, without a round trip per row."""

    id: UUID = Field(..., title="Transaction ID")
    name: str = Field(..., title="Transaction Name")
    datetime: DateTime = Field(..., title="Transaction Date & Time")
    amount: Decimal = Field(..., title="Transaction Amount")
    currency_code: str = Field(..., title="Currency Code")


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
    attachments: List[BillAttachmentRef] = Field(
        default_factory=list,
        title="Attachments",
        description="id/name/filename for each attachment linked to the bill directly or via a linked transaction -- fetch a fresh download_url via GET /attachments/{id}",
    )
    transaction_count: int = Field(
        ...,
        title="Linked Transaction Count",
        description="Count of distinct transactions linked via a bill_payments row, not the count of payments",
    )
    transactions: List[TransactionRef] = Field(
        default_factory=list,
        title="Linked Transactions",
        description="Distinct transactions linked to this bill via a payment, for navigating to GET /transactions/{id}",
    )
