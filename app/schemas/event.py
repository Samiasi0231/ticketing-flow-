from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EventStatus, SeatStatus


class EventCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None
    venue: str = Field(min_length=2, max_length=200)
    starts_at: datetime
    is_seated: bool = False

    @field_validator("starts_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("starts_at must include a timezone")
        if v <= datetime.now(v.tzinfo):
            raise ValueError("starts_at must be in the future")
        return v


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    venue: str | None = None
    starts_at: datetime | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organizer_id: int
    name: str
    description: str | None
    venue: str
    starts_at: datetime
    is_seated: bool
    status: EventStatus


class EventStatusUpdate(BaseModel):
    status: EventStatus


class TicketTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    quantity: int = Field(gt=0)


class TicketTypeOut(TicketTypeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    sold: int


class SeatBulkCreate(BaseModel):
    ticket_type_id: int
    labels: list[str] = Field(min_length=1, max_length=1000)


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_type_id: int
    label: str
    status: SeatStatus


class SalesRow(BaseModel):
    ticket_type_id: int
    name: str
    quantity: int
    tickets_sold: int
    revenue: Decimal


class SalesReport(BaseModel):
    event_id: int
    total_tickets_sold: int
    total_revenue: Decimal
    by_ticket_type: list[SalesRow]
