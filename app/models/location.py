from pydantic import BaseModel, Field
from typing import Optional, Literal

class Location(BaseModel):
    id: Optional[int] = Field(
        None,
        title="Location ID",
        description="The unique identifier for the location. Auto-generated"
    )
    name: str = Field(
        ...,
        title="Location Name",
        description="The name of the location",
        min_length=1,
        max_length=255,
    )
    url: Optional[str] = Field(
        None,
        title="Location URL",
        description="URL of any type that references the location",
        max_length=255,
    )
    google_page_link: Optional[str] = Field(
        None,
        title="Location Google Page Link",
        description="Link to the location's Google Search Page",
        max_length=255,
    )
    google_maps_link: Optional[str] = Field(
        None,
        title="Location Google Maps Link",
        description="Link to the location's Google Maps Link",
        max_length=255,
    )
    category: Optional[str] = Field(
        None,
        title="Location Category",
        description="The category of the location",
        max_length=255,
    )
    access_type: Literal[
        "onsite",
        "online",
    ] = Field(
        "onsite",
        title="Location Access Type",
        description="The method of accessing the location: onsite or online. Default: onsite"
    )
    is_active: Optional[bool] = Field(
        True,
        title="Location Active Status",
        description="Status to show if location is active or inactive. Default: True",
        exclude=True,
    )
