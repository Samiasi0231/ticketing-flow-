from fastapi import APIRouter

from app.api.routes import admin, auth, events, orders

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(orders.router)
api_router.include_router(admin.router)
