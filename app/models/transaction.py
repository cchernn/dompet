from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date as Date, datetime
from decimal import Decimal
from uuid import UUID


class Transaction(BaseModel):
    id: UUID = Field(
        ...,
        title="Transaction ID",
        description="Immutable internal identifier for the transaction",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
        description="Cognito UUID of the transaction owner",
    )
    date: Date = Field(
        ...,
        title="Transaction Date",
        description="The date the financial transaction occurred",
    )
    name: str = Field(
        ...,
        title="Transaction Name",
        min_length=1,
        max_length=255,
    )
    type: Literal["expenditure", "income", "transfer"] = Field(
        ...,
        title="Transaction Type",
    )
    amount: Decimal = Field(
        ...,
        title="Transaction Amount",
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
    source_account_id: UUID = Field(
        ...,
        title="Source Account ID",
        description="Account the money/activity originates from",
    )
    destination_account_id: UUID = Field(
        ...,
        title="Destination Account ID",
        description="Account the money/activity goes to",
    )
    is_active: bool = Field(
        True,
        title="Transaction Active Status",
    )
    created_at: datetime
    updated_at: datetime
