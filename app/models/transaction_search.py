from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date as Date
from decimal import Decimal
from uuid import UUID


class TransactionSearchResult(BaseModel):
    """Shape of a row from dompet.vw_transactions -- distinct from
    Transaction (app/models/transaction.py): joined names instead of ids,
    no user_id/account ids, pipe-delimited tags/attachments split into
    lists. Active transactions only, since the view is already filtered."""

    id: UUID = Field(
        ...,
        title="Transaction ID",
    )
    date: Date = Field(
        ...,
        title="Transaction Date",
        description="Derived from the transaction's datetime",
    )
    name: str = Field(
        ...,
        title="Transaction Name",
    )
    type: Literal["expenditure", "income", "transfer"] = Field(
        ...,
        title="Transaction Type",
    )
    amount: Decimal = Field(
        ...,
        title="Transaction Amount",
    )
    currency: str = Field(
        ...,
        title="Currency Code",
    )
    category: Optional[str] = Field(
        None,
        title="Category Name",
    )
    source: str = Field(
        ...,
        title="Source Account Name",
    )
    destination: str = Field(
        ...,
        title="Destination Account Name",
    )
    tags: List[str] = Field(
        default_factory=list,
        title="Tag Names",
    )
    attachments: List[str] = Field(
        default_factory=list,
        title="Attachment Filenames",
    )
