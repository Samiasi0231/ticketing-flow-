from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderOut
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def reserve(data: OrderCreate, db: DB, user: CurrentUser):
    """Step 1: reserve tickets/seats (held until expires_at)."""
    return order_service.reserve_order(db, user, data)


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay(order_id: int, db: DB, user: CurrentUser):
    """Step 2 + 3: pay and confirm."""
    return order_service.pay_order(db, order_id, user)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, db: DB, user: CurrentUser):
    return order_service.cancel_order(db, order_id, user)


@router.get("", response_model=list[OrderOut])
def my_orders(db: DB, user: CurrentUser):
    return db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: DB, user: CurrentUser):
    order = db.get(Order, order_id)
    if not order or (order.user_id != user.id and user.role.value != "admin"):
        raise HTTPException(404, "Order not found")
    return order
