from .group import Group
from .attachment import Attachment

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

class Transaction(BaseModel):
    id: Optional[int] = Field(
        None, 
        title="Transaction ID", 
        description="The unique identifier for the transaction. Auto-generated",
    )
    date: datetime = Field(
        ..., 
        title="Transaction Date", 
        description="The date when the transaction occured in format YYYY-MM-DD",
    )
    name: str = Field(
        ..., 
        title="Transaction Name", 
        description="The name of the transaction", 
        min_length=1, 
        max_length=255,
    )
    type: Optional[Literal[
        "expenditure",
        "income",
        "transfer",
    ]] = Field(
        "expenditure", 
        title="Transaction Type",
        description="Type of transaction: expenditure, income or transfer. Default: expenditure",
    )
    amount: Optional[float] = Field(
        0.0,
        title="Transaction Amount",
        description="Amount of transaction by the transaction currency. Default: 0",
    )
    currency: Optional[str] = Field(
        None,
        title="Transaction Currency",
        description="Currency used for the transaction. Default: MYR",
        min_length=3,
        max_length=3,
    )
    payment_method: Optional[str] = Field(
        "cash",
        title="Transaction Payment Method",
        description="The method used for payment for the transaction. Default: cash",
        max_length=255,
    )
    category: Optional[str] = Field(
        None,
        title="Transaction Category",
        description="The category of the transaction",
        max_length=255,
    )
    is_active: Optional[bool] = Field(
        True,
        title="Transaction Active Status",
        description="Status to show if transaction is active or inactive. Default: True",
        exclude=True,
    )
    user: Optional[UUID] = Field(
        None,
        title="Transaction User ID",
        description="The user ID for the transaction in UUID format"
    )
    location: Optional[int] = Field(
        None,
        title="Transaction Location ID",
        description="The ID of the location associated with the transaction"
    )
    location_name: Optional[str] = Field(
        None,
        title="Transaction Location Name",
        description="The name of the location associated with the transaction"
    )
    groups: Optional[list[Group]] = Field(
        None,
        title="Transaction Groups",
        description="The list of transaction groups associated with the transaction"
    )
    attachments: Optional[list[Attachment]] = Field(
        None,
        title="Transaction Attachments",
        description="The list of attachments associated with the transaction"
    )