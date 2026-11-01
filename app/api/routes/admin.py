from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.deps import DB, Admin
from app.models.enums import EventStatus
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventOut, EventStatusUpdate
from app.schemas.user import UserOut, UserStatusUpdate

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/events", response_model=list[EventOut])
def all_events(db: DB, _: Admin, status: EventStatus | None = None, skip: int = 0, limit: int = Query(50, le=200)):
    stmt = select(Event).order_by(Event.id.desc())
    if status:
        stmt = stmt.where(Event.status == status)
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.patch("/events/{event_id}/status", response_model=EventOut)
def moderate_event(event_id: int, data: EventStatusUpdate, db: DB, _: Admin):
    """Approve (active), reject, or suspend an event."""
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    event.status = data.status
    db.commit()
    return event


@router.get("/users", response_model=list[UserOut])
def all_users(db: DB, _: Admin, skip: int = 0, limit: int = Query(50, le=200)):
    return db.scalars(select(User).order_by(User.id).offset(skip).limit(limit)).all()


@router.patch("/users/{user_id}/status", response_model=UserOut)
def suspend_user(user_id: int, data: UserStatusUpdate, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot suspend yourself")
    user.is_active = data.is_active
    db.commit()
    return user
