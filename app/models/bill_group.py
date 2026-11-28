from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date
from decimal import Decimal
from uuid import UUID


class BillGroup(BaseModel):
    kind: Literal["series", "one_off"] = Field(
        ...,
        title="Kind",
        description="'series' opens its occurrences via GET /bills/search?series_id=<id>; 'one_off' is itself a single bill, GET /bills/{id}",
    )
    id: UUID = Field(..., title="Series ID or Bill ID", description="A bill_series id when kind is 'series', a bill id when 'one_off'")
    name: str = Field(..., title="Name")
    amount: Decimal = Field(..., title="Amount", description="Latest occurrence's amount for a series, the bill's amount for a one-off")
    currency: str = Field(..., title="Currency Code")
    category: Optional[str] = Field(None, title="Category Name")
    account: Optional[str] = Field(None, title="Expected Payment Account Name")
    recurrence_unit: Optional[Literal["day", "week", "month", "year"]] = Field(None, title="Recurrence Unit", description="Null for a one-off")
    recurrence_count: Optional[int] = Field(None, title="Recurrence Count", description="Null for a one-off")
    is_active: bool = Field(..., title="Active", description="False for a deactivated series that still has unpaid occurrences")
    occurrence_count: int = Field(..., title="Occurrence Count", description="1 for a one-off")
    unpaid_count: int = Field(..., title="Unpaid Occurrence Count", description="Occurrences that are unpaid or only partly paid")
    overdue_count: int = Field(..., title="Overdue Occurrence Count")
    next_due_date: Optional[date] = Field(None, title="Next Due Date", description="Earliest due date among unpaid occurrences; null when everything is paid")
    latest_status: Optional[Literal["unpaid", "partial", "paid"]] = Field(None, title="Latest Occurrence Status")
    latest_bill_date: Optional[date] = Field(None, title="Latest Occurrence Bill Date")
    requires_document: bool = Field(..., title="Requires Document", description="The series' current setting; always false for a one-off")
    awaiting_document_count: int = Field(..., title="Occurrences Awaiting Document", description="Occurrences that need a document that hasn't arrived or been confirmed")
