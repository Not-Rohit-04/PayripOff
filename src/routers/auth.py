from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_async_session, User
from ..schemas import UserResponse, CreateUser
from ..security import hash_password
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
