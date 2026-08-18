from __future__ import annotations

import sys

from mcp_pnp.config import Settings
from mcp_pnp.ingest.sync import sync
from mcp_pnp.server import create_server


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["sync"]:
        from pathlib import Path

        from_dir = None
        rest = argv[1:]
        if rest[:1] == ["--from-dir"] and len(rest) >= 2:
            from_dir = Path(rest[1])
        elif rest:
            from_dir = Path(rest[0])
        print(sync(Settings.from_env(), from_dir=from_dir))
        return
    create_server().run()
