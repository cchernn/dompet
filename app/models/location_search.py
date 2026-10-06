from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID


class LocationSearchResult(BaseModel):
    id: UUID = Field(..., title="Location ID")
    name: str = Field(..., title="Location Name")
    type: Literal["physical", "online"] = Field(..., title="Location Type")
    account_count: int = Field(..., title="Account Count", description="Number of accounts linked to this location")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions at this location (as source or destination)")
    user_id: Optional[UUID] = Field(
        None, title="Owner User ID", description="NULL for public/shared locations"
    )
