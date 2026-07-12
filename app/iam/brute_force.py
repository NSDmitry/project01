"""Эскалирующая блокировка подбора пароля по номеру телефона.

5 неудачных попыток - блок на 1 минуту, ещё 5 попыток (в том числе во время
блока) - на 30 минут, ещё 5 - на сутки. Успешный вход сбрасывает счётчики.
Хранение - Redis из FastAPILimiter; без Redis (тесты) - no-op, как в rate_limiter.
"""
from fastapi_limiter import FastAPILimiter

from app.core.errors.errors import TooManyRequests

MAX_FAILS = 5
BLOCK_SECONDS = [60, 1800, 86400]
LEVEL_TTL = 86400  # уровень эскалации и счётчик неудач живут сутки с последней попытки


def _keys(phone_number: str) -> tuple[str, str, str]:
    return (
        f"bf:fails:{phone_number}",
        f"bf:lock:{phone_number}",
        f"bf:level:{phone_number}",
    )


async def check_not_locked(phone_number: str) -> None:
    """Вызывать до проверки пароля. Попытки во время блока тоже идут в счёт эскалации."""
    redis = FastAPILimiter.redis
    if redis is None:
        return

    _, lock_key, _ = _keys(phone_number)
    ttl = await redis.ttl(lock_key)
    if ttl > 0:
        await _register_failure(redis, phone_number)
        ttl = max(await redis.ttl(lock_key), ttl)
        raise TooManyRequests(errors=[f"Попробуйте снова через {ttl} сек."])


async def register_failure(phone_number: str) -> None:
    redis = FastAPILimiter.redis
    if redis is None:
        return
    await _register_failure(redis, phone_number)


async def reset(phone_number: str) -> None:
    redis = FastAPILimiter.redis
    if redis is None:
        return
    await redis.delete(*_keys(phone_number))


async def _register_failure(redis, phone_number: str) -> None:
    fails_key, lock_key, level_key = _keys(phone_number)

    fails = await redis.incr(fails_key)
    await redis.expire(fails_key, LEVEL_TTL)
    if fails < MAX_FAILS:
        return

    level = min(await redis.incr(level_key), len(BLOCK_SECONDS))
    await redis.expire(level_key, LEVEL_TTL)
    await redis.set(lock_key, 1, ex=BLOCK_SECONDS[level - 1])
    await redis.delete(fails_key)
