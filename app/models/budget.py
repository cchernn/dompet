from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class Budget(BaseModel):
    id: UUID = Field(
        ...,
        title="Budget ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    name: str = Field(
        ...,
        title="Budget Name",
        max_length=255,
    )
    is_active: bool = Field(
        True,
        title="Budget Active Status",
    )
    created_at: datetime
    updated_at: datetime
