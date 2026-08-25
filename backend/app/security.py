"""Auth helpers: JWT issuance/verification, password hashing, file validation."""
from __future__ import annotations
import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import magic
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ------------------------------------------------------------------
# Passwords
# ------------------------------------------------------------------


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_ctx.verify(password, password_hash)


# ------------------------------------------------------------------
# JWTs
# ------------------------------------------------------------------


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    """Returns (token, token_hash, expires_at). Caller persists the hash in refresh_tokens."""
    jti = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "jti": jti, "exp": expires_at}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash, expires_at


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


# ------------------------------------------------------------------
# File validation — MIME sniffing via magic bytes, not extension
# ------------------------------------------------------------------

MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

# Maps sniffed magic-byte MIME types to the canonical type we store/trust.
ALLOWED_MIME = {
    "application/pdf": "application/pdf",
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/tiff": "image/tiff",
}


def sniff_mime_type(contents: bytes) -> Optional[str]:
    detected = magic.from_buffer(contents, mime=True)
    return ALLOWED_MIME.get(detected)


def validate_upload(contents: bytes) -> str:
    """Validates size + real (magic-byte sniffed) MIME type. Returns the canonical MIME type
    or raises HTTPException. Must run before anything reaches the analysis queue."""
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 100MB limit")
    if len(contents) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    mime_type = sniff_mime_type(contents)
    if not mime_type:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported or unrecognized file type")
    return mime_type
