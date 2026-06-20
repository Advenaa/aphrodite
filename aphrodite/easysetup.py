from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

INSTALLER_URL = "https://raw.githubusercontent.com/Frens-Pods/aphrodite/main/install.sh"
MCP_MODULE = "aphrodite.mcp_server"


def aphrodite_python_path(python_path: str | None = None) -> str:
    path = Path(python_path or sys.executable).expanduser()
    return str(path if path.is_absolute() else path.absolute())


def mcp_config(python_path: str | None = None) -> dict[str, Any]:
    return {
        "mcp_servers": {
            "aphrodite": {
                "command": aphrodite_python_path(python_path),
                "args": ["-m", MCP_MODULE],
            }
        }
    }


def build_hermes_prompt(python_path: str | None = None) -> str:
    config = json.dumps(mcp_config(python_path), indent=2)
    return (
        "Install Aphrodite as a Hermes sidecar plugin backend. Keep it external: do not modify Hermes core.\n\n"
        "1. Run:\n"
        f"   curl --proto '=https' --tlsv1.2 -fsSL {INSTALLER_URL} | bash\n\n"
        "2. Register this MCP server config in the active Hermes profile:\n"
        f"{config}\n\n"
        "3. Restart this Hermes session/profile.\n\n"
        "4. Verify:\n"
        "   aphrodite doctor\n"
        "   aphrodite modules\n"
        "   aphrodite serve\n\n"
        "Plugin/module model:\n"
        "- Hermes stays the agent runtime.\n"
        "- Aphrodite exposes MCP, HTTP, Discord, and module-adapter backend surfaces.\n"
        "- Add Aphrodite modules with `aphrodite new-module my_plugin`, install into Aphrodite's Python environment, then enable with `APHRODITE_MODULES=+my_plugin`.\n"
        "- Keep the leading + to append your module without replacing built-ins.\n\n"
        "Important: keep the exact absolute command path above. Do not replace it with $HOME, a guessed path, or a literal '~'."
    )


def easysetup_payload(python_path: str | None = None) -> dict[str, Any]:
    config = mcp_config(python_path)
    return {
        "prompt": build_hermes_prompt(python_path),
        "installer_url": INSTALLER_URL,
        "mcp_config": config,
        "mcp_servers": config["mcp_servers"],
    }
