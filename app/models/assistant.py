from pydantic import BaseModel, Field


class AssistantReply(BaseModel):
    reply: str = Field(..., title="Assistant Reply")
