from fastapi import APIRouter, HTTPException, Response

from .auth import create_access_token, create_refresh_token
from .models import User
from .schemas import LogoutResponse, Token, UserCreate, UserLogin, UserResponse
from .utils import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    exists = await User.filter(email=user.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await User.create(
        email=user.email, password=hash_password(user.password)
    )
    return new_user


@router.post("/login", response_model=Token)
async def login(user: UserLogin, response: Response):
    db_user = await User.filter(email=user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token({"sub": str(db_user.id)})
    refresh = create_refresh_token({"sub": str(db_user.id)})

    response.set_cookie("access_token", access, httponly=True)
    response.set_cookie("refresh_token", refresh, httponly=True)

    return Token(access_token=access, refresh_token=refresh)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return LogoutResponse()
