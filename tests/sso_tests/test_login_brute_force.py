import pytest
from fastapi_limiter import FastAPILimiter

from app.core.errors.errors import TooManyRequests
from app.iam import brute_force

PHONE = "+79990000001"


class FakeRedis:
    """Минимум команд, которые использует brute_force. Без реального истечения TTL."""

    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def expire(self, key, seconds):
        self.ttls[key] = seconds

    async def ttl(self, key):
        return self.ttls.get(key, -2) if key in self.store else -2

    async def set(self, key, value, ex=None):
        self.store[key] = value
        self.ttls[key] = ex

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)
            self.ttls.pop(key, None)

    def expire_lock(self, phone):
        """Имитация истечения блокировки."""
        self.store.pop(f"bf:lock:{phone}", None)
        self.ttls.pop(f"bf:lock:{phone}", None)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(FastAPILimiter, "redis", redis)
    return redis


def lock_ttl(redis, phone=PHONE):
    return redis.ttls.get(f"bf:lock:{phone}")


async def fail_times(n, phone=PHONE):
    for _ in range(n):
        await brute_force.check_not_locked(phone)
        await brute_force.register_failure(phone)


async def locked_attempts(n, phone=PHONE):
    for _ in range(n):
        with pytest.raises(TooManyRequests):
            await brute_force.check_not_locked(phone)


class TestLoginBruteForce:
    async def test_four_failures_do_not_lock(self, fake_redis):
        await fail_times(4)
        await brute_force.check_not_locked(PHONE)

    async def test_five_failures_lock_for_one_minute(self, fake_redis):
        await fail_times(5)
        with pytest.raises(TooManyRequests):
            await brute_force.check_not_locked(PHONE)
        assert lock_ttl(fake_redis) == 60

    async def test_five_attempts_during_lock_escalate_to_30_minutes(self, fake_redis):
        await fail_times(5)
        await locked_attempts(5)
        assert lock_ttl(fake_redis) == 1800

    async def test_next_five_attempts_escalate_to_one_day(self, fake_redis):
        await fail_times(5)
        await locked_attempts(5)
        await locked_attempts(5)
        assert lock_ttl(fake_redis) == 86400

    async def test_escalation_survives_lock_expiry(self, fake_redis):
        # Блок истёк, но уровень эскалации остался - следующие 5 неудач дают 30 минут.
        await fail_times(5)
        fake_redis.expire_lock(PHONE)
        await fail_times(5)
        assert lock_ttl(fake_redis) == 1800

    async def test_success_resets_counters(self, fake_redis):
        await fail_times(5)
        fake_redis.expire_lock(PHONE)
        await brute_force.reset(PHONE)
        await fail_times(5)
        assert lock_ttl(fake_redis) == 60

    async def test_noop_without_redis(self, monkeypatch):
        monkeypatch.setattr(FastAPILimiter, "redis", None)
        await fail_times(10)
        await brute_force.check_not_locked(PHONE)
