from pydantic import BaseModel, Field
from typing import List
from decimal import Decimal

from .insights import Bucket, TrendPoint, BudgetBreakdown


class BudgetSummary(BaseModel):
    budget_count: int = Field(..., title="Budget Count")
    total_transactions: int = Field(..., title="Total Transactions")
    total_income: Decimal = Field(..., title="Total Income")
    total_expense: Decimal = Field(..., title="Total Expense")
    net: Decimal = Field(..., title="Net")
    by_budget: List[BudgetBreakdown] = Field(default_factory=list, title="By Budget")


class BudgetTrend(BaseModel):
    bucket: Bucket = Field(..., title="Bucket")
    series: List[TrendPoint] = Field(default_factory=list, title="Series")
