from pwdlib import PasswordHash
import os
import jwt
from datetime import datetime, timedelta, timezone

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hash_password: str) -> bool:
    return password_hash.verify(password, hash_password)


def create_access_token(subject: str) -> str:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY not configured")

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY not configured")

    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
