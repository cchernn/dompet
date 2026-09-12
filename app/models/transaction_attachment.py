from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class TransactionAttachmentLink(BaseModel):
    transaction_id: UUID = Field(..., title="Transaction ID")
    attachment_id: UUID = Field(..., title="Attachment ID")
    created_at: datetime
