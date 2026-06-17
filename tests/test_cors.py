from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from aphrodite.app import create_app


def test_cors_middleware_absent_when_origins_unset(monkeypatch):
    monkeypatch.delenv("APHRODITE_CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    response = client.get("/health", headers={"Origin": "https://app.example.com"})

    assert "access-control-allow-origin" not in response.headers


def test_explicit_cors_origins_allow_get_and_preflight(monkeypatch):
    monkeypatch.setenv(
        "APHRODITE_CORS_ORIGINS",
        "https://app.example.com,https://admin.example.com",
    )
    client = TestClient(create_app())

    get_response = client.get("/health", headers={"Origin": "https://app.example.com"})

    assert get_response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert get_response.headers["access-control-allow-credentials"] == "true"

    preflight_response = client.options(
        "/dispatch/skillopt:v1:status",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert preflight_response.status_code == 200
    assert preflight_response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert preflight_response.headers["access-control-allow-credentials"] == "true"


def test_cors_origins_are_trimmed_and_empty_entries_dropped(monkeypatch):
    monkeypatch.setenv(
        "APHRODITE_CORS_ORIGINS",
        " https://app.example.com, ,https://admin.example.com ",
    )
    client = TestClient(create_app())

    response = client.get("/health", headers={"Origin": "https://admin.example.com"})

    assert response.headers["access-control-allow-origin"] == "https://admin.example.com"


def test_wildcard_cors_origin_disables_credentials(monkeypatch):
    monkeypatch.setenv("APHRODITE_CORS_ORIGINS", "*")
    client = TestClient(create_app())

    response = client.get("/health", headers={"Origin": "https://app.example.com"})

    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_disallowed_cors_origin_does_not_echo_origin(monkeypatch):
    monkeypatch.setenv("APHRODITE_CORS_ORIGINS", "https://app.example.com")
    client = TestClient(create_app())

    response = client.get("/health", headers={"Origin": "https://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers
