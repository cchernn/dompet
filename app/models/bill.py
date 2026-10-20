from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class Bill(BaseModel):
    id: UUID = Field(
        ...,
        title="Bill ID",
        description="One occurrence -- either a one-off bill or a single cycle generated from a bill series",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    series_id: Optional[UUID] = Field(
        None,
        title="Bill Series ID",
        description="NULL for a one-off bill",
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
    due_date: date = Field(
        ...,
        title="Due Date",
    )
    is_active: bool = Field(
        True,
        title="Bill Active Status",
    )
    created_at: datetime
    updated_at: datetime
