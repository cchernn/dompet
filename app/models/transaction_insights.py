from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from .insights import Bucket, TrendPoint


class CurrencyTotals(BaseModel):
    total_income: Decimal = Field(..., title="Total Income")
    total_expense: Decimal = Field(..., title="Total Expense")
    total_transfer: Decimal = Field(..., title="Total Transfer")
    net: Decimal = Field(..., title="Net", description="total_income - total_expense; transfers excluded")
    transaction_count: int = Field(..., title="Transaction Count", description="Includes transfers")


class BreakdownMetrics(BaseModel):
    """Metrics shared by every breakdown row. One row per (label, currency):
    amounts in different currencies are never added together. Transfers are
    not part of any breakdown."""

    currency: str = Field(..., title="Currency Code")
    total_income: Decimal = Field(..., title="Total Income")
    total_expense: Decimal = Field(..., title="Total Expense")
    net: Decimal = Field(..., title="Net")
    count: int = Field(..., title="Transaction Count")


class CategoryBreakdown(BreakdownMetrics):
    category: str = Field(..., title="Category Name", description="'Uncategorized' for transactions without one")


class AccountBreakdown(BreakdownMetrics):
    account: str = Field(
        ...,
        title="Account Name",
        description="A transaction counts toward both its source and its destination account, so rows overlap",
    )


class BudgetBreakdown(BreakdownMetrics):
    budget: str = Field(..., title="Budget Name")


class UserBreakdown(BreakdownMetrics):
    user_id: UUID = Field(..., title="Owner User ID")
    username: Optional[str] = Field(None, title="Username")
    display_name: Optional[str] = Field(None, title="Display Name")


class TransactionSummary(BaseModel):
    timezone: str = Field("UTC", title="Timezone", description="All dates and datetimes are UTC; convert on the client")
    default_currency: Optional[str] = Field(None, title="Caller's Default Currency")
    currencies: List[str] = Field(
        default_factory=list,
        title="Currencies",
        description="Currencies present in this result: the caller's default first, then by transaction count",
    )
    by_total: Dict[str, CurrencyTotals] = Field(default_factory=dict, title="Totals By Currency")
    by_category: List[CategoryBreakdown] = Field(default_factory=list, title="By Category")
    by_account: List[AccountBreakdown] = Field(default_factory=list, title="By Account")
    by_budget: List[BudgetBreakdown] = Field(default_factory=list, title="By Budget")
    by_user: List[UserBreakdown] = Field(default_factory=list, title="By User")


class TransactionTrendPoint(TrendPoint):
    currency: str = Field(..., title="Currency Code")


class TransactionTrend(BaseModel):
    timezone: str = Field("UTC", title="Timezone", description="Buckets are cut in UTC; convert labels on the client")
    default_currency: Optional[str] = Field(None, title="Caller's Default Currency")
    currencies: List[str] = Field(default_factory=list, title="Currencies")
    bucket: Bucket = Field(..., title="Bucket")
    series: List[TransactionTrendPoint] = Field(
        default_factory=list,
        title="Series",
        description="One point per (period, currency); count includes transfers, income/expense do not",
    )
