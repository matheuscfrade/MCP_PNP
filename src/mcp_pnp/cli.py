from __future__ import annotations

import sys

from mcp_pnp.config import Settings
from mcp_pnp.ingest.sync import sync
from mcp_pnp.server import create_server


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["sync"]:
        print(sync(Settings.from_env()))
        return
    create_server().run()
