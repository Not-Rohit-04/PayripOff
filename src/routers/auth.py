from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_async_session, User
from ..schemas import UserResponse, CreateUser, UserLogin
from ..security import hash_password, verify_password , create_access_token
from ..dependencies import get_current_user
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: CreateUser, session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already register.",
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(
    user_data: UserLogin, session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.email == user_data.email))

    user = result.scalar_one_or_none()

    if user is None or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    access_token = create_access_token(subject=str(user.id))
    
    return {"access_token": access_token , "token_type": "bearer"}

@router.get('/me')
async def read_current_user(
    current_user : str = Depends(get_current_user)
):
    return {
        "id" : str(current_user.id),
        "username" : current_user.username,
        "email" : current_user.email
    }