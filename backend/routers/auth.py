"""Domain API controllers. HTTP concerns live here; shared models/dependencies live in gymtrack_api."""
from fastapi import APIRouter

try:
    from backend.gymtrack_api import *
except ModuleNotFoundError:
    from gymtrack_api import *

router = APIRouter()


# Authentication
@router.post("/api/auth/signup", status_code=201)
def signup(data: Signup, request: Request, response: Response, db: DB):
    email = str(data.email).lower()
    if db.exec(select(AppUser).where(AppUser.email == email)).first():
        raise HTTPException(409, "An account with this email already exists")
    bootstrap_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").lower()
    user = AppUser(full_name=data.full_name.strip(), email=email, password_hash=hash_password(data.password),
                   role="admin" if bootstrap_email and bootstrap_email == email else "user")
    db.add(user); db.commit(); db.refresh(user)
    # Automatically link the signup to a personal gym member record.
    db.add(Member(full_name=user.full_name, email=user.email, phone="", is_active=True,
                  created_by=user.id, user_id=user.id))
    db.commit()
    refresh = secrets.token_urlsafe(48)
    db.add(AuthSession(id=str(uuid.uuid4()), user_id=user.id, refresh_token_hash=hash_refresh(refresh),
                       expires_at=now()+timedelta(days=REFRESH_DAYS), ip_address=client_ip(request),
                       user_agent=(request.headers.get("user-agent") or "")[:250]))
    db.commit(); set_cookie(response, refresh)
    audit(db, request, "signup", user, "user", user.id)
    return {"user": public_user(user, db), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@router.post("/api/auth/login")
def login(data: Login, request: Request, response: Response, db: DB):
    email = str(data.email).lower()
    user = db.exec(select(AppUser).where(AppUser.email == email)).first()
    if not user:
        audit(db, request, "login_failed", email=email, details="Unknown email")
        raise HTTPException(401, "Invalid email or password")
    if user.is_banned:
        audit(db, request, "login_blocked", user, details="Banned account")
        raise HTTPException(403, "Account is banned")
    if user.locked_until and user.locked_until > now():
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    if not check_password(data.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.failed_login_count = 0
            user.locked_until = now() + timedelta(minutes=15)
            audit(db, request, "login_locked", user, details="Five failed attempts")
        else:
            audit(db, request, "login_failed", user)
        db.add(user); db.commit()
        raise HTTPException(401, "Invalid email or password")
    user.failed_login_count, user.locked_until = 0, None
    user.updated_at = now(); db.add(user); db.commit()
    refresh = secrets.token_urlsafe(48)
    db.add(AuthSession(id=str(uuid.uuid4()), user_id=user.id, refresh_token_hash=hash_refresh(refresh),
                       expires_at=now()+timedelta(days=REFRESH_DAYS), ip_address=client_ip(request),
                       user_agent=(request.headers.get("user-agent") or "")[:250]))
    db.commit(); set_cookie(response, refresh); audit(db, request, "login", user)
    return {"user": public_user(user, db), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@router.post("/api/auth/refresh")
def refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(401, "Refresh cookie missing")
    token_row = db.exec(select(AuthSession).where(AuthSession.refresh_token_hash == hash_refresh(raw))).first()
    if not token_row or token_row.revoked_at or token_row.expires_at <= now():
        clear_cookie(response)
        raise HTTPException(401, "Refresh session expired or revoked")
    user = db.get(AppUser, token_row.user_id)
    if not user or user.is_banned:
        token_row.revoked_at = now(); db.add(token_row); db.commit(); clear_cookie(response)
        raise HTTPException(403, "Account is banned or unavailable")
    new_refresh = secrets.token_urlsafe(48)
    token_row.refresh_token_hash = hash_refresh(new_refresh)
    token_row.last_used_at = now(); token_row.ip_address = client_ip(request)
    db.add(token_row); db.commit(); set_cookie(response, new_refresh)
    return {"user": public_user(user, db), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@router.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        row = db.exec(select(AuthSession).where(AuthSession.refresh_token_hash == hash_refresh(raw))).first()
        if row and not row.revoked_at:
            row.revoked_at = now(); db.add(row); db.commit()
            user = db.get(AppUser, row.user_id); audit(db, request, "logout", user)
    clear_cookie(response)
    return Response(status_code=204)


@router.get("/api/me")
def me(user: CURRENT, db: DB):
    member = db.exec(select(Member).where(Member.user_id == user.id)).first()
    return {**public_user(user, db), "member_id": member.id if member else None, "phone": member.phone if member else ""}


@router.patch("/api/me")
def update_me(data: ProfilePatch, user: CURRENT, db: DB, request: Request):
    user.full_name = data.full_name.strip(); user.updated_at = now()
    db.add(user)
    member = db.exec(select(Member).where(Member.user_id == user.id)).first()
    if member:
        member.full_name = user.full_name; db.add(member)
    db.commit(); audit(db, request, "profile_updated", user)
    return public_user(user, db)


@router.post("/api/me/password", status_code=204)
def change_password(data: PasswordPatch, user: CURRENT, db: DB, request: Request, response: Response):
    if not check_password(data.current_password, user.password_hash):
        audit(db, request, "password_change_failed", user)
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password); user.updated_at = now(); db.add(user)
    for row in db.exec(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))).all():
        row.revoked_at = now(); db.add(row)
    db.commit(); clear_cookie(response); audit(db, request, "password_changed", user)
    return Response(status_code=204)


@router.get("/api/auth/sessions")
def sessions(user: CURRENT, db: DB, request: Request):
    active = db.exec(select(AuthSession).where(AuthSession.user_id == user.id,
                    AuthSession.revoked_at.is_(None), AuthSession.expires_at > now())).all()
    current_hash = hash_refresh(request.cookies[COOKIE_NAME]) if request.cookies.get(COOKIE_NAME) else None
    return [{"id": row.id, "created_at": row.created_at, "last_used_at": row.last_used_at,
             "expires_at": row.expires_at, "ip_address": row.ip_address, "user_agent": row.user_agent,
             "current": row.refresh_token_hash == current_hash} for row in active]


@router.delete("/api/auth/sessions/{session_id}", status_code=204)
def revoke_session(session_id: str, user: CURRENT, db: DB, request: Request, response: Response):
    row = db.get(AuthSession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Session not found")
    was_current = request.cookies.get(COOKIE_NAME) and row.refresh_token_hash == hash_refresh(request.cookies[COOKIE_NAME])
    row.revoked_at = now(); db.add(row); db.commit()
    if was_current: clear_cookie(response)
    audit(db, request, "session_revoked", user, "session", session_id)
    return Response(status_code=204)


@router.get("/api/member/dashboard")
def member_dashboard(user: CURRENT, db: DB):
    # A regular login represents one member profile. Members only receive
    # their own records; administrators use the management modules instead.
    if user.role != "user":
        raise HTTPException(403, "Member dashboard is only available to member accounts")
    member = get_my_member(db, user)
    my_memberships = db.exec(
        select(Membership).where(Membership.member_id == member.id)
        .order_by(Membership.created_at.desc())
    ).all()
    my_attendance = db.exec(
        select(Attendance).where(Attendance.member_id == member.id)
        .order_by(Attendance.check_in.desc()).limit(100)
    ).all()
    assignment_rows = db.exec(
        select(WorkoutAssignment, WorkoutPlan, Trainer)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
        .outerjoin(Trainer, Trainer.id == WorkoutAssignment.trainer_id)
        .where(WorkoutAssignment.member_id == member.id)
        .order_by(WorkoutAssignment.created_at.desc())
    ).all()
    workouts = [
        {
            "assignment": assignment,
            "plan": plan,
            "trainer": trainer,
            "progress": db.exec(
                select(WorkoutProgress)
                .where(WorkoutProgress.assignment_id == assignment.id)
                .order_by(WorkoutProgress.progress_date.desc(), WorkoutProgress.created_at.desc())
            ).all(),
        }
        for assignment, plan, trainer in assignment_rows
    ]
    return {
        "member": member,
        "memberships": my_memberships,
        "attendance": my_attendance,
        "workouts": workouts,
    }
