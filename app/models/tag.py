from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class Tag(BaseModel):
    id: UUID = Field(
        ...,
        title="Tag ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    name: str = Field(
        ...,
        title="Tag Name",
        max_length=255,
    )
    is_active: bool = Field(
        True,
        title="Tag Active Status",
    )
    created_at: datetime
    updated_at: datetime
