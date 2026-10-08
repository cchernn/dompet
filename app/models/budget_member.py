from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class BudgetMember(BaseModel):
    budget_id: UUID = Field(..., title="Budget ID")
    user_id: UUID = Field(
        ...,
        title="Member User ID",
        description="Cognito UUID -- internal identifier, not shown in the UI",
    )
    username: str | None = Field(
        None,
        title="Member Username",
        description="Null if the member hasn't created a user profile yet",
    )
    display_name: str | None = Field(None, title="Member Display Name")
    created_at: datetime
