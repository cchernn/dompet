from pydantic import BaseModel, Field
from uuid import UUID


class BudgetSearchResult(BaseModel):
    id: UUID = Field(..., title="Budget ID")
    name: str = Field(..., title="Budget Name")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions linked to this budget")
