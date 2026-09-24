from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class BudgetMember(BaseModel):
    budget_id: UUID = Field(..., title="Budget ID")
    user_id: UUID = Field(..., title="Member User ID")
    created_at: datetime
