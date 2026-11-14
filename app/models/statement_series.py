from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime
from uuid import UUID


class StatementSeries(BaseModel):
    id: UUID = Field(
        ...,
        title="Statement Series ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    account_id: UUID = Field(
        ...,
        title="Account ID",
        description="The account that issues these statements -- an account can have only one active series",
    )
    currency_code: Optional[str] = Field(
        None,
        title="Currency Code",
        description="Copied onto each generated statement, so balances recorded later have a currency",
        min_length=3,
        max_length=3,
    )
    recurrence_unit: Literal["day", "week", "month", "year"] = Field(
        ...,
        title="Recurrence Unit",
    )
    recurrence_count: int = Field(
        ...,
        title="Recurrence Count",
        description="e.g. 3 with recurrence_unit=month means every 3 months",
        gt=0,
    )
    anchor_date: date = Field(
        ...,
        title="Anchor Date",
        description="First occurrence's statement_date -- every occurrence's statement_date is computed as anchor_date + k * interval, never by accumulating onto a prior one",
    )
    is_active: bool = Field(
        True,
        title="Series Active Status",
        description="Deactivating stops future occurrences from being generated; existing ones are untouched",
    )
    created_at: datetime
    updated_at: datetime
