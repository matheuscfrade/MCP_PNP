"""Entrypoint HTTP / Prefect Horizon. Horizon ignora o bloco ``__main__``."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mcp_pnp.server import mcp  # noqa: E402

if __name__ == "__main__":
    import os

    mcp.run(
        transport="http",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
