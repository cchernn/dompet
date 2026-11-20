from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime as DateTime
from decimal import Decimal
from uuid import UUID


class StagedTransaction(BaseModel):
    id: UUID = Field(
        ...,
        title="Staged Transaction ID",
        description="A draft transaction awaiting approval; nearly every field is optional until it is approved",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    status: Literal["draft", "approved", "discarded"] = Field(
        ...,
        title="Status",
    )
    origin: Literal["manual", "suggestion", "import"] = Field(
        ...,
        title="Origin",
        description="Where the draft came from; 'import' is reserved for a later phase",
    )
    origin_transaction_id: Optional[UUID] = Field(
        None,
        title="Origin Transaction ID",
        description="The transaction a suggestion-sourced draft was copied from",
    )
    approved_transaction_id: Optional[UUID] = Field(
        None,
        title="Approved Transaction ID",
        description="The real transaction this draft became, once approved",
    )
    name: Optional[str] = Field(None, title="Name", max_length=255)
    type: Optional[Literal["expenditure", "income", "transfer"]] = Field(None, title="Type")
    amount: Optional[Decimal] = Field(None, title="Amount")
    currency_code: Optional[str] = Field(None, title="Currency Code", min_length=3, max_length=3)
    category_id: Optional[UUID] = Field(None, title="Category ID")
    source_account_id: Optional[UUID] = Field(None, title="Source Account ID")
    destination_account_id: Optional[UUID] = Field(None, title="Destination Account ID")
    source_location_id: Optional[UUID] = Field(None, title="Source Location ID")
    destination_location_id: Optional[UUID] = Field(None, title="Destination Location ID")
    datetime: Optional[DateTime] = Field(None, title="Transaction Datetime")
    notes: Optional[str] = Field(None, title="Notes")
    tag_ids: list[UUID] = Field(default_factory=list, title="Tag IDs")
    budget_ids: list[UUID] = Field(default_factory=list, title="Budget IDs")
    attachment_ids: list[UUID] = Field(default_factory=list, title="Attachment IDs")
    created_at: DateTime
    updated_at: DateTime
