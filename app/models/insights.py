from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
from decimal import Decimal

Bucket = Literal["day", "week", "month"]


class TrendPoint(BaseModel):
    """One bucketed point in a /trend series -- same shape for
    transaction and budget trends per the insights spec's shared rules."""

    period_start: datetime = Field(..., title="Period Start")
    period_label: str = Field(
        ...,
        title="Period Label",
        description="Backend-formatted for display, e.g. '10 Mar', 'Week of Mar 3', 'Mar 2026'",
    )
    income: Decimal = Field(..., title="Income")
    expense: Decimal = Field(..., title="Expense")
    net: Decimal = Field(..., title="Net")
    count: int = Field(..., title="Transaction Count")


class BudgetBreakdown(BaseModel):
    """Shared by /transactions/summary's by_budget and /budgets/summary's
    by_budget -- same {budget, total, count} shape in both."""

    budget: str = Field(..., title="Budget Name")
    total: Decimal = Field(..., title="Total Amount")
    count: int = Field(..., title="Transaction Count")
