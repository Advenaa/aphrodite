from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_create_app_accepts_explicit_config(monkeypatch):
    monkeypatch.delenv("APHRODITE_CORS_ORIGINS", raising=False)
    from aphrodite.app import create_app
    from aphrodite.config import AphroditeConfig

    cfg = AphroditeConfig(cors_origins=("https://example.com",))
    app = create_app(config=cfg)
    assert any(m.cls.__name__ == "CORSMiddleware" for m in app.user_middleware)


def test_create_app_root_path_for_embedding():
    from aphrodite.app import create_app

    app = create_app(root_path="/api/aphrodite")
    assert app.root_path == "/api/aphrodite"


def test_create_app_defaults_to_load_config(monkeypatch):
    monkeypatch.delenv("APHRODITE_CORS_ORIGINS", raising=False)
    from aphrodite.app import create_app

    app = create_app()
    assert app.title == "Aphrodite"
    assert app.root_path == ""


def test_create_app_config_modules_register(monkeypatch):
    monkeypatch.setenv("APHRODITE_MODULES", "image_gen")
    from fastapi.testclient import TestClient
    from aphrodite.app import create_app
    from aphrodite.config import AphroditeConfig

    cfg = AphroditeConfig(modules=("foo", "bar"))
    with TestClient(create_app(config=cfg)) as client:
        status = client.get("/status").json()
    assert status["registered_systems"] == ["bar", "foo"]
    assert status["modules"] == ["foo", "bar"]
