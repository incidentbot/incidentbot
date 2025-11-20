import bcrypt
import jwt

from datetime import datetime, timedelta, timezone
from incidentbot.configuration.settings import settings
from typing import Any

ALGORITHM = "HS256"
BCRYPT_ROUNDS = 12


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_password_hash(password: str) -> str:
    # returns a $2b$... string compatible with existing bcrypt hashes
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        # bad/unknown hash format
        return False
