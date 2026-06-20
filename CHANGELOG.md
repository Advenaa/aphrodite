# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Extensible adapter platform: third-party adapters are discovered via the `aphrodite.adapters` entry-point group, with a typed `AdapterSpec` contract and fail-loud `discover_adapter_specs()`.
- Adapter route seam: a discovered adapter can contribute a FastAPI router, auto-mounted under `/<system>`.
- Public SDK (`aphrodite.sdk`) and testing kit (`aphrodite.testing`) for adapter authors.
- Embeddable `create_app(config=, root_path=)` factory for mounting Aphrodite inside a larger app.
- Per-adapter lifespan with failure isolation and a configurable timeout.
- Per-adapter namespaced configuration via `adapter_env()`, plus the `APHRODITE_MODULES=+name` append form.
- `aphrodite run --adapter` dev-runner (no install required; uvicorn reload).
- `aphrodite scaffold` generates an installable adapter package with a FastAPI router and tests.
- Adapter load/mount/lifespan errors surfaced in `/status`; `doctor` adapter lint and dependency-health check.
- MCP: discovered adapters exposed via the `aphrodite_adapters` and `aphrodite_dispatch` tools.
- `aphrodite update` / `aphrodite version` commands.
- Daily "update available" notification (opt out via `APHRODITE_NO_UPDATE_NOTIFIER=1`).
- One-line `install.sh` installer/updater.
- `doctor` reports whether a newer version is available.
- `aphrodite easysetup` prints paste-ready Hermes setup and MCP registration guidance.

### Changed

- Adapter `handle()` responses standardized on the `{"ok": ...}` dialect; the legacy `handled` key was dropped (breaking for adapters that read `handled`).
- Public docs and defaults now use generic operator/profile wording instead of private deployment names; `APHRODITE_ACP_PROFILE` defaults to `default`.

### Fixed

- macOS staleness check no longer depends on GNU `date -d`; service timestamps are parsed in pure Python.

### Security

- Mounted adapter routers require bearer-token auth by default (`APHRODITE_ADAPTER_AUTH_TOKEN`).
- `APHRODITE_TRUSTED_ADAPTERS` allowlist plus mount-time quarantine, so a failing adapter cannot crash startup.
- Adapter trust model documented in `SECURITY.md`.
- Operator-private ledgers and deployment identifiers were removed from the public tree; keep local runbooks under the gitignored `.local/` overlay.
