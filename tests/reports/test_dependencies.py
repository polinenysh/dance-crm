from datetime import date

import pytest
from fastapi import HTTPException

from app.modules.reports.dependencies import resolve_branch_id, validate_period
from app.shared.enums import UserRole


class FakeUser:
    """Минимальный пользователь для проверки прав отчётов."""

    def __init__(self, role: UserRole, branch_id: int | None) -> None:
        self.role = role
        self.branch_id = branch_id


def test_owner_can_request_all_branches() -> None:
    user = FakeUser(UserRole.OWNER, None)

    assert resolve_branch_id(user, None) is None


def test_owner_can_filter_by_branch() -> None:
    user = FakeUser(UserRole.OWNER, None)

    assert resolve_branch_id(user, 7) == 7


def test_branch_admin_is_limited_to_own_branch() -> None:
    user = FakeUser(UserRole.BRANCH_ADMIN, 3)

    assert resolve_branch_id(user, None) == 3
    assert resolve_branch_id(user, 3) == 3


def test_branch_admin_cannot_request_another_branch() -> None:
    user = FakeUser(UserRole.BRANCH_ADMIN, 3)

    with pytest.raises(HTTPException) as exc_info:
        resolve_branch_id(user, 4)

    assert exc_info.value.status_code == 403


def test_branch_admin_without_branch_is_forbidden() -> None:
    user = FakeUser(UserRole.BRANCH_ADMIN, None)

    with pytest.raises(HTTPException) as exc_info:
        resolve_branch_id(user, None)

    assert exc_info.value.status_code == 403


def test_validate_period_accepts_valid_range() -> None:
    validate_period(date(2026, 7, 1), date(2026, 7, 31))


def test_validate_period_rejects_reversed_range() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_period(date(2026, 7, 31), date(2026, 7, 1))

    assert exc_info.value.status_code == 422


def test_validate_period_rejects_more_than_366_days() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_period(date(2025, 1, 1), date(2026, 1, 3))

    assert exc_info.value.status_code == 422
