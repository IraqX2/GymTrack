from fastapi import APIRouter, HTTPException, Request, Response

try:
    from backend.core.dependencies import CURRENT, DB
    from backend.schemas.resources import Signup, Login, ProfilePatch, PasswordPatch
    from backend.services import auth_service
except ModuleNotFoundError:
    from core.dependencies import CURRENT, DB
    from schemas.resources import Signup, Login, ProfilePatch, PasswordPatch
    from services import auth_service


router = APIRouter(tags=["authentication"])


@router.post("/api/auth/signup", status_code=201)
def signup(payload: Signup, request: Request, response: Response, db: DB):
    result = auth_service.signup(db, payload, request)
    auth_service.set_cookie(response, result.pop("refresh"))
    return result


@router.post("/api/auth/login")
def login(payload: Login, request: Request, response: Response, db: DB):
    result = auth_service.login(db, payload, request)
    auth_service.set_cookie(response, result.pop("refresh"))
    return result


@router.post("/api/auth/refresh")
def refresh(request: Request, response: Response, db: DB):
    try:
        result = auth_service.refresh_session(
            db,
            request.cookies.get(auth_service.COOKIE_NAME),
            request,
        )
    except HTTPException:
        auth_service.clear_cookie(response)
        raise
    auth_service.set_cookie(response, result.pop("refresh"))
    return result


@router.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    auth_service.logout(db, request.cookies.get(auth_service.COOKIE_NAME), request)
    auth_service.clear_cookie(response)
    return Response(status_code=204)


@router.get("/api/me")
def get_me(user: CURRENT, db: DB):
    return auth_service.get_profile(db, user)


@router.patch("/api/me")
def update_me(payload: ProfilePatch, user: CURRENT, db: DB, request: Request):
    updated = auth_service.update_profile(db, user, payload)
    from backend.core.audit import audit
    audit(db, request, "profile_updated", updated)
    return auth_service.public_user(updated)


@router.post("/api/me/password", status_code=204)
def change_password(
    payload: PasswordPatch,
    user: CURRENT,
    db: DB,
    request: Request,
    response: Response,
):
    auth_service.change_password(db, user, payload, request)
    auth_service.clear_cookie(response)
    return Response(status_code=204)


@router.get("/api/auth/sessions")
def list_sessions(user: CURRENT, db: DB, request: Request):
    return auth_service.list_sessions(
        db,
        user,
        request.cookies.get(auth_service.COOKIE_NAME),
    )


@router.delete("/api/auth/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    user: CURRENT,
    db: DB,
    request: Request,
    response: Response,
):
    is_current = auth_service.revoke_session(
        db,
        session_id,
        user,
        request.cookies.get(auth_service.COOKIE_NAME),
        request,
    )
    if is_current:
        auth_service.clear_cookie(response)
    return Response(status_code=204)
