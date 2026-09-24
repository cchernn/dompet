from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class Category(BaseModel):
    id: UUID = Field(
        ...,
        title="Category ID",
    )
    user_id: Optional[UUID] = Field(
        None,
        title="Owner User ID",
        description="NULL for global/system categories, Cognito UUID for user-owned categories",
    )
    name: str = Field(
        ...,
        title="Category Name",
        max_length=255,
    )
    parent_id: Optional[UUID] = Field(
        None,
        title="Parent Category ID",
    )
    is_active: bool = Field(
        True,
        title="Category Active Status",
    )
    created_at: datetime
    updated_at: datetime
