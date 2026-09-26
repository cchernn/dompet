from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class AccountSearchResult(BaseModel):
    id: UUID = Field(..., title="Account ID")
    code: str = Field(..., title="Account Code")
    name: str = Field(..., title="Account Name")
    description: Optional[str] = Field(None, title="Account Description")
    usage_count: int = Field(..., title="Usage Count", description="Number of transactions referencing this account as source or destination")
