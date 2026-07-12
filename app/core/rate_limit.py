from fastapi import Depends, Request, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.core.errors.errors import TooManyRequests

REGISTRATIONS_LIMIT = 3
REGISTRATIONS_WINDOW = 3600


def rate_limiter(times: int, seconds: int):
    """Rate-limit зависимость на Redis (ключ - IP + путь).

    Если лимитер не инициализирован (например в тестах, где lifespan не
    запускается) - запрос пропускается без ограничения.
    """
    limiter = RateLimiter(times=times, seconds=seconds)

    async def dependency(request: Request, response: Response) -> None:
        if FastAPILimiter.redis is None:
            return
        await limiter(request, response)

    return Depends(dependency)


def client_ip(request: Request) -> str:
    # Та же логика, что у default_identifier в fastapi_limiter: XFF от Caddy, иначе peer IP.
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


async def check_registrations_limit(ip: str) -> None:
    """429, если с этого IP за последний час уже создано REGISTRATIONS_LIMIT аккаунтов.

    Считаются только успешные регистрации (count_registration вызывается после
    создания аккаунта), поэтому неудачные попытки лимит не расходуют.
    Без Redis (тесты) - no-op.
    """
    redis = FastAPILimiter.redis
    if redis is None:
        return

    count = await redis.get(f"reg:{ip}")
    if count is not None and int(count) >= REGISTRATIONS_LIMIT:
        raise TooManyRequests(errors=["Слишком много регистраций с этого адреса. Попробуйте позже"])


async def count_registration(ip: str) -> None:
    redis = FastAPILimiter.redis
    if redis is None:
        return

    key = f"reg:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, REGISTRATIONS_WINDOW)
