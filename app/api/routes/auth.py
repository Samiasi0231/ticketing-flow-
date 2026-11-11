
from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DB
from app.core.security import create_access_token
from app.schemas.user import  UserCreate, UserLogin,LoginResponse, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(data: UserCreate, db: DB):
    return auth_service.register_user(db, data)


@router.post("/login", response_model=LoginResponse)
def login(data: UserLogin, db: DB):
    user = auth_service.authenticate(db, data.email, data.password)

    return LoginResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        user=user
    )
    


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
