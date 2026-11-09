from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class BillBudgetLink(BaseModel):
    bill_id: UUID = Field(..., title="Bill ID")
    budget_id: UUID = Field(..., title="Budget ID")
    created_at: datetime
