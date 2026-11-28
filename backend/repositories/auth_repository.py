"""Database access for user accounts and refresh sessions."""

from sqlmodel import Session, select

try:
    from backend.models.resources import AuthSession
    from backend.models.user import AppUser
except ModuleNotFoundError:
    from models.resources import AuthSession
    from models.user import AppUser


def find_user_by_email(session: Session, email: str) -> AppUser | None:
    return session.exec(select(AppUser).where(AppUser.email == email)).first()


def get_user(session: Session, user_id: int) -> AppUser | None:
    return session.get(AppUser, user_id)


def save_user(session: Session, user: AppUser) -> AppUser:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def add_member_profile(session: Session, user: AppUser) -> None:
    from backend.models.member import Member
    session.add(
        Member(
            full_name=user.full_name,
            email=user.email,
            phone="",
            is_active=True,
            created_by=user.id,
            user_id=user.id,
        )
    )
    session.commit()


def add_session(session: Session, auth_session: AuthSession) -> AuthSession:
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return auth_session


def find_session_by_refresh_hash(session: Session, refresh_hash: str) -> AuthSession | None:
    return session.exec(
        select(AuthSession).where(AuthSession.refresh_token_hash == refresh_hash)
    ).first()


def get_session(session: Session, session_id: str) -> AuthSession | None:
    return session.get(AuthSession, session_id)


def list_active_sessions(session: Session, user_id: int, current_time):
    statement = select(AuthSession).where(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > current_time,
    )
    return list(session.exec(statement).all())


def list_revocable_sessions(session: Session, user_id: int):
    statement = select(AuthSession).where(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
    )
    return list(session.exec(statement).all())


def save_session(session: Session, auth_session: AuthSession) -> AuthSession:
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)
    return auth_session
