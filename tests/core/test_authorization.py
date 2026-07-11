import pytest

from app.core.authorization import require_permission
from app.core.errors.errors import Forbidden
from app.iam.models import User


def _user(id: int, is_admin: bool = False) -> User:
    return User(id=id, is_admin=is_admin)


def test_allows_matching_id():
    require_permission(_user(1), 1, message="denied")


def test_allows_any_matching_id_among_several():
    require_permission(_user(2), 1, 2, message="denied")


def test_denies_non_matching_id():
    with pytest.raises(Forbidden):
        require_permission(_user(1), 2, message="denied")


def test_admin_bypasses_non_matching_id():
    require_permission(_user(1, is_admin=True), 2, message="denied")
