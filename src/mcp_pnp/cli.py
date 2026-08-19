from __future__ import annotations

import os
import sys

from mcp_pnp.bootstrap import ensure_database
from mcp_pnp.config import Settings
from mcp_pnp.ingest.sync import sync
from mcp_pnp.server import create_server


def _parse_serve(argv: list[str]) -> tuple[str, int]:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    rest = list(argv)
    while rest:
        if rest[0] == "--host" and len(rest) >= 2:
            host = rest[1]
            rest = rest[2:]
            continue
        if rest[0] == "--port" and len(rest) >= 2:
            port = int(rest[1])
            rest = rest[2:]
            continue
        raise SystemExit(f"argumento desconhecido: {rest[0]}")
    return host, port


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
    if argv[:1] == ["serve"]:
        host, port = _parse_serve(argv[1:])
        ensure_database()
        create_server().run(transport="http", host=host, port=port)
        return
    ensure_database()
    create_server().run()
