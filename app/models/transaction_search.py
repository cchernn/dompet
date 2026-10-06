from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date as Date, datetime as DateTime
from decimal import Decimal
from uuid import UUID


class AttachmentRef(BaseModel):
    """A minimal attachment reference for search results -- id lets the
    caller fetch a fresh presigned download_url on demand via
    GET /attachments/{id} instead of one being generated eagerly for every
    attachment on every search page load."""

    id: UUID = Field(
        ...,
        title="Attachment ID",
    )
    filename: str = Field(
        ...,
        title="Attachment Filename",
    )


class TransactionSearchResult(BaseModel):
    """Shape of a row from dompet.vw_transactions -- distinct from
    Transaction (app/models/transaction.py): joined names instead of
    account ids, pipe-delimited tags/budgets split into lists. user_id is
    the transaction's owner (not necessarily the caller -- a shared-budget
    member sees other members' transactions too, per transactions_select's
    RLS policy). For those shared rows the owner's accounts aren't visible
    to the caller, so source/destination (and category/tags/locations) can
    be NULL. Active transactions only, since the view is already filtered."""

    id: UUID = Field(
        ...,
        title="Transaction ID",
    )
    date: Date = Field(
        ...,
        title="Transaction Date",
        description="Derived from the transaction's datetime",
    )
    datetime: DateTime = Field(
        ...,
        title="Transaction Date & Time",
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
    source: Optional[str] = Field(
        None,
        title="Source Account Name",
    )
    destination: Optional[str] = Field(
        None,
        title="Destination Account Name",
    )
    tags: List[str] = Field(
        default_factory=list,
        title="Tag Names",
    )
    attachments: List[AttachmentRef] = Field(
        default_factory=list,
        title="Attachments",
    )
    budgets: List[str] = Field(
        default_factory=list,
        title="Budget Names",
    )
    source_location: Optional[str] = Field(
        None,
        title="Source Location Name",
    )
    destination_location: Optional[str] = Field(
        None,
        title="Destination Location Name",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
