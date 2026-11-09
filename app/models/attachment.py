from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class Attachment(BaseModel):
    id: UUID = Field(
        ...,
        title="Attachment ID",
    )
    user_id: UUID = Field(
        ...,
        title="Owner User ID",
    )
    name: str = Field(
        ...,
        title="Attachment Name",
        max_length=255,
        description="User-given display name, separate from filename -- defaults to filename unless given explicitly",
    )
    filename: str = Field(
        ...,
        title="Attachment Filename",
        max_length=255,
        description="The file name used for the S3 storage key at upload time",
    )
    content_type: Optional[str] = Field(
        None,
        title="Attachment Content Type",
        max_length=255,
    )
    size_bytes: Optional[int] = Field(
        None,
        title="Attachment Size (bytes)",
    )
    download_url: Optional[str] = Field(
        None,
        title="Attachment Download URL",
        description="A short-lived presigned URL, generated fresh on every read",
    )
    is_active: bool = Field(
        True,
        title="Attachment Active Status",
    )
    created_at: datetime
    updated_at: datetime
