# Module adapters

Aphrodite routes Discord component custom IDs and HTTP dispatch calls through `aphrodite.router.DispatchRouter`.

## Custom ID format

The router expects this form:

```text
system:v1:action:arg1:arg2
```

Parsing rules from `aphrodite/router.py`:

- `system` selects a registered adapter.
- `v1` is the supported custom-id version.
- `action` selects behavior inside the adapter.
- Remaining colon-separated fields are passed as `payload: list[str]`.
- The adapter also receives a `context: dict[str, Any]` built by the caller.

A successful dispatch response includes `ok`, `system`, `version`, `action`, `payload`, and `result`. Unknown systems, unsupported versions, parsing errors, and adapter exceptions return structured `ok: false` responses instead of escaping through the HTTP boundary.

## Bundled adapters

`aphrodite.app.build_router()` registers the configured modules from
`APHRODITE_MODULES`. The default public set is
`image_gen,skillopt,acp_relay`.

| Adapter | Purpose | Standalone behavior |
| --- | --- | --- |
| `skillopt` | Manages SkillOpt runs, diffs, evaluations, review HTML, bundles, and candidate import/export artifacts. | Self-contained aside from configured local storage and optional train commands. |
| `image_gen` | Provides a dispatch status action and the `/image/generate` HTTP route for Codex-backed image generation. | Live HTTP generation requires Hermes Codex/OpenAI OAuth from the private `agent` stack; no plain API-key environment path exists. |
| `acp_relay` | Bridges Aphrodite to an external ACP agent runtime and exposes both dispatch and `/acp/*` HTTP surfaces. | Requires a working external Hermes/ACP runtime for real turns; fake transports can test the Aphrodite-owned pieces. |

Adapters that bridge private Hermes plugins belong in the operator overlay, not
the public module set. Custom modules can still be registered by listing their
names in `APHRODITE_MODULES`; unknown names are wired to a placeholder handler
so startup remains deterministic.

## Adding an adapter

1. Create or update a module under `aphrodite/modules/`.
2. Expose a callable with this signature:

```python
def handle(action: str, payload: list[str], context: dict[str, Any]) -> dict[str, Any]:
    ...
```

3. Return dictionaries with stable fields. Prefer `ok: true` or `ok: false` plus an `error` string for failures.
4. Register the module in `aphrodite/app.py` inside `build_router()`:

```python
elif system == "my_adapter":
    from .modules.my_adapter import handle as handle_my_adapter

    router.register(system, handle_my_adapter)
```

5. Add the adapter name to `APHRODITE_MODULES` when it should be active.

Keep adapter boundaries narrow: Aphrodite should call public plugin/runtime APIs and should not patch the external runtime core.

## Image generation auth

`aphrodite/modules/image_gen.py` does not read `OPENAI_API_KEY` or any other
plain API-key environment variable for the HTTP route. `/image/generate` calls
`_build_codex_client()`, which reads a Codex/OpenAI OAuth token through the
private Hermes `agent.auxiliary_client` stack and constructs:

```python
openai.OpenAI(
    api_key=token,
    base_url="https://chatgpt.com/backend-api/codex",
    ...
)
```

If that private OAuth token is unavailable, the route returns an
`auth_required` error and performs no generation. The standalone integration
path is programmatic: import `generate_image` and pass a client you own, for
example `generate_image(payload, client=<openai.OpenAI instance>)`.

Model selection can still be influenced with `APHRODITE_IMAGE_GEN_MODEL` or
`OPENAI_IMAGE_MODEL`, but those variables select quality/model only; they do
not authenticate the OpenAI/Codex client.

## ACP relay

`aphrodite/modules/acp_relay.py` bridges Aphrodite to an external ACP agent runtime while Aphrodite owns the conversation database and HTTP boundary.

Public surfaces:

- `handle(action, payload, context)` for `DispatchRouter` registration. Actions `health`, `readiness`, and `status` report relay readiness. Other actions currently return a handled-false response that points callers to the `/acp` HTTP routes.
- `router = APIRouter(prefix="/acp", tags=["acp_relay"])`, included by `create_app()`, with conversation and turn endpoints. `/acp/*` requires a bearer token only when `APHRODITE_ACP_AUTH_TOKEN` is set.
- `AcpRelay`, `ConversationStore`, and configuration helpers used by the HTTP router and tests.

Runtime behavior:

- Conversation metadata, turns, and successful idempotent turn responses are stored in SQLite owned by Aphrodite.
- The real transport spawns `hermes -p <profile> acp`, creates or resumes an ACP session, explicitly selects the configured engine, and drives one ACP turn.
- If `APHRODITE_ACP_PROVIDER` and `APHRODITE_ACP_MODEL` are both set, that override wins. Otherwise the relay uses the spawned Hermes profile's own current model; no provider/model default is forced.
- The `acp` Python client is imported lazily inside `acp_transport`; environments that do not install the optional client can still import the module and use tests/fake transports.
- Default profile, provider, model, binary, working directory, database path, turn timeout, optional auth token, profile allowlist, cwd override gate, and headless approval/hook toggles are configurable with `APHRODITE_ACP_*` environment variables.
- Conversation creation can be constrained with `APHRODITE_ACP_ALLOWED_PROFILES`; request `cwd` overrides are ignored unless `APHRODITE_ACP_ALLOW_CWD_OVERRIDE=true` and the requested directory is under the configured relay cwd.
- `GET /acp/conversations` supports `limit`/`offset` pagination. `POST /acp/conversations/{conversation_id}/turns` accepts an `Idempotency-Key` header or `idempotency_key` payload field.
- Readiness includes executable, cwd, database-writability, and ACP-library checks. Transport failures map to `502`; stale external ACP sessions are replaced with fresh sessions, losing only the upstream ACP context.
- Turn responses include an `incomplete` flag for non-end stop reasons. The relay is intentionally text-only: assistant/thought text is retained, while non-text ACP content blocks are ignored.

Default relay settings in the current code are profile `forge` and timeout `240.0` seconds. Provider and model are unset by default, so the relay uses the Hermes profile's configured engine unless `APHRODITE_ACP_PROVIDER` and `APHRODITE_ACP_MODEL` are both set. Auto-approve and accept-hooks toggles default to true so headless forge turns continue to run without prompting.
