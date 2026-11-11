
from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DB
from app.core.security import create_access_token
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserLogin, LoginResponse, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
)
def register(data: UserCreate, db: DB):
    user = auth_service.register_user(db, data)

    return ApiResponse(
        status_code=201,
        success=True,
        message="User registered successfully",
        data=user,
    )


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
)
def login(data: UserLogin, db: DB):
    user = auth_service.authenticate(db, data.email, data.password)

    result = LoginResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        user=user,
    )

    return ApiResponse(
        status_code=200,
        success=True,
        message="Login successful",
        data=result,
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserOut],
)
def me(user: CurrentUser):
    return ApiResponse(
        status_code=200,
        success=True,
        message="Profile retrieved successfully",
        data=user,
    )
