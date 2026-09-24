from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class TransactionBudgetLink(BaseModel):
    transaction_id: UUID = Field(..., title="Transaction ID")
    budget_id: UUID = Field(..., title="Budget ID")
    created_at: datetime
