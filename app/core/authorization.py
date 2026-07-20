from app.core.contracts import Principal
from app.core.errors.errors import Forbidden


def require_permission(user: Principal, *allowed_ids: int | None, message: str) -> None:
    """Разрешает, если user.id входит в allowed_ids, либо user - админ."""
    if not user.is_admin and user.id not in allowed_ids:
        raise Forbidden(message)
