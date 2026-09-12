from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class AccountLocationLink(BaseModel):
    account_id: UUID = Field(..., title="Account ID")
    location_id: UUID = Field(..., title="Location ID")
    created_at: datetime
