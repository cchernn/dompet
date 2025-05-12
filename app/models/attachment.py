from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class Attachment(BaseModel):
    id: Optional[int] = Field(
        None, 
        title="Attachment ID", 
        description="The unique identifier for the attachment. Auto-generated",
    )
    date: datetime = Field(
        ..., 
        title="Attachment Date", 
        description="The date when the attachment occured in format YYYY-MM-DD",
    )
    name: str = Field(
        ..., 
        title="Attachment Name", 
        description="The name of the attachment", 
        min_length=1, 
        max_length=255,
    )
    filename: Optional[str] = Field(
        None,
        title="Attachment Filename",
        description="The name of the file for the attachment",
        max_length=255,
    )
    url: Optional[str] = Field(
        None,
        title="Attachment URL",
        description="Link that references the attachment file",
        max_length=255,
    )
    type: Optional[str] = Field(
        None,
        title="Attachment Type",
        description="The type of the attachment file",
        max_length=255,
    )
    is_active: Optional[bool] = Field(
        True,
        title="Attachment Active Status",
        description="Status to show if attachment is active or inactive. Default: True",
        exclude=True,
    )
    user: Optional[UUID] = Field(
        None,
        title="Attachment User ID",
        description="The user ID for the attachment in UUID format"
    )