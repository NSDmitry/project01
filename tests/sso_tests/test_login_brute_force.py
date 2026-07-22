import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bcrypt
import pytest
from fastapi_limiter import FastAPILimiter

from app.core.errors.errors import TooManyRequests, Unauthorized
from app.iam import brute_force
from app.iam.schemas import SignInRequest
from app.iam.service import AuthService

PHONE = "+79990000001"
CLIENT_IP = "203.0.113.7"


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

    def expire_lock(self, subject):
        """Имитация истечения блокировки."""
        self.store.pop(f"bf:lock:{subject}", None)
        self.ttls.pop(f"bf:lock:{subject}", None)


class ConcurrentRedis(FakeRedis):
    """FakeRedis, дающий другим корутинам вклиниться между incr и установкой блока."""

    async def expire(self, key, seconds):
        await asyncio.sleep(0)
        await super().expire(key, seconds)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(FastAPILimiter, "redis", redis)
    return redis


def lock_ttl(redis, subject=PHONE, policy=brute_force.PHONE):
    return redis.ttls.get(f"{policy.prefix}:lock:{subject}")


async def fail_times(n, subject=PHONE, policy=brute_force.PHONE):
    for _ in range(n):
        await brute_force.check_not_locked(subject, policy)
        await brute_force.register_failure(subject, policy)


async def locked_attempts(n, subject=PHONE, policy=brute_force.PHONE):
    for _ in range(n):
        with pytest.raises(TooManyRequests):
            await brute_force.check_not_locked(subject, policy)


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


class TestIpBruteForce:
    async def test_nineteen_failures_do_not_lock(self, fake_redis):
        await fail_times(19, CLIENT_IP, brute_force.IP)
        await brute_force.check_not_locked(CLIENT_IP, brute_force.IP)

    async def test_twenty_failures_lock_for_five_minutes(self, fake_redis):
        await fail_times(20, CLIENT_IP, brute_force.IP)
        with pytest.raises(TooManyRequests):
            await brute_force.check_not_locked(CLIENT_IP, brute_force.IP)
        assert lock_ttl(fake_redis, CLIENT_IP, brute_force.IP) == 300

    async def test_twenty_attempts_during_lock_escalate_to_one_day(self, fake_redis):
        await fail_times(20, CLIENT_IP, brute_force.IP)
        await locked_attempts(20, CLIENT_IP, brute_force.IP)
        assert lock_ttl(fake_redis, CLIENT_IP, brute_force.IP) == 86400

    async def test_escalation_stays_at_one_day(self, fake_redis):
        await fail_times(20, CLIENT_IP, brute_force.IP)
        await locked_attempts(20, CLIENT_IP, brute_force.IP)
        await locked_attempts(20, CLIENT_IP, brute_force.IP)
        assert lock_ttl(fake_redis, CLIENT_IP, brute_force.IP) == 86400

    async def test_policies_are_isolated(self, fake_redis):
        await fail_times(20, CLIENT_IP, brute_force.IP)
        assert not [key for key in fake_redis.store if key.startswith("bf:")]

        await fail_times(5)
        assert not [key for key in fake_redis.store if key.startswith("bfip:fails")]
        assert lock_ttl(fake_redis) == 60
        assert lock_ttl(fake_redis, CLIENT_IP, brute_force.IP) == 300

    async def test_fails_counter_expires_in_an_hour(self, fake_redis):
        await fail_times(1, CLIENT_IP, brute_force.IP)
        assert fake_redis.ttls[f"bfip:fails:{CLIENT_IP}"] == 3600

    async def test_level_outlives_the_longest_block(self, fake_redis):
        # Уровень эскалации живёт дольше блока, который сам назначил. Иначе он протухнет
        # при живом суточном блоке, и следующая серия понизит сутки обратно до 5 минут.
        await fail_times(20, CLIENT_IP, brute_force.IP)
        assert fake_redis.ttls[f"bfip:level:{CLIENT_IP}"] >= 86400

    async def test_parallel_failures_do_not_skip_levels(self, monkeypatch):
        # Порог обязан сработать ровно у одной из параллельных неудач, иначе лишние
        # поднимают уровень и первый же блок выдаётся суточным вместо пятиминутного.
        redis = ConcurrentRedis()
        monkeypatch.setattr(FastAPILimiter, "redis", redis)
        redis.store[f"bfip:fails:{CLIENT_IP}"] = brute_force.IP.max_fails - 1

        await asyncio.gather(
            *[brute_force.register_failure(CLIENT_IP, brute_force.IP) for _ in range(3)]
        )

        assert lock_ttl(redis, CLIENT_IP, brute_force.IP) == 300


def _auth_service(db_user=None):
    """AuthService с замоканными репозиториями - проверяем только связку с brute_force."""
    user_repository = AsyncMock()
    user_repository.get_user_by_phone_number.return_value = db_user
    user_session_service = AsyncMock()
    user_session_service.create_user_session.return_value = "sid"

    return AuthService(
        user_service=AsyncMock(),
        user_repository=user_repository,
        user_session_service=user_session_service,
    )


class TestLoginIpLockout:
    async def test_spray_over_distinct_phones_locks_the_ip(self, fake_redis):
        service = _auth_service(db_user=None)

        for i in range(20):
            with pytest.raises(Unauthorized):
                await service.login(
                    SignInRequest(phone_number=f"+7999000{i:04d}", password="ValidPass1"),
                    client_ip=CLIENT_IP,
                )

        with pytest.raises(TooManyRequests):
            await service.login(
                SignInRequest(phone_number="+79990009999", password="ValidPass1"),
                client_ip=CLIENT_IP,
            )

    async def test_successful_login_does_not_reset_ip_counter(self, fake_redis):
        password = "ValidPass1"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        service = _auth_service()

        # Репозиторий отдаёт пользователя только для валидного номера.
        service.user_repository.get_user_by_phone_number.side_effect = (
            lambda phone_number: SimpleNamespace(id=1, password=hashed) if phone_number == PHONE else None
        )

        for i in range(19):
            with pytest.raises(Unauthorized):
                await service.login(
                    SignInRequest(phone_number=f"+7999111{i:04d}", password="WrongPass1"),
                    client_ip=CLIENT_IP,
                )

        await service.login(SignInRequest(phone_number=PHONE, password=password), client_ip=CLIENT_IP)

        with pytest.raises(Unauthorized):
            await service.login(
                SignInRequest(phone_number="+79990009998", password="WrongPass1"),
                client_ip=CLIENT_IP,
            )

        with pytest.raises(TooManyRequests):
            await service.login(
                SignInRequest(phone_number="+79990009997", password="WrongPass1"),
                client_ip=CLIENT_IP,
            )
