from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import OrderStatus, TicketStatus


class OrderItemIn(BaseModel):
    ticket_type_id: int
    quantity: int = Field(default=1, ge=1, le=10)
    seat_ids: list[int] | None = None  # required for seated events

    @model_validator(mode="after")
    def sync_quantity(self):
        if self.seat_ids is not None:
            if not 1 <= len(self.seat_ids) <= 10:
                raise ValueError("Select between 1 and 10 seats")
            self.quantity = len(self.seat_ids)
        return self


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1, max_length=5)


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_type_id: int
    seat_id: int | None
    price: Decimal
    code: str
    status: TicketStatus


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: OrderStatus
    total: Decimal
    expires_at: datetime
    tickets: list[TicketOut]
