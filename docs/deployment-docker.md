# Container deployment

Aphrodite ships a multi-stage `Dockerfile` and a `docker-compose.yml` example
for running the FastAPI sidecar in a container. This is an alternative to the
bare-metal [systemd + Caddy](deployment.md) path; the same safety posture
applies.

## Bind address: 127.0.0.1 vs 0.0.0.0

The app defaults to `APHRODITE_HOST=127.0.0.1` so a bare-metal process only
listens on loopback unless an operator opts in. A container has its own network
namespace, so the service **must** bind `0.0.0.0` to be reachable through a
published port. The image handles this for you:

- The `Dockerfile` `CMD` runs `uvicorn ... --host 0.0.0.0` (the authoritative
  bind) and sets `APHRODITE_HOST=0.0.0.0` for config consistency.
- The published port still maps to host loopback by default
  (`127.0.0.1:9079:9079`), so a reverse proxy owns the public origin — the
  container is open inside Docker, not on your host's public interface.

The application default in `aphrodite/config.py` is unchanged; only the
container overrides the bind.

## Build and run the image

```sh
docker build -t aphrodite-sidecar:local .
docker run -d --rm --name aphrodite -p 127.0.0.1:9079:9079 aphrodite-sidecar:local
curl -fsS http://127.0.0.1:9079/health
curl -fsS http://127.0.0.1:9079/status
docker stop aphrodite
```

The image installs the `[acp]` extra. The MCP server (`mcp` extra) is not
included by default; add it to the `pip install` line in the `Dockerfile` if you
need it.

## Compose stack

```sh
# Create the private env file first (gitignored). The stack also starts without
# it (loopback-only, CORS and the Discord endpoint disabled).
cp config/aphrodite.env.example config/aphrodite.env

docker compose up -d --build
curl -fsS http://127.0.0.1:9079/health
docker compose logs -f aphrodite
docker compose down
```

Configuration is injected from `config/aphrodite.env` via `env_file` (loaded
with `required: false`). Keep real Discord tokens, public keys, channel IDs, and
hostnames in that file — never in `docker-compose.yml`.

## Reverse proxy

`docker-compose.yml` includes a commented-out `caddy` service that mounts
[`caddy/aphrodite.caddy.example`](../caddy/aphrodite.caddy.example). Edit the
example with a real HTTPS hostname and point its upstream at the `aphrodite`
service name before enabling it. As with bare-metal, the proxy forwards the
public HTTPS origin to the Aphrodite listener.

## Safety checklist

The container path does not relax the production rules:

1. Set `APHRODITE_DISCORD_PUBLIC_KEY` in `config/aphrodite.env` before exposing
   `/discord/interactions`. The endpoint verifies Discord's
   `X-Signature-Ed25519` / `X-Signature-Timestamp` headers against it.
2. Keep the published port on host loopback and front it with the reverse proxy;
   do not publish `0.0.0.0:9079` to the public interface directly.
3. Use `/discord/interactions/dry-run` only for local testing; it intentionally
   skips Discord signatures.
4. Confirm `GET /health` and `GET /status` respond before routing real traffic.
5. Do not auto-expose the service until preflight passes and an operator has
   approved activation.
