from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime as DateTime
from decimal import Decimal
from uuid import UUID


class TransactionSuggestion(BaseModel):
    name: str = Field(..., title="Name")
    type: Literal["expenditure", "income", "transfer"] = Field(..., title="Type")
    currency: str = Field(..., title="Currency Code")
    category_id: Optional[UUID] = Field(None, title="Category ID")
    category: Optional[str] = Field(None, title="Category Name")
    source_account_id: UUID = Field(..., title="Source Account ID")
    source_account: str = Field(..., title="Source Account Name")
    destination_account_id: UUID = Field(..., title="Destination Account ID")
    destination_account: str = Field(..., title="Destination Account Name")
    source_location_id: Optional[UUID] = Field(None, title="Source Location ID")
    destination_location_id: Optional[UUID] = Field(None, title="Destination Location ID")
    typical_amount: Decimal = Field(
        ...,
        title="Typical Amount",
        description="The most common amount across the pattern's past uses",
    )
    last_amount: Decimal = Field(..., title="Last Amount", description="The amount of the most recent use")
    times_used: int = Field(..., title="Times Used")
    used_last_90d: int = Field(..., title="Used In The Last 90 Days")
    last_used: DateTime = Field(..., title="Last Used")
    time_matches: int = Field(
        0,
        title="Time Matches",
        description="Past uses around this time of day on the same kind of day; 0 when no tz_offset was given",
    )
    score: float = Field(..., title="Score", description="Recency-weighted frequency")
    ranked_score: float = Field(..., title="Ranked Score", description="score with the time-of-day boost applied")
    origin_transaction_id: UUID = Field(
        ...,
        title="Origin Transaction ID",
        description="The most recent transaction in the pattern; open the add page with ?from=<id> to prefill from it",
    )
