# ACP relay

`aphrodite/modules/acp_relay.py` lets Aphrodite bridge HTTP or dispatch calls to an external ACP agent runtime while keeping conversation state in Aphrodite-owned SQLite.

## Public surfaces

The module exposes three integration points.

### FastAPI router

```python
router = APIRouter(prefix="/acp", tags=["acp_relay"])
```

`aphrodite.app.create_app()` includes this router. Routes include:

- `GET /acp/health` — relay readiness/configuration summary.
- `POST /acp/conversations` — create a conversation record.
- `GET /acp/conversations` — list conversations with `limit` and `offset` pagination.
- `GET /acp/conversations/{conversation_id}` — read one conversation.
- `DELETE /acp/conversations/{conversation_id}` — delete one conversation.
- `POST /acp/conversations/{conversation_id}/turns` — send one user message through the ACP transport, optionally with an idempotency key.

### Dispatch handler

```python
def handle(action: str, payload: list[str], context: dict[str, Any]) -> dict[str, Any]:
    ...
```

Registering `acp_relay` in `APHRODITE_MODULES` makes this callable available through `DispatchRouter`. Actions `health`, `readiness`, and `status` return the readiness payload. Other dispatch actions currently return a handled-false response that points callers to the `/acp` HTTP routes.

### Relay classes

- `RelayConfig` stores profile, model, provider, binary, working directory, timeout, database path, and protocol version.
- `ConversationStore` persists conversations and turns in SQLite.
- `AcpRelay` orchestrates conversation creation, lookup, deletion, and turn execution.
- `configure_relay()` and `reset_relay()` let tests or embedding code replace the process-wide relay singleton.

## Runtime model

For a real turn, `acp_transport()` spawns:

```text
hermes -p <profile> acp
```

It then uses the ACP client protocol to create or resume a session and selects the engine via `session/set_model` before prompting. An explicit `APHRODITE_ACP_PROVIDER`+`APHRODITE_ACP_MODEL` override wins; otherwise the relay reads the session's own `current_model_id` (the spawned profile's configured engine) and sets that. Setting it explicitly is required because some engines (e.g. `openai-codex`) reject an empty model and the ACP session does not auto-apply its current model. It then sends the user message and collects assistant reply and thought chunks.

The `acp` Python client is imported lazily inside `acp_transport()`. This keeps the module importable when the optional ACP client is not installed. In that case, real turns fail with an `AcpTransportError`, while tests and fake transports can still use the rest of the module.

The subprocess environment sets these defaults only when the matching relay toggles are enabled:

- `HERMES_YOLO_MODE=1` when `APHRODITE_ACP_AUTO_APPROVE` is true.
- `HERMES_ACCEPT_HOOKS=1` when `APHRODITE_ACP_ACCEPT_HOOKS` is true.

