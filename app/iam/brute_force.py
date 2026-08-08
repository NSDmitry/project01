"""Эскалирующая блокировка подбора пароля - по номеру телефона и по IP.

Политика PHONE (номер телефона): 5 неудачных попыток - блок на 1 минуту, ещё 5
попыток (в том числе во время блока) - на 30 минут, ещё 5 - на сутки. Успешный
вход сбрасывает счётчики.

Политика IP (адрес клиента, только login): 20 неудачных попыток - блок на 5
минут, ещё 20 - на сутки и дальше сутки. Успешный вход IP-счётчик не сбрасывает.

Хранение - Redis из FastAPILimiter; без Redis (тесты) - no-op, как в rate_limiter.
"""
from typing import NamedTuple

from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from app.core.errors.errors import TooManyRequests


class Policy(NamedTuple):
    prefix: str
    max_fails: int
    block_seconds: tuple[int, ...]
    ttl: int  # счётчик неудач живёт столько с последней попытки


PHONE = Policy("bf", 5, (60, 1800, 86400), 86400)
# ponytail: окно накопления IP-счётчика 1 час - компенсация пользователям за общим
# NAT. Точка тюнинга, если пойдут жалобы на ложные блокировки.
IP = Policy("bfip", 20, (300, 86400), 3600)


def _keys(subject: str, policy: Policy) -> tuple[str, str, str]:
    return (
        f"{policy.prefix}:fails:{subject}",
        f"{policy.prefix}:lock:{subject}",
        f"{policy.prefix}:level:{subject}",
    )


async def check_not_locked(subject: str, policy: Policy = PHONE) -> None:
    """Вызывать до проверки пароля. Попытки во время блока тоже идут в счёт эскалации."""
    redis = FastAPILimiter.redis
    if redis is None:
        return

    _, lock_key, _ = _keys(subject, policy)
    ttl = await redis.ttl(lock_key)
    if ttl > 0:
        await _register_failure(redis, subject, policy)
        ttl = max(await redis.ttl(lock_key), ttl)
        raise TooManyRequests(errors=[f"Попробуйте снова через {ttl} сек."])


async def register_failure(subject: str, policy: Policy = PHONE) -> None:
    redis = FastAPILimiter.redis
    if redis is None:
        return
    await _register_failure(redis, subject, policy)


async def reset(subject: str, policy: Policy = PHONE) -> None:
    redis = FastAPILimiter.redis
    if redis is None:
        return
    await redis.delete(*_keys(subject, policy))


async def _register_failure(redis: Redis, subject: str, policy: Policy) -> None:
    fails_key, lock_key, level_key = _keys(subject, policy)

    fails = await redis.incr(fails_key)
    await redis.expire(fails_key, policy.ttl)
    # Строго равенство, а не >=: параллельные неудачи получают от incr разные значения,
    # и порог обязан сработать ровно у одной из них. Иначе каждая лишняя поднимает
    # уровень, и три опечатки в параллельных запросах дают сутки вместо минуты.
    if fails != policy.max_fails:
        return

    level = min(await redis.incr(level_key), len(policy.block_seconds))
    # Уровень обязан пережить блок, который сам же и назначил, иначе следующая серия
    # начнёт эскалацию заново и понизит уже выданный блок (сутки -> 5 минут).
    await redis.expire(level_key, max(policy.ttl, policy.block_seconds[-1]))
    await redis.set(lock_key, 1, ex=policy.block_seconds[level - 1])
    await redis.delete(fails_key)
