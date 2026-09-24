from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class Account(BaseModel):
    id: UUID = Field(
        ...,
        title="Account ID",
        description="Immutable internal identifier for the account",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
        description="Cognito UUID of the account owner",
    )
    code: str = Field(
        ...,
        title="Account Code",
        description="User-editable identifier for the account",
        max_length=100,
    )
    name: str = Field(
        ...,
        title="Account Name",
        max_length=255,
    )
    description: Optional[str] = Field(
        None,
        title="Account Description",
    )
    is_active: bool = Field(
        True,
        title="Account Active Status",
    )
    created_at: datetime
    updated_at: datetime