Both relay toggles default to true, so an existing headless agent runtime flow does not block on prompts. If `APHRODITE_ACP_AUTO_APPROVE` is false, ACP permission requests are denied instead of auto-approved and `HERMES_YOLO_MODE` is not injected. If `APHRODITE_ACP_ACCEPT_HOOKS` is false, `HERMES_ACCEPT_HOOKS` is not injected.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APHRODITE_ACP_PROFILE` | `default` | Profile passed to `hermes -p <profile> acp`. |
| `APHRODITE_ACP_MODEL` | (unset) | Optional model override; only used with `APHRODITE_ACP_PROVIDER`. When unset, the relay uses the Hermes profile's own current model. |
| `APHRODITE_ACP_PROVIDER` | (unset) | Optional provider override; only used with `APHRODITE_ACP_MODEL`. When unset, the relay uses the Hermes profile's own current model. |
| `APHRODITE_ACP_HERMES_BIN` | discovered `hermes` binary | Explicit executable path or command name for the external runtime. |
| `APHRODITE_ACP_DB` | `<hermes_root>/aphrodite/acp_relay.sqlite3` | SQLite database path. |
| `APHRODITE_ACP_CWD` | shared Hermes root | Working directory for the subprocess and base directory for allowed request `cwd` overrides. |
| `APHRODITE_ACP_TURN_TIMEOUT` | `240.0` | Maximum seconds for one ACP turn. |
| `APHRODITE_ACP_AUTH_TOKEN` | (unset; no auth) | Optional bearer token for `/acp/*`. Unset keeps local routes open; set requires `Authorization: Bearer <token>`. |
| `APHRODITE_ACP_ALLOWED_PROFILES` | (unset; any profile) | Optional comma-separated profile allowlist. Unset allows any requested profile. |
| `APHRODITE_ACP_ALLOW_CWD_OVERRIDE` | `false` | Gates request payload `cwd` overrides. By default request `cwd` is ignored and the configured cwd is used. |
| `APHRODITE_ACP_AUTO_APPROVE` | `true` | Auto-approves ACP permission prompts and injects `HERMES_YOLO_MODE=1` unless already set. Set false to deny prompts. |
| `APHRODITE_ACP_ACCEPT_HOOKS` | `true` | Injects `HERMES_ACCEPT_HOOKS=1` unless already set. Set false to avoid accepting hooks automatically. |

`RelayConfig.model_choice_id()` returns a model choice only when both provider and model are configured:

```text
<provider>:<model>
```

If either value is unset, it returns `None`, meaning "no override" — the relay then falls back to the session's own `current_model_id`.

## Security and request validation

The relay is permissive by default for local use. Set `APHRODITE_ACP_AUTH_TOKEN` to require `Authorization: Bearer <token>` on every `/acp/*` route; when the variable is unset, the auth dependency is a no-op.

Conversation creation accepts only the known fields `profile`, `model`, `provider`, `cwd`, and `title`. Unknown keys or non-string values are rejected with `422`. Empty strings are treated as unset.

`APHRODITE_ACP_ALLOWED_PROFILES` can restrict requested profiles to a comma-separated allowlist. When the allowlist is unset, any profile may be requested. If it is set and a request names a profile outside the list, creation fails with `403`.

Request `cwd` overrides are ignored by default. `APHRODITE_ACP_ALLOW_CWD_OVERRIDE=true` enables them, but only for existing directories at or below the configured relay cwd; invalid or out-of-tree directories fail with `403`.

Headless approval controls are also explicit. `APHRODITE_ACP_AUTO_APPROVE` defaults to true, preserving the existing allow-and-continue behavior; when false, permission prompts are denied and `HERMES_YOLO_MODE` is not added. `APHRODITE_ACP_ACCEPT_HOOKS` also defaults to true; when false, `HERMES_ACCEPT_HOOKS` is not added.

## Readiness

`GET /acp/health` reports the relay configuration and readiness. The response keeps the existing fields such as `profile`, `model`, `provider`, `model_choice`, `hermes_bin`, `hermes_bin_found`, and `db_path`, and adds a `checks` map:

| Check | Meaning |
| --- | --- |
| `bin_runnable` | The configured Hermes binary can be found and is executable when it is an existing path. |
| `cwd_ok` | The configured relay cwd exists and is a directory. |
| `db_writable` | The SQLite database parent directory exists or can be created and is writable; `:memory:` is treated as writable. |
| `acp_library` | The optional Python ACP client imports successfully. |

The top-level `ok` value is true only when `bin_runnable`, `cwd_ok`, `db_writable`, and `acp_library` are all true.

## Conversation API robustness

`GET /acp/conversations` is paginated. Query parameter `limit` defaults to `50` and is clamped to `1..200`; `offset` defaults to `0` and is clamped to zero or greater. The response shape is:

```json
{
  "conversations": [],
  "limit": 50,
  "offset": 0
}
```

`POST /acp/conversations/{conversation_id}/turns` is idempotent when the caller supplies a key. Send it as the `Idempotency-Key` header or as `idempotency_key` in the JSON payload; the header wins when both are present. A repeated key for the same conversation returns the stored successful turn response and does not run the transport again. Failed turns are not cached.

All ACP transport failures are normalized to `AcpTransportError` and the HTTP route maps them to `502`. Client cancellation is not wrapped, so the underlying subprocess context can still tear down normally.

If a conversation has a stored ACP session id but the external runtime can no longer load it, the relay self-heals by creating a fresh ACP session and persisting the new session id on the successful turn. The prior upstream ACP context is lost in that case, though Aphrodite's own recorded conversation history remains in SQLite.

Turn responses include `incomplete`. It is `false` for `stop_reason` values `end_turn` or an empty string, and `true` for non-end stop reasons such as `max_tokens`, `refusal`, or `cancelled`. Non-empty incomplete replies still return `200`; empty assistant replies still fail before recording and are returned as `502`.

Successful turn responses include the assistant text, any captured thoughts, stop reason, ACP session id, and the incomplete flag:

```json
{
  "conversation_id": "conversation-id",
  "reply": "assistant text",
  "thoughts": [],
  "stop_reason": "end_turn",
  "acp_session_id": "upstream-session-id",
  "incomplete": false
}
```

The relay intentionally has a text-only chunk policy. Assistant text chunks are accumulated into the reply, thought text is tracked separately, and non-text content blocks such as images, audio, or resources are ignored by design.

## Minimal local smoke

1. Install the optional ACP client in the environment if you want real turns.
2. Set any needed `APHRODITE_ACP_*` overrides.
3. Start Aphrodite.
4. Check readiness:

```sh
curl http://127.0.0.1:9079/acp/health
```

5. Create a conversation, then post turns to `/acp/conversations/{conversation_id}/turns`.

Keep hostnames, tokens, profile homes, and deployment paths in private configuration, not in tracked docs.
