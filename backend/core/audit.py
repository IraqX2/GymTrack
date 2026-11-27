from fastapi import Request
from sqlmodel import Session

try:
    from backend.models.activity import ActivityLog
    from backend.models.user import AppUser
except ModuleNotFoundError:
    from models.activity import ActivityLog
    from models.user import AppUser


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    value = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "")
    )
    return value[:45] or None


def audit(
    db: Session,
    request: Request,
    action: str,
    user: AppUser | None = None,
    entity_type: str | None = None,
    entity_id: object | None = None,
    details: str | None = None,
    email: str | None = None,
) -> None:
    try:
        db.add(
            ActivityLog(
                user_id=user.id if user else None,
                email=user.email if user else email,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                details=(details or "")[:500] or None,
                ip_address=client_ip(request),
                user_agent=(request.headers.get("user-agent") or "")[:250] or None,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
