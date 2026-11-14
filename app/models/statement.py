from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class Statement(BaseModel):
    id: UUID = Field(
        ...,
        title="Statement ID",
        description="One occurrence -- either a standalone statement or a single cycle generated from a statement series",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    series_id: Optional[UUID] = Field(
        None,
        title="Statement Series ID",
        description="NULL for a standalone statement",
    )
    account_id: UUID = Field(
        ...,
        title="Account ID",
    )
    statement_date: date = Field(
        ...,
        title="Statement Date",
        description="The date the statement is issued, or expected to be",
    )
    period_start: date = Field(
        ...,
        title="Period Start",
        description="For a generated statement, the day after the previous occurrence's statement_date",
    )
    period_end: date = Field(
        ...,
        title="Period End",
        description="For a generated statement, the statement_date itself",
    )
    received_date: Optional[date] = Field(
        None,
        title="Received Date",
        description="NULL until the statement has actually been received -- this is what flips it from pending/overdue to received",
    )
    opening_balance: Optional[Decimal] = Field(
        None,
        title="Opening Balance",
    )
    closing_balance: Optional[Decimal] = Field(
        None,
        title="Closing Balance",
    )
    currency_code: Optional[str] = Field(
        None,
        title="Currency Code",
        min_length=3,
        max_length=3,
    )
    notes: Optional[str] = Field(
        None,
        title="Notes",
    )
    is_active: bool = Field(
        True,
        title="Statement Active Status",
    )
    created_at: datetime
    updated_at: datetime
