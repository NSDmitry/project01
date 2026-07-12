from types import SimpleNamespace

import pytest
from fastapi_limiter import FastAPILimiter

from app.core.errors.errors import TooManyRequests
from app.core.rate_limit import check_registrations_limit, client_ip, count_registration
from tests.sso_tests.test_login_brute_force import FakeRedis

IP = "1.2.3.4"


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(FastAPILimiter, "redis", redis)
    return redis


class TestClientIp:
    def test_prefers_forwarded_header(self):
        request = SimpleNamespace(
            headers={"X-Forwarded-For": "10.0.0.1, 172.18.0.2"},
            client=SimpleNamespace(host="172.18.0.5"),
        )
        assert client_ip(request) == "10.0.0.1"

    def test_falls_back_to_peer_ip(self):
        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="172.18.0.5"))
        assert client_ip(request) == "172.18.0.5"


class TestRegistrationsLimit:
    async def test_three_registrations_allowed(self, fake_redis):
        for _ in range(3):
            await check_registrations_limit(IP)
            await count_registration(IP)

    async def test_fourth_registration_blocked(self, fake_redis):
        for _ in range(3):
            await check_registrations_limit(IP)
            await count_registration(IP)

        with pytest.raises(TooManyRequests):
            await check_registrations_limit(IP)

    async def test_failed_attempts_do_not_consume_limit(self, fake_redis):
        # check без count (регистрация упала) - лимит не расходуется.
        for _ in range(10):
            await check_registrations_limit(IP)

    async def test_limit_is_per_ip(self, fake_redis):
        for _ in range(3):
            await count_registration(IP)

        with pytest.raises(TooManyRequests):
            await check_registrations_limit(IP)
        await check_registrations_limit("5.6.7.8")

    async def test_counter_expires_in_an_hour(self, fake_redis):
        await count_registration(IP)
        assert fake_redis.ttls[f"reg:{IP}"] == 3600

    async def test_noop_without_redis(self, monkeypatch):
        monkeypatch.setattr(FastAPILimiter, "redis", None)
        for _ in range(5):
            await check_registrations_limit(IP)
            await count_registration(IP)
