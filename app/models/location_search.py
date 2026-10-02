from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID


class LocationSearchResult(BaseModel):
    id: UUID = Field(..., title="Location ID")
    name: str = Field(..., title="Location Name")
    type: Literal["physical", "online"] = Field(..., title="Location Type")
    usage_count: int = Field(..., title="Usage Count", description="Number of accounts linked to this location")
    user_id: Optional[UUID] = Field(
        None, title="Owner User ID", description="NULL for public/shared locations"
    )
