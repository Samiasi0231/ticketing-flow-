
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.config import settings
from app.core.deps import DB, Organizer
from app.models.enums import EventStatus, OrderStatus, UserRole
from app.models.event import Event, Seat, TicketType
from app.models.order import Order, Ticket
from app.schemas.common import ApiResponse
from app.schemas.event import (
    EventCreate,
    EventOut,
    EventUpdate,
    SalesReport,
    SalesRow,
    SeatBulkCreate,
    SeatOut,
    TicketTypeCreate,
    TicketTypeOut,
)

router = APIRouter(prefix="/events", tags=["Events"])


def _get_event(db, event_id: int) -> Event:
    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(404, "Event not found")

    return event


def _get_owned_event(db, event_id: int, user) -> Event:
    event = _get_event(db, event_id)

    if event.organizer_id != user.id and user.role != UserRole.admin:
        raise HTTPException(403, "You do not own this event")

    return event


# ---------- events ----------

@router.post(
    "",
    response_model=ApiResponse[EventOut],
    status_code=status.HTTP_201_CREATED,
)
def create_event(data: EventCreate, db: DB, user: Organizer):
    event = Event(
        **data.model_dump(),
        organizer_id=user.id,
        status=(
            EventStatus.pending
            if settings.events_require_approval
            else EventStatus.active
        ),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return ApiResponse(
        status_code=201,
        success=True,
        message="Event created successfully",
        data=event,
    )


@router.get(
    "",
    response_model=ApiResponse[list[EventOut]],
)
def browse_events(
    db: DB,
    skip: int = 0,
    limit: int = Query(20, le=100),
    q: str | None = None,
):
    """Public: upcoming, active events."""

    stmt = (
        select(Event)
        .where(
            Event.status == EventStatus.active,
            Event.starts_at > datetime.now(timezone.utc),
        )
        .order_by(Event.starts_at)
    )

    if q:
        stmt = stmt.where(Event.name.ilike(f"%{q}%"))

    events = db.scalars(stmt.offset(skip).limit(limit)).all()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Events retrieved successfully",
        data=events,
    )


@router.get(
    "/mine",
    response_model=ApiResponse[list[EventOut]],
)
def my_events(db: DB, user: Organizer):
    events = db.scalars(
        select(Event)
        .where(Event.organizer_id == user.id)
        .order_by(Event.starts_at)
    ).all()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Your events retrieved successfully",
        data=events,
    )


@router.get(
    "/{event_id}",
    response_model=ApiResponse[EventOut],
)
def get_event(event_id: int, db: DB):
    event = _get_event(db, event_id)

    return ApiResponse(
        status_code=200,
        success=True,
        message="Event retrieved successfully",
        data=event,
    )


@router.patch(
    "/{event_id}",
    response_model=ApiResponse[EventOut],
)
def update_event(
    event_id: int,
    data: EventUpdate,
    db: DB,
    user: Organizer,
):
    event = _get_owned_event(db, event_id, user)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)

    return ApiResponse(
        status_code=200,
        success=True,
        message="Event updated successfully",
        data=event,
    )


@router.delete(
    "/{event_id}",
    response_model=ApiResponse[None],
    status_code=status.HTTP_200_OK,
)
def delete_event(event_id: int, db: DB, user: Organizer):
    event = _get_owned_event(db, event_id, user)

    has_sales = db.scalar(
        select(func.count(TicketType.id)).where(
            TicketType.event_id == event_id,
            TicketType.sold > 0,
        )
    )

    if has_sales:
        raise HTTPException(
            409,
            "Event has sold tickets; cancel/refund them first",
        )

    db.delete(event)
    db.commit()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Event deleted successfully",
        data=None,
    )


# ---------- ticket types ----------

