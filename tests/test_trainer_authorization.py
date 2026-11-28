from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.core.dependencies import admin_user, trainer_user
from backend.services import trainer_service


def test_member_cannot_use_admin_dependency():
    member = SimpleNamespace(role="user")

    with pytest.raises(HTTPException) as error:
        admin_user(member)

    assert error.value.status_code == 403


def test_admin_cannot_use_trainer_dependency():
    administrator = SimpleNamespace(role="admin")

    with pytest.raises(HTTPException) as error:
        trainer_user(administrator)

    assert error.value.status_code == 403


def test_trainer_dependency_accepts_trainer_account():
    trainer = SimpleNamespace(role="trainer")

    assert trainer_user(trainer) is trainer


def test_trainer_cannot_read_another_trainers_assignment(monkeypatch):
    trainer = SimpleNamespace(id=12, role="trainer", email="trainer@example.test")
    assignment = SimpleNamespace(id=44, trainer_id=99, member_id=31)
    monkeypatch.setattr(
        trainer_service,
        "_require_trainer_profile",
        lambda session, account: trainer,
    )
    monkeypatch.setattr(
        trainer_service.repository,
        "find_assignment",
        lambda session, assignment_id: assignment,
    )
    monkeypatch.setattr(
        trainer_service.repository,
        "list_progress_for_assignment",
        lambda *args, **kwargs: pytest.fail("Progress must not be read for another trainer"),
    )

    with pytest.raises(HTTPException) as error:
        trainer_service.list_assignment_progress(object(), trainer, 44)

    assert error.value.status_code == 404


def test_trainer_can_record_progress_for_owned_assignment(monkeypatch):
    trainer = SimpleNamespace(id=12, role="trainer", email="trainer@example.test")
    assignment = SimpleNamespace(id=44, trainer_id=12, member_id=31)
    payload = SimpleNamespace(completion_percent=75, notes="Good progress")
    saved = SimpleNamespace(
        id=7, assignment_id=44, member_id=31, trainer_id=12,
        completion_percent=75, notes="Good progress",
    )
    monkeypatch.setattr(
        trainer_service,
        "_require_trainer_profile",
        lambda session, account: trainer,
    )
    monkeypatch.setattr(
        trainer_service.repository,
        "find_assignment",
        lambda session, assignment_id: assignment,
    )
    monkeypatch.setattr(
        trainer_service.repository,
        "add_progress",
        lambda session, progress: saved,
    )

    result = trainer_service.record_assignment_progress(object(), trainer, 44, payload)

    assert result is saved
    assert result.trainer_id == trainer.id
    assert result.assignment_id == assignment.id
    assert result.member_id == assignment.member_id
    assert result.completion_percent == 75


def test_trainer_progress_route_audits_completion_percent(monkeypatch):
    from backend.routers import trainers as trainer_router

    trainer = SimpleNamespace(id=12, role="trainer")
    progress = SimpleNamespace(completion_percent=80)
    audit_events = []

    monkeypatch.setattr(
        trainer_service,
        "record_assignment_progress",
        lambda session, account, assignment_id, payload: progress,
    )
    monkeypatch.setattr(
        trainer_router,
        "audit",
        lambda *args, **kwargs: audit_events.append((args, kwargs)),
    )

    result = trainer_router.add_assignment_progress(
        assignment_id=44,
        payload=SimpleNamespace(completion_percent=80, notes=""),
        user=trainer,
        db=object(),
        request=object(),
    )

    assert result is progress
    assert audit_events
    assert audit_events[0][0][6] == "completion_percent=80"


def test_member_cannot_read_another_members_profile(monkeypatch):
    from backend.services import member_service

    other_member = SimpleNamespace(id=44, user_id=99)
    monkeypatch.setattr(
        member_service.repository,
        "find_member_by_id",
        lambda session, member_id: other_member,
    )
    account = SimpleNamespace(id=12, role="user")

    with pytest.raises(HTTPException) as error:
        member_service.get_member_record(object(), 44, account)

    assert error.value.status_code == 404


def test_group_member_without_create_permission_is_denied():
    from backend.services.group_service import _allow

    membership = SimpleNamespace(role="member", can_create=False, can_edit=True, can_assign=False)

    with pytest.raises(HTTPException) as error:
        _allow(membership, "create")

    assert error.value.status_code == 403


def test_group_owner_can_create_without_member_flags():
    from backend.services.group_service import _allow

    owner = SimpleNamespace(role="owner", can_create=False, can_edit=False, can_assign=False)

    assert _allow(owner, "create") is None


def test_access_token_verification_rejects_tampered_token():
    from backend.core.dependencies import current_user

    credentials = SimpleNamespace(credentials="this.is.not.a.valid.jwt")

    with pytest.raises(HTTPException) as error:
        current_user(credentials, object())

    assert error.value.status_code == 401


def test_application_registers_trainer_routes():
    from backend.gymtrack_api import app

    paths = set(app.openapi()["paths"])
    assert "/api/trainer/dashboard" in paths
    assert "/api/members" in paths
    assert "/api/members/{member_id}" in paths
    assert "/api/groups" in paths
    assert "/api/groups/{group_id}/work" in paths
    assert "/api/memberships" in paths
    assert "/api/memberships/{membership_id}" in paths
    assert "/api/attendance" in paths
    assert "/api/attendance/requests" in paths
    assert "/api/attendance/requests/{request_id}" in paths
    assert "/api/workout-plans" in paths
    assert "/api/workout-assignments" in paths
    assert "/api/auth/signup" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/refresh" in paths
    assert "/api/me" in paths
    assert "/api/auth/sessions" in paths
    assert "/api/admin/stats" in paths
    assert "/api/admin/users" in paths
    assert "/api/admin/content" in paths
    assert "/api/admin/export/users" in paths
    assert "/api/trainer/assignments/{assignment_id}/progress" in paths
    assert "/api/admin/users/{target_id}" in paths
    assert "/api/admin/users/bulk-ban" in paths
    assert "/api/admin/users/bulk-unban" in paths
    assert "/api/admin/content" in paths
    assert "/api/admin/content/{content_type}/{record_id}" in paths
    assert "/api/admin/content/{content_type}/bulk-delete" in paths
    assert "/api/admin/export/attendance" in paths
    assert "/api/admin/export/assignments" in paths


def test_password_is_hashed_and_can_be_verified():
    from backend.gymtrack_api import check_password, hash_password

    plain_password = "GymTrack-Demo-Password-2026"
    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert check_password(plain_password, password_hash)
    assert not check_password("incorrect-password", password_hash)


def test_trainer_progress_schema_enforces_percentage_range():
    from pydantic import ValidationError
    from backend.schemas.trainer import TrainerProgressCreate

    assert TrainerProgressCreate(completion_percent=100).completion_percent == 100
    with pytest.raises(ValidationError):
        TrainerProgressCreate(completion_percent=101)
