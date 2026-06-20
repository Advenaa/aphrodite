from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_ok_and_err_return_stable_result_shapes():
    from aphrodite.sdk import err, ok

    assert ok(value=42) == {"ok": True, "value": 42}
    assert err("boom", error_type="validation", field="name") == {
        "ok": False,
        "error": "boom",
        "error_type": "validation",
        "field": "name",
    }


def test_dispatch_once_routes_custom_id_to_handler_system():
    from aphrodite.testing import dispatch_once

    def handler(action, payload, context):
        return {"action": action, "payload": payload, "context": context}

    result = dispatch_once(handler, "demo:v1:run:123", context={"source": "test"})

    assert result == {
        "ok": True,
        "system": "demo",
        "version": "v1",
        "action": "run",
        "payload": ["123"],
        "result": {"action": "run", "payload": ["123"], "context": {"source": "test"}},
    }


def test_make_adapter_client_mounts_spec_router():
    from fastapi import APIRouter

    from aphrodite.modules import AdapterSpec
    from aphrodite.testing import make_adapter_client

    router = APIRouter()

    @router.get("/health")
    def health():
        return {"ok": True}

    def handler(action, payload, context):
        return {"action": action, "payload": payload, "context": context}

    spec = AdapterSpec(system="demo", handle=handler, router=router)

    response = make_adapter_client(spec).get("/demo/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_assert_result_ok_passes_and_raises():
    import pytest

    from aphrodite.testing import assert_result_ok

    assert_result_ok({"ok": True})
    with pytest.raises(AssertionError) as excinfo:
        assert_result_ok({"ok": False})

    assert excinfo.value.args == ({"ok": False},)
