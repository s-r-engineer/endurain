from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PolarClient(BaseModel):
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)


class PolarWebhookPayload(BaseModel):
    event: str
    user_id: int | None = None
    entity_id: str | None = None
    timestamp: datetime | None = None
    url: str | None = None
    date: str | None = None

    model_config = ConfigDict(extra="allow")

