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
    assignment = SimpleNamespace(id=44, trainer_id=99)
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
    assignment = SimpleNamespace(id=44, trainer_id=12)
    payload = SimpleNamespace(status="completed", notes="Good progress")
    saved = SimpleNamespace(id=7, assignment_id=44, trainer_id=12, status="completed")
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
    assert "/api/trainer/assignments/{assignment_id}/progress" in paths


def test_password_is_hashed_and_can_be_verified():
    from backend.gymtrack_api import check_password, hash_password

    plain_password = "GymTrack-Demo-Password-2026"
    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert check_password(plain_password, password_hash)
    assert not check_password("incorrect-password", password_hash)
