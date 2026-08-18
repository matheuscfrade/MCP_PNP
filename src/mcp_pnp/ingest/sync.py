from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from mcp_pnp.config import Settings
from mcp_pnp.db.schema import apply_schema
from mcp_pnp.errors import PnpError
from mcp_pnp.ingest.catalog import EXTRATOR_CONJUNTOS
from mcp_pnp.ingest.client import ExtratorClient
from mcp_pnp.ingest.loader import load_csv


def sync(settings: Settings, client: ExtratorClient | None = None) -> dict[str, Any]:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    apply_schema(conn)
    conn.execute(
        "INSERT INTO sync_log(iniciado_em, status, detalhe) VALUES (?, 'ok', ?)",
        (datetime.now(timezone.utc).isoformat(), "inicio"),
    )
    conn.commit()
    conn.close()
    client = client or ExtratorClient(settings.extrator_base)
    falhas: list[str] = []
    for item in EXTRATOR_CONJUNTOS:
        try:
            raw = client.download_csv(item["id"])
            (settings.cache_dir / f"{item['tabela']}.csv").write_text(
                raw, encoding="utf-8"
            )
            load_csv(
                settings.db_path,
                item["tabela"],
                raw,
                ano_edicao=2025,
                edicao_pnp="2026",
            )
        except Exception as exc:  # noqa: BLE001 — registra e segue o próximo conjunto
            falhas.append(f"{item['tabela']}: {exc}")
    if falhas and len(falhas) == len(EXTRATOR_CONJUNTOS):
        raise PnpError("sync_falhou", "; ".join(falhas))
    return {"ok": True, "falhas": falhas}
