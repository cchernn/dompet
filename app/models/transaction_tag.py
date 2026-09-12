from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class TransactionTagLink(BaseModel):
    transaction_id: UUID = Field(..., title="Transaction ID")
    tag_id: UUID = Field(..., title="Tag ID")
    created_at: datetime
