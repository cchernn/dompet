from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class BillSeries(BaseModel):
    id: UUID = Field(
        ...,
        title="Bill Series ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    name: str = Field(
        ...,
        title="Bill Name",
        max_length=255,
    )
    amount: Decimal = Field(
        ...,
        title="Bill Amount",
    )
    currency_code: str = Field(
        ...,
        title="Currency Code",
        min_length=3,
        max_length=3,
    )
    category_id: Optional[UUID] = Field(
        None,
        title="Category ID",
    )
    account_id: Optional[UUID] = Field(
        None,
        title="Expected Payment Account ID",
    )
    recurrence_unit: Literal["day", "week", "month", "year"] = Field(
        ...,
        title="Recurrence Unit",
    )
    recurrence_count: int = Field(
        ...,
        title="Recurrence Count",
        description="e.g. 2 with recurrence_unit=week means every 2 weeks",
        gt=0,
    )
    anchor_date: date = Field(
        ...,
        title="Anchor Date",
        description="First occurrence's bill_date (issue date), not due_date -- every occurrence's bill_date is computed as anchor_date + k * interval, never by accumulating onto a prior one. due_date defaults to the day before the following occurrence's bill_date",
    )
    is_active: bool = Field(
        True,
        title="Series Active Status",
        description="Deactivating stops future occurrences from being generated; existing ones are untouched",
    )
    created_at: datetime
    updated_at: datetime
