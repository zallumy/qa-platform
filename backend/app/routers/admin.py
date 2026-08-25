"""Admin routes — user role management, org thresholds, audit log.
Every mutating action writes an audit_log row. Scoped to the admin's own org."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, QAThresholds, AuditLog
from app.schemas import RoleChangeIn, ThresholdsIn, ThresholdsOut, AuditLogOut, UserOut
from app.security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _write_audit_log(db: Session, actor_id, action: str, target_type: str, target_id, metadata: dict) -> None:
    db.add(AuditLog(
        actor_id=actor_id, action=action, target_type=target_type,
        target_id=target_id, metadata_json=metadata,
    ))


def _get_org_user(db: Session, admin: User, user_id: str) -> User:
    target = db.get(User, user_id)
    # admins manage users within their own org only
    if not target or target.org_id != admin.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target


@router.get("/users", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).filter_by(org_id=admin.org_id).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_user_role(
    user_id: str, body: RoleChangeIn,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    target = _get_org_user(db, admin, user_id)
    if target.id == admin.id and body.role != "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot demote your own account")
    previous_role = target.role
    target.role = body.role
    _write_audit_log(db, admin.id, "user.update_role", "user", target.id,
                      {"previous_role": previous_role, "new_role": body.role})
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = _get_org_user(db, admin, user_id)
    if target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate your own account")
    target.is_active = False
    _write_audit_log(db, admin.id, "user.deactivate", "user", target.id, {})
    db.commit()
    db.refresh(target)
    return target


@router.patch("/users/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = _get_org_user(db, admin, user_id)
    target.is_active = True
    _write_audit_log(db, admin.id, "user.reactivate", "user", target.id, {})
    db.commit()
    db.refresh(target)
    return target


@router.get("/thresholds", response_model=ThresholdsOut)
def get_thresholds(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(QAThresholds).filter_by(org_id=admin.org_id).first()
    if not row:
        row = QAThresholds(org_id=admin.org_id, updated_by=admin.id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.put("/thresholds", response_model=ThresholdsOut)
def update_thresholds(
    body: ThresholdsIn, admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    row = db.query(QAThresholds).filter_by(org_id=admin.org_id).first()
    previous = None
    if not row:
        row = QAThresholds(org_id=admin.org_id)
        db.add(row)
    else:
        previous = {
            "min_dpi": float(row.min_dpi), "min_bleed_mm": float(row.min_bleed_mm),
            "require_crop_marks": row.require_crop_marks,
        }
    row.min_dpi = body.min_dpi
    row.min_bleed_mm = body.min_bleed_mm
    row.require_crop_marks = body.require_crop_marks
    row.updated_by = admin.id
    _write_audit_log(db, admin.id, "org.update_thresholds", "organization", admin.org_id,
                      {"previous": previous, "new": body.model_dump()})
    db.commit()
    db.refresh(row)
    return row


@router.get("/audit-log", response_model=list[AuditLogOut])
def list_audit_log(
    limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    # audit log entries are global, but only actions by users in this admin's org are relevant to them
    org_user_ids = [u.id for u in db.query(User.id).filter_by(org_id=admin.org_id).all()]
    return (
        db.query(AuditLog)
        .filter(AuditLog.actor_id.in_(org_user_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
