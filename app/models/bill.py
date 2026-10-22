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
    bill_date: date = Field(
        ...,
        title="Bill Date",
        description="The date the bill was issued (e.g. a statement date), distinct from due_date",
    )
    due_date: date = Field(
        ...,
        title="Due Date",
        description="Defaults to the day before the series' next bill_date for a recurring bill, or to bill_date itself for a one-off bill, unless given explicitly",
    )
    is_active: bool = Field(
        True,
        title="Bill Active Status",
    )
    created_at: datetime
    updated_at: datetime
