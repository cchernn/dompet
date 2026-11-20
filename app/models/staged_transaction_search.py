from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime as DateTime
from decimal import Decimal
from uuid import UUID


class StagedTransactionSearchResult(BaseModel):
    id: UUID = Field(..., title="Staged Transaction ID")
    status: Literal["draft", "approved", "discarded"] = Field(..., title="Status")
    origin: Literal["manual", "suggestion", "import"] = Field(..., title="Origin")
    origin_transaction_id: Optional[UUID] = Field(None, title="Origin Transaction ID")
    approved_transaction_id: Optional[UUID] = Field(None, title="Approved Transaction ID")
    name: Optional[str] = Field(None, title="Name")
    type: Optional[Literal["expenditure", "income", "transfer"]] = Field(None, title="Type")
    amount: Optional[Decimal] = Field(None, title="Amount")
    currency: Optional[str] = Field(None, title="Currency Code")
    category: Optional[str] = Field(None, title="Category Name")
    category_id: Optional[UUID] = Field(None, title="Category ID")
    source_account: Optional[str] = Field(None, title="Source Account Name")
    source_account_id: Optional[UUID] = Field(None, title="Source Account ID")
    destination_account: Optional[str] = Field(None, title="Destination Account Name")
    destination_account_id: Optional[UUID] = Field(None, title="Destination Account ID")
    source_location: Optional[str] = Field(None, title="Source Location Name")
    destination_location: Optional[str] = Field(None, title="Destination Location Name")
    datetime: Optional[DateTime] = Field(None, title="Transaction Datetime")
    notes: Optional[str] = Field(None, title="Notes")
    missing_fields: list[str] = Field(
        default_factory=list,
        title="Missing Fields",
        description="Fields that still block approval",
    )
    is_complete: bool = Field(..., title="Is Complete", description="True when nothing blocks approval")
    created_at: DateTime
    updated_at: DateTime
