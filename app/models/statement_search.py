from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date
from decimal import Decimal
from uuid import UUID

from .transaction_search import AttachmentRef


class StatementSearchResult(BaseModel):
    id: UUID = Field(..., title="Statement ID")
    account_id: UUID = Field(..., title="Account ID")
    account: str = Field(..., title="Account Name")
    statement_date: date = Field(..., title="Statement Date")
    period_start: date = Field(..., title="Period Start")
    period_end: date = Field(..., title="Period End")
    received_date: Optional[date] = Field(None, title="Received Date")
    status: Literal["pending", "received", "overdue"] = Field(
        ...,
        title="Status",
        description="Derived, not stored: received once received_date is set, overdue once statement_date has passed without one, otherwise pending",
    )
    is_recurring: bool = Field(..., title="Is Recurring")
    opening_balance: Optional[Decimal] = Field(None, title="Opening Balance")
    closing_balance: Optional[Decimal] = Field(None, title="Closing Balance")
    currency: Optional[str] = Field(None, title="Currency Code")
    notes: Optional[str] = Field(None, title="Notes")
    attachment_count: int = Field(..., title="Attachment Count")
    attachments: List[AttachmentRef] = Field(
        default_factory=list,
        title="Attachments",
        description="id/name/filename for each linked attachment -- fetch a fresh download_url via GET /attachments/{id}",
    )
