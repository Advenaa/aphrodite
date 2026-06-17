#!/usr/bin/env bash
set -euo pipefail

main() {
  # PowerShell equivalent for Windows is planned.
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Aphrodite needs Python 3.10 or newer." >&2
    echo "Please install python3, then run this installer again." >&2
    exit 1
  fi

  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    echo "Aphrodite needs Python 3.10 or newer." >&2
    echo "Please upgrade python3, then run this installer again." >&2
    exit 1
  fi

  local INSTALL_ROOT="${APHRODITE_HOME:-$HOME/.local/share/aphrodite}"
  local VENV="$INSTALL_ROOT/venv"
  local BIN_DIR="${APHRODITE_BIN_DIR:-$HOME/.local/bin}"
  local BIN="$BIN_DIR/aphrodite"
  local CONFIG_DIR="$HOME/.config/aphrodite"
  local CACHE_DIR="$HOME/.cache/aphrodite"
  local PACKAGE_SPEC="aphrodite-sidecar[mcp,acp] @ git+https://github.com/Advenaa/aphrodite"

  mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$CONFIG_DIR" "$CACHE_DIR"

  if [ ! -x "$VENV/bin/python" ]; then
    echo "Creating Aphrodite Python environment..."
    python3 -m venv "$VENV"
  fi

  echo "Installing or updating Aphrodite..."
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install --upgrade "$PACKAGE_SPEC"

  local tmp
  tmp="$(mktemp "$BIN_DIR/.aphrodite.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT

  {
    printf '%s\n' '#!/usr/bin/env bash'
    printf 'VENV=%q\n' "$VENV"
    printf '%s\n' 'exec "$VENV/bin/python" -m aphrodite.cli "$@"'
  } >"$tmp"
  chmod +x "$tmp"
  mv "$tmp" "$BIN"
  trap - EXIT

  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
      echo "Note: $BIN_DIR is not on your PATH yet. Add it to your shell profile or restart your terminal so 'aphrodite' works everywhere." >&2
      ;;
  esac

  "$BIN" version 2>/dev/null || true
  echo "Aphrodite is ready. Next: aphrodite doctor"
}

main "$@"
