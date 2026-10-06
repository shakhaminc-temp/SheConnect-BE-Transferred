import os
import re
import random
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException
from typing import Tuple


ALGORITHM = "HS256"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("FATAL: SECRET_KEY environment variable is not set.")

OTP_SECRET_KEY = os.getenv("OTP_SECRET_KEY")
if not OTP_SECRET_KEY:
    raise RuntimeError("FATAL: OTP_SECRET_KEY environment variable is not set.")

ACCESS_TOKEN_EXPIRE_MINUTES = 60
OTP_EXPIRE_MINUTES = 10
REFRESH_TOKEN_EXPIRE_DAYS = 7


def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character."
    return True, "Password is valid."


def generate_otp():
    return str(random.randint(100000, 999999))


def create_jwt_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "refresh",
        "scope": "refresh"
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_otp_token(email: str, otp: str, purpose: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    payload = {
        "sub": email,
        "otp": otp,
        "purpose": purpose,
        "exp": expire
    }

    return jwt.encode(payload, OTP_SECRET_KEY, algorithm=ALGORITHM)


def verify_otp_token(token: str):
    try:
        return jwt.decode(token, OTP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP token")
