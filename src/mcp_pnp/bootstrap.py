from __future__ import annotations

import os
from pathlib import Path

import httpx

from mcp_pnp.config import Settings
from mcp_pnp.errors import PnpError

DEFAULT_DB_URL = (
    "https://github.com/matheuscfrade/MCP_PNP/releases/download/"
    "extrator-2025/pnp.sqlite"
)
_SQLITE_MAGIC = b"SQLite format 3"


def _skip_download() -> bool:
    return os.environ.get("PNP_SKIP_DB_DOWNLOAD", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _parece_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(16).startswith(_SQLITE_MAGIC)
    except OSError:
        return False


def ensure_database(
    settings: Settings | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Path:
    """Garante um `pnp.sqlite` local; baixa da release se o arquivo não existir."""
    settings = settings or Settings.from_env()
    path = settings.db_path
    if path.exists() and path.stat().st_size > 0 and _parece_sqlite(path):
        return path
    if _skip_download():
        return path

    url = os.environ.get("PNP_DB_URL", DEFAULT_DB_URL).strip() or DEFAULT_DB_URL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        with httpx.Client(
            transport=transport,
            timeout=300.0,
            follow_redirects=True,
        ) as http:
            with http.stream("GET", url) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_bytes(1024 * 1024):
                        fh.write(chunk)
    except httpx.HTTPError as err:
        tmp.unlink(missing_ok=True)
        raise PnpError("download_falhou", str(err)) from err

    if not _parece_sqlite(tmp):
        tmp.unlink(missing_ok=True)
        raise PnpError("download_falhou", "arquivo baixado não é um SQLite")
    tmp.replace(path)
    return path
