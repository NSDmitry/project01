from __future__ import annotations


def assert_status_code(response, expected_status_code: int) -> None:
    assert response.status_code == expected_status_code, response.json()


def assert_contains_keys(data: dict, expected_keys: set[str]) -> None:
    assert expected_keys.issubset(data.keys()), data
