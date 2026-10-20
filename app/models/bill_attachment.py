from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class BillAttachmentLink(BaseModel):
    bill_id: UUID = Field(..., title="Bill ID")
    attachment_id: UUID = Field(..., title="Attachment ID")
    created_at: datetime
