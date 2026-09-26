from pydantic import BaseModel, Field
from uuid import UUID


class BudgetSearchResult(BaseModel):
    id: UUID = Field(..., title="Budget ID")
    name: str = Field(..., title="Budget Name")
    usage_count: int = Field(..., title="Usage Count", description="Number of transactions linked to this budget")
