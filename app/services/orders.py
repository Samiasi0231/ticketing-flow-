"""Reserve -> Pay -> Confirm flow.

Overselling is prevented by locking rows (SELECT ... FOR UPDATE) inside one
transaction, so two buyers can never grab the same seat or last ticket.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import EventStatus, OrderStatus, SeatStatus, TicketStatus
from app.models.event import Event, Seat, TicketType
from app.models.order import Order, Ticket
from app.models.user import User
from app.schemas.order import OrderCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def reserve_order(db: Session, user: User, data: OrderCreate) -> Order:
    order = Order(user_id=user.id, total=Decimal(0),
                  expires_at=_now() + timedelta(minutes=settings.reservation_minutes))
    db.add(order)
    total = Decimal(0)
    try:
        # lock ticket types in a stable order to avoid deadlocks
        for item in sorted(data.items, key=lambda i: i.ticket_type_id):
            tt = db.scalar(select(TicketType).where(TicketType.id == item.ticket_type_id).with_for_update())
            if not tt:
                raise HTTPException(404, f"Ticket type {item.ticket_type_id} not found")
            event = db.get(Event, tt.event_id)
            if event.status != EventStatus.active or event.starts_at <= _now():
                raise HTTPException(400, f"Event '{event.name}' is not open for sales")

            seats: list[Seat | None]
            if event.is_seated:
                if not item.seat_ids:
                    raise HTTPException(400, "This event is seated: choose seat_ids")
                ids = sorted(set(item.seat_ids))
                if len(ids) != len(item.seat_ids):
                    raise HTTPException(400, "Duplicate seats in request")
                found = db.scalars(select(Seat).where(Seat.id.in_(ids), Seat.ticket_type_id == tt.id)
                                   .order_by(Seat.id).with_for_update()).all()
                if len(found) != len(ids):
                    raise HTTPException(404, "One or more seats not found for this ticket type")
                if any(s.status != SeatStatus.available for s in found):
                    raise HTTPException(409, "One or more seats are no longer available")
                for s in found:
                    s.status = SeatStatus.reserved
                seats = list(found)
            else:
                if item.seat_ids:
                    raise HTTPException(400, "This event has no seat selection")
                seats = [None] * item.quantity

            if tt.sold + len(seats) > tt.quantity:
                raise HTTPException(409, f"Not enough '{tt.name}' tickets left")
            tt.sold += len(seats)

            for seat in seats:
                order.tickets.append(Ticket(ticket_type_id=tt.id, seat_id=seat.id if seat else None, price=tt.price))
                total += tt.price
        order.total = total
        db.commit()
    except Exception:
        db.rollback()
        raise
    return order


def _release(db: Session, order: Order, new_status: OrderStatus) -> None:
    """Give tickets/seats back to inventory."""
    for t in order.tickets:
        tt = db.scalar(select(TicketType).where(TicketType.id == t.ticket_type_id).with_for_update())
        tt.sold = max(0, tt.sold - 1)
        if t.seat_id:
            seat = db.get(Seat, t.seat_id)
            seat.status = SeatStatus.available
        t.status = TicketStatus.cancelled
    order.status = new_status


def _get_locked_order(db: Session, order_id: int, user: User) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order or (order.user_id != user.id and user.role.value != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


def pay_order(db: Session, order_id: int, user: User) -> Order:
    order = _get_locked_order(db, order_id, user)
    if order.status != OrderStatus.pending:
        raise HTTPException(409, f"Order is {order.status.value}")
    if order.expires_at <= _now():
        _release(db, order, OrderStatus.expired)
        db.commit()
        raise HTTPException(status.HTTP_410_GONE, "Reservation expired")

    # TODO (P2): call a real payment gateway here (Paystack/Stripe). Mocked as success.
    for t in order.tickets:
        t.status = TicketStatus.valid
        if t.seat_id:
            db.get(Seat, t.seat_id).status = SeatStatus.sold
    order.status = OrderStatus.paid
    db.commit()
    # TODO (P1): BackgroundTasks -> generate QR code + send confirmation email
    return order


def cancel_order(db: Session, order_id: int, user: User) -> Order:
    order = _get_locked_order(db, order_id, user)
    if order.status != OrderStatus.pending:
        raise HTTPException(409, "Only pending orders can be cancelled (paid orders need a refund)")
    _release(db, order, OrderStatus.cancelled)
    db.commit()
    return order


def release_expired_orders(db: Session) -> int:
    """Run periodically (background task / cron) to free abandoned reservations."""
    expired = db.scalars(select(Order).where(Order.status == OrderStatus.pending, Order.expires_at <= _now())
                         .with_for_update(skip_locked=True)).all()
    for o in expired:
        _release(db, o, OrderStatus.expired)
    db.commit()
    return len(expired)
