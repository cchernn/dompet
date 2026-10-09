from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class BudgetSearchResult(BaseModel):
    id: UUID = Field(..., title="Budget ID")
    name: str = Field(..., title="Budget Name")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions linked to this budget")
    owner_user_id: UUID = Field(..., title="Owner User ID")
    owner_username: Optional[str] = Field(
        None, title="Owner Username", description="NULL if the owner hasn't created a profile yet"
    )
    owner_display_name: Optional[str] = Field(None, title="Owner Display Name")
    members: List[Optional[str]] = Field(
        default_factory=list,
        title="Member Usernames",
        description="Ordered by when they joined; a NULL entry is a member who hasn't created a profile yet",
    )
    last_updated: Optional[datetime] = Field(
        None,
        title="Last Transaction At",
        description="Datetime of the most recently linked transaction, not the budget row's own updated_at; NULL if the budget has no transactions",
    )
