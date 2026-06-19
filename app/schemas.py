from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class PlaceShort(BaseModel):
    id: UUID
    name: str
    city: str
    address: str

    model_config = {"from_attributes": True}


class PlaceDetailed(PlaceShort):
    seats_pattern: str

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    id: UUID
    name: str
    place: PlaceShort
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = {"from_attributes": True}


class EventDetail(BaseModel):
    id: UUID
    name: str
    place: PlaceDetailed
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: list[str]


class CreateTicketRequest(BaseModel):
    event_id: UUID
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    seat: str = Field(min_length=1)

    @field_validator("first_name", "last_name", "seat")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class CreateTicketResponse(BaseModel):
    ticket_id: UUID


class CancelTicketResponse(BaseModel):
    success: bool


class SyncTriggerResponse(BaseModel):
    sync_status: str


class HealthResponse(BaseModel):
    status: str = "ok"
