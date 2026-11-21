"""Create an administrator account in the configured GymTrack database.

Run from the repository root after setting JWT_SECRET_KEY and PASSWORD_PEPPER:
    python -m backend.create_admin
"""

from getpass import getpass

from sqlmodel import Session, select

from backend.database import create_db_and_tables, engine
from backend.models.user import User
from backend.security import ensure_auth_configuration, hash_password


def main() -> None:
    ensure_auth_configuration()
    create_db_and_tables()

    full_name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass("Administrator password (8+ characters): ")
    if len(full_name) < 2 or len(password) < 8:
        raise SystemExit("Name must contain at least 2 characters and password at least 8.")

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            raise SystemExit("An account with that email already exists.")
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
        )
        session.add(user)
        session.commit()
        print(f"Administrator account created for {email} (user ID: {user.id}).")


if __name__ == "__main__":
    main()
