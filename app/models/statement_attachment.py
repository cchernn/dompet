from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class StatementAttachmentLink(BaseModel):
    statement_id: UUID = Field(..., title="Statement ID")
    attachment_id: UUID = Field(..., title="Attachment ID")
    created_at: datetime