@router.post(
    "/{event_id}/ticket-types",
    response_model=ApiResponse[TicketTypeOut],
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_type(
    event_id: int,
    data: TicketTypeCreate,
    db: DB,
    user: Organizer,
):
    _get_owned_event(db, event_id, user)

    tt = TicketType(
        **data.model_dump(),
        event_id=event_id,
    )

    db.add(tt)
    db.commit()
    db.refresh(tt)

    return ApiResponse(
        status_code=201,
        success=True,
        message="Ticket type created successfully",
        data=tt,
    )


@router.get(
    "/{event_id}/ticket-types",
    response_model=ApiResponse[list[TicketTypeOut]],
)
def list_ticket_types(event_id: int, db: DB):
    _get_event(db, event_id)

    ticket_types = db.scalars(
        select(TicketType).where(TicketType.event_id == event_id)
    ).all()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Ticket types retrieved successfully",
        data=ticket_types,
    )


# ---------- seats ----------

@router.post(
    "/{event_id}/seats",
    response_model=ApiResponse[list[SeatOut]],
    status_code=status.HTTP_201_CREATED,
)
def create_seats(
    event_id: int,
    data: SeatBulkCreate,
    db: DB,
    user: Organizer,
):
    event = _get_owned_event(db, event_id, user)

    if not event.is_seated:
        raise HTTPException(400, "Event is not a seated event")

    tt = db.get(TicketType, data.ticket_type_id)

    if not tt or tt.event_id != event_id:
        raise HTTPException(404, "Ticket type not found for this event")

    existing = set(
        db.scalars(
            select(Seat.label).where(Seat.event_id == event_id)
        ).all()
    )

    new_labels = list(dict.fromkeys(data.labels))

    if existing & set(new_labels):
        raise HTTPException(409, "Some seat labels already exist")

    total = (
        db.scalar(
            select(func.count(Seat.id)).where(
                Seat.ticket_type_id == tt.id
            )
        )
        + len(new_labels)
    )

    if total > tt.quantity:
        raise HTTPException(
            400,
            f"Seats ({total}) would exceed ticket type quantity ({tt.quantity})",
        )

    seats = [
        Seat(
            event_id=event_id,
            ticket_type_id=tt.id,
            label=label,
        )
        for label in new_labels
    ]

    db.add_all(seats)
    db.commit()

    return ApiResponse(
        status_code=201,
        success=True,
        message="Seats created successfully",
        data=seats,
    )


@router.get(
    "/{event_id}/seats",
    response_model=ApiResponse[list[SeatOut]],
)
def seat_map(
    event_id: int,
    db: DB,
    available_only: bool = False,
):
    _get_event(db, event_id)

    stmt = (
        select(Seat)
        .where(Seat.event_id == event_id)
        .order_by(Seat.label)
    )

    if available_only:
        stmt = stmt.where(Seat.status == "available")

    seats = db.scalars(stmt).all()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Seat map retrieved successfully",
        data=seats,
    )


# ---------- sales ----------

@router.get(
    "/{event_id}/sales",
    response_model=ApiResponse[SalesReport],
)
def sales_report(
    event_id: int,
    db: DB,
    user: Organizer,
):
    _get_owned_event(db, event_id, user)

    rows = db.execute(
        select(
            TicketType.id,
            TicketType.name,
            TicketType.quantity,
            func.count(Order.id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Order.status == OrderStatus.paid,
                            Ticket.price,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .select_from(TicketType)
        .outerjoin(
            Ticket,
            Ticket.ticket_type_id == TicketType.id,
        )
        .outerjoin(
            Order,
            (Order.id == Ticket.order_id)
            & (Order.status == OrderStatus.paid),
        )
        .where(TicketType.event_id == event_id)
        .group_by(TicketType.id)
    ).all()

    by_type = [
        SalesRow(
            ticket_type_id=row[0],
            name=row[1],
            quantity=row[2],
            tickets_sold=row[3],
            revenue=row[4],
        )
        for row in rows
    ]

    report = SalesReport(
        event_id=event_id,
        total_tickets_sold=sum(
            row.tickets_sold for row in by_type
        ),
        total_revenue=sum(
            (row.revenue for row in by_type),
            Decimal(0),
        ),
        by_ticket_type=by_type,
    )

    return ApiResponse(
        status_code=200,
        success=True,
        message="Sales report retrieved successfully",
        data=report,
    )
