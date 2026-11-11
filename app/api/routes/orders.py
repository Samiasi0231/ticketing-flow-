
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.order import Order
from app.schemas.common import ApiResponse
from app.schemas.order import OrderCreate, OrderOut
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=ApiResponse[OrderOut],
    status_code=status.HTTP_201_CREATED,
)
def reserve(data: OrderCreate, db: DB, user: CurrentUser):
    """Step 1: reserve tickets/seats (held until expires_at)."""

    order = order_service.reserve_order(db, user, data)

    return ApiResponse(
        status_code=201,
        success=True,
        message="Order created successfully. Tickets reserved.",
        data=order,
    )


@router.post(
    "/{order_id}/pay",
    response_model=ApiResponse[OrderOut],
)
def pay(order_id: int, db: DB, user: CurrentUser):
    """Step 2 + 3: pay and confirm."""

    order = order_service.pay_order(db, order_id, user)

    return ApiResponse(
        status_code=200,
        success=True,
        message="Payment successful. Your tickets are confirmed.",
        data=order,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[OrderOut],
)
def cancel(order_id: int, db: DB, user: CurrentUser):
    order = order_service.cancel_order(db, order_id, user)

    return ApiResponse(
        status_code=200,
        success=True,
        message="Order cancelled successfully.",
        data=order,
    )


@router.get(
    "",
    response_model=ApiResponse[list[OrderOut]],
)
def my_orders(db: DB, user: CurrentUser):
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.id.desc())
    ).all()

    return ApiResponse(
        status_code=200,
        success=True,
        message="Orders retrieved successfully.",
        data=orders,
    )


@router.get(
    "/{order_id}",
    response_model=ApiResponse[OrderOut],
)
def get_order(order_id: int, db: DB, user: CurrentUser):
    order = db.get(Order, order_id)

    if not order or (
        order.user_id != user.id and user.role.value != "admin"
    ):
        raise HTTPException(404, "Order not found")

    return ApiResponse(
        status_code=200,
        success=True,
        message="Order retrieved successfully.",
        data=order,
    )
