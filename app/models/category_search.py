from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class CategorySearchResult(BaseModel):
    id: UUID = Field(..., title="Category ID")
    name: str = Field(..., title="Category Name")
    parent_id: Optional[UUID] = Field(None, title="Parent Category ID")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions using this category")
    user_id: Optional[UUID] = Field(
        None, title="Owner User ID", description="NULL for global/system categories"
    )
    username: Optional[str] = Field(
        None, title="Owner Username", description="NULL for global categories, or if the owner hasn't created a profile yet"
    )
    display_name: Optional[str] = Field(None, title="Owner Display Name")
