from pydantic import BaseModel, Field
from uuid import UUID


class TagSearchResult(BaseModel):
    id: UUID = Field(..., title="Tag ID")
    name: str = Field(..., title="Tag Name")
    usage_count: int = Field(..., title="Usage Count", description="Number of transactions linked to this tag")
