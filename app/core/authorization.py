from app.core.errors.errors import Forbidden
from app.iam.models import User


def require_permission(user: User, *allowed_ids: int | None, message: str) -> None:
    """Разрешает, если user.id входит в allowed_ids, либо user - админ."""
    if not user.is_admin and user.id not in allowed_ids:
        raise Forbidden(message)
