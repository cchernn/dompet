from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class CategorySearchResult(BaseModel):
    id: UUID = Field(..., title="Category ID")
    name: str = Field(..., title="Category Name")
    parent_id: Optional[UUID] = Field(None, title="Parent Category ID")
    usage_count: int = Field(..., title="Usage Count", description="Number of transactions using this category")
