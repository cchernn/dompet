from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class Location(BaseModel):
    id: UUID = Field(
        ...,
        title="Location ID",
    )
    type: Literal["physical", "online"] = Field(
        ...,
        title="Location Type",
    )
    name: str = Field(
        ...,
        title="Location Name",
        max_length=255,
    )
    google_maps_url: Optional[str] = Field(
        None,
        title="Google Maps URL",
        description="Set for physical locations",
    )
    url: Optional[str] = Field(
        None,
        title="Site URL",
        description="Set for online locations",
    )
    is_active: bool = Field(
        True,
        title="Location Active Status",
    )
    created_at: datetime
    updated_at: datetime
