from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import APIRouter
from fastapi.testclient import TestClient

from aphrodite.app import create_app
from aphrodite.modules import AdapterSpec


def _ping_router() -> APIRouter:
    router = APIRouter()

    @router.get("/ping")
    def ping():
        return {"ok": True}

    return router


def test_discovered_adapter_router_requires_bearer_token(monkeypatch):
    spec = AdapterSpec(system="demo", handle=lambda *a: {}, router=_ping_router())
    monkeypatch.setattr("aphrodite.app.discover_adapter_specs", lambda: ({"demo": spec}, {}))
    monkeypatch.setenv("APHRODITE_ADAPTER_AUTH_TOKEN", "t")

    response = TestClient(create_app()).get("/demo/ping")

    assert response.status_code == 401


def test_discovered_adapter_router_accepts_valid_bearer_token(monkeypatch):
    spec = AdapterSpec(system="demo", handle=lambda *a: {}, router=_ping_router())
    monkeypatch.setattr("aphrodite.app.discover_adapter_specs", lambda: ({"demo": spec}, {}))
    monkeypatch.setenv("APHRODITE_ADAPTER_AUTH_TOKEN", "t")

    response = TestClient(create_app()).get("/demo/ping", headers={"Authorization": "Bearer t"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_discovered_public_adapter_router_skips_host_auth(monkeypatch):
    spec = AdapterSpec(
        system="demo",
        handle=lambda *a: {},
        router=_ping_router(),
        requires_auth=False,
    )
    monkeypatch.setattr("aphrodite.app.discover_adapter_specs", lambda: ({"demo": spec}, {}))

    response = TestClient(create_app()).get("/demo/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_invalid_adapter_router_is_quarantined_at_mount_time(monkeypatch):
    spec = AdapterSpec(system="demo", handle=lambda *a: {}, router=object())
    monkeypatch.setattr("aphrodite.app.discover_adapter_specs", lambda: ({"demo": spec}, {}))

    app = create_app()

    assert "demo" in app.state.adapter_quarantine
    assert app.state.adapter_quarantine["demo"]["phase"] == "mount"


def test_adapter_without_router_is_not_mounted(monkeypatch):
    spec = AdapterSpec(system="demo", handle=lambda *a: {}, router=None)
    monkeypatch.setattr("aphrodite.app.discover_adapter_specs", lambda: ({"demo": spec}, {}))

    response = TestClient(create_app()).get("/demo/ping")

    assert response.status_code == 404
