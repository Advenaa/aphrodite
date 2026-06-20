from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_run_cli_loads_local_adapter_and_starts_reload_server(monkeypatch, tmp_path):
    import aphrodite.cli as cli
    import aphrodite.serve as serve

    calls = []

    class FakeUvicorn:
        @staticmethod
        def run(target, **kwargs):
            calls.append((target, kwargs))

    original_sys_path = list(sys.path)
    monkeypatch.setattr(cli, "maybe_notify_update", lambda command: None)
    monkeypatch.setattr(serve, "uvicorn", FakeUvicorn)
    monkeypatch.setenv("APHRODITE_HOST", "127.0.0.9")
    monkeypatch.setenv("APHRODITE_MODULES", "image_gen")

    try:
        assert cli.main(["run", "--adapter", str(tmp_path), "--port", "9090"]) == 0

        adapter_dir = str(tmp_path.resolve())
        assert sys.path[0] == adapter_dir
        assert calls == [
            (
                "aphrodite.app:create_app",
                {
                    "factory": True,
                    "host": "127.0.0.9",
                    "port": 9090,
                    "reload": True,
                    "reload_dirs": [adapter_dir],
                },
            )
        ]
        assert calls[0][1]["reload_dirs"] == [adapter_dir]
        assert serve.os.environ["APHRODITE_MODULES"] == f"image_gen,+{tmp_path.name}"
    finally:
        sys.path[:] = original_sys_path
