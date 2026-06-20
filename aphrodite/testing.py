from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from .router import DispatchRouter, parse_custom_id


def dispatch_once(handler: Any, custom_id: str, context: dict | None = None) -> dict:
    parsed = parse_custom_id(custom_id)
    router = DispatchRouter()
    router.register(parsed.system, handler)
    return router.dispatch(custom_id, context)


def make_adapter_app(spec: Any) -> FastAPI:
    app = FastAPI()
    if spec.router:
        app.include_router(spec.router, prefix=f"/{spec.system}")
    return app


def make_adapter_client(spec: Any) -> TestClient:
    return TestClient(make_adapter_app(spec))


def assert_result_ok(result: dict) -> None:
    if result.get("ok") is not True:
        raise AssertionError(result)


__all__ = [
    "assert_result_ok",
    "dispatch_once",
    "make_adapter_app",
    "make_adapter_client",
]
