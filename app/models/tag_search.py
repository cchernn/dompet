from pydantic import BaseModel, Field
from uuid import UUID


class TagSearchResult(BaseModel):
    id: UUID = Field(..., title="Tag ID")
    name: str = Field(..., title="Tag Name")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions linked to this tag")
