from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class Notification(BaseModel):
    id: UUID = Field(
        ...,
        title="Notification ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    type: Literal["success", "error", "warning", "info"] = Field(
        ...,
        title="Notification Type",
        description="Matches the frontend toast types",
    )
    message: str = Field(
        ...,
        title="Notification Message",
    )
    description: Optional[str] = Field(
        None,
        title="Notification Description",
        description="Optional secondary line, e.g. an error detail",
    )
    entity_type: Optional[str] = Field(
        None,
        title="Related Entity Type",
        description="Optional -- lets a notification deep-link to what it's about",
    )
    entity_id: Optional[UUID] = Field(
        None,
        title="Related Entity ID",
    )
    is_read: bool = Field(
        False,
        title="Read Status",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
    )
