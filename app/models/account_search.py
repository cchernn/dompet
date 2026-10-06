from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID


class AccountSearchResult(BaseModel):
    id: UUID = Field(..., title="Account ID")
    code: str = Field(..., title="Account Code")
    name: str = Field(..., title="Account Name")
    description: Optional[str] = Field(None, title="Account Description")
    transaction_count: int = Field(..., title="Transaction Count", description="Number of transactions referencing this account as source or destination")
    type: Literal["bank", "wallet", "merchant", "online", "utility", "subscription", "other"] = Field(
        ..., title="Account Type"
    )
    location_count: int = Field(..., title="Location Count", description="Number of locations linked to this account")
