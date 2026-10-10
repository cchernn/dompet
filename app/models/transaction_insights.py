from pydantic import BaseModel, Field
from typing import List
from decimal import Decimal

from .insights import Bucket, TrendPoint, BudgetBreakdown


class CategoryBreakdown(BaseModel):
    category: str = Field(..., title="Category Name")
    total: Decimal = Field(..., title="Total Amount")
    count: int = Field(..., title="Transaction Count")


class AccountBreakdown(BaseModel):
    account: str = Field(
        ...,
        title="Source Account Name",
        description="Grouped by source account -- where money left from",
    )
    total: Decimal = Field(..., title="Total Amount")
    count: int = Field(..., title="Transaction Count")


class DestinationAccountBreakdown(BaseModel):
    account: str = Field(
        ...,
        title="Destination Account Name",
        description="Grouped by destination account -- where money went",
    )
    total: Decimal = Field(..., title="Total Amount")
    count: int = Field(..., title="Transaction Count")


class TransactionSummary(BaseModel):
    total_income: Decimal = Field(..., title="Total Income")
    total_expense: Decimal = Field(..., title="Total Expense")
    net: Decimal = Field(..., title="Net")
    transaction_count: int = Field(..., title="Transaction Count")
    by_category: List[CategoryBreakdown] = Field(default_factory=list, title="By Category")
    by_account: List[AccountBreakdown] = Field(default_factory=list, title="By Account")
    by_destination_account: List[DestinationAccountBreakdown] = Field(
        default_factory=list, title="By Destination Account"
    )
    by_budget: List[BudgetBreakdown] = Field(default_factory=list, title="By Budget")


class TransactionTrend(BaseModel):
    bucket: Bucket = Field(..., title="Bucket")
    series: List[TrendPoint] = Field(default_factory=list, title="Series")
