from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
from uuid import UUID


class User(BaseModel):
    id: UUID = Field(
        ...,
        title="User ID",
        description="Cognito UUID -- internal identifier, never shown to other users",
    )
    username: str = Field(
        ...,
        title="Username",
        description="Public identifier other users address this account by",
        max_length=30,
    )
    display_name: str | None = Field(
        None,
        title="Display Name",
        max_length=100,
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        title="User Configuration",
        description="Opaque per-user settings blob (e.g. preferred currency, locale, theme)",
    )
    created_at: datetime
    updated_at: datetime
