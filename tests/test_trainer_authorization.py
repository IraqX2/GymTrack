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
    progress_reader = pytest.MonkeyPatch()
    progress_reader.setattr(
        trainer_service.repository,
        "list_progress_for_assignment",
        lambda *args, **kwargs: pytest.fail("Progress must not be read for another trainer"),
    )

    with pytest.raises(HTTPException) as error:
        trainer_service.list_assignment_progress(object(), trainer, 44)

    assert error.value.status_code == 404
    progress_reader.undo()


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
