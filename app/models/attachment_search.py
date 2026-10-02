from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AttachmentSearchResult(BaseModel):
    id: UUID = Field(..., title="Attachment ID")
    filename: str = Field(..., title="Attachment Filename")
    content_type: Optional[str] = Field(None, title="Attachment Content Type")
    size_bytes: Optional[int] = Field(None, title="File Size (bytes)")
    created_at: datetime = Field(..., title="Uploaded At")
