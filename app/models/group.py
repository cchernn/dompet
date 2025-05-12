from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class Group(BaseModel):
    id: Optional[int] = Field(
        None,
        title="Group ID",
        description="The unique identifier for the transaction group. Auto-generated",
    )
    name: str = Field(
        ...,
        title="Group Name",
        description="The name of the transaction group",
        min_length=1,
        max_length=255,
    )
    is_active: Optional[bool] = Field(
        True,
        title="Group Active Status",
        description="Status to show if transaction group is active or inactive. Default: True",
        exclude=True,
    )
    user: Optional[UUID] = Field(
        None,
        title="Group User ID",
        description="The user ID for the transaction group in UUID format"
    )