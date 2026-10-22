from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from .security import decode_access_token

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .db import User, get_async_session
from uuid import UUID

oauth2_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:

    token = credentials.credentials

    try:
        payload = decode_access_token(token=token)
        user_id = payload["sub"]

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_id = UUID(user_id)

        except (ValueError, TypeError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user
