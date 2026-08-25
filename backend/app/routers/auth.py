"""Signup, login, refresh (with rotation), current-user lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, User, RefreshToken
from app.schemas import SignupIn, LoginIn, RefreshIn, TokenOut, UserOut
from app.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, hash_token, get_current_user, REFRESH_TOKEN_DAYS,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenOut:
    access = create_access_token(user.id)
    refresh, refresh_hash, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at))
    db.commit()
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    # first user in a brand-new org becomes that org's admin
    org = Organization(name=body.org_name)
    db.add(org)
    db.flush()

    user = User(
        org_id=org.id,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
    )
    db.add(user)
    db.flush()

    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is deactivated")

    user.last_login_at = datetime.now(timezone.utc)
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    token_hash = hash_token(body.refresh_token)
    stored = db.query(RefreshToken).filter_by(token_hash=token_hash).first()
    if not stored or stored.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked or unknown")
    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    # rotate: revoke the used refresh token, issue a new pair
    stored.revoked_at = datetime.now(timezone.utc)
    return _issue_tokens(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
