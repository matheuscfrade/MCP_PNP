from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp_pnp.config import Settings
from mcp_pnp.db.schema import apply_schema
from mcp_pnp.errors import PnpError
from mcp_pnp.ingest.catalog import EXTRATOR_CONJUNTOS, tabela_do_arquivo
from mcp_pnp.ingest.client import ExtratorClient
from mcp_pnp.ingest.loader import load_csv


def sync(
    settings: Settings,
    client: ExtratorClient | None = None,
    from_dir: Path | None = None,
) -> dict[str, Any]:
    if from_dir is not None:
        return sync_from_dir(settings, from_dir)
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


def sync_from_dir(settings: Settings, directory: Path) -> dict[str, Any]:
    pasta = directory.expanduser().resolve()
    if not pasta.is_dir():
        raise PnpError("sync_falhou", f"pasta inexistente: {pasta}")

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    apply_schema(conn)
    conn.execute(
        "INSERT INTO sync_log(iniciado_em, status, detalhe) VALUES (?, 'ok', ?)",
        (datetime.now(timezone.utc).isoformat(), f"local:{pasta}"),
    )
    conn.commit()
    conn.close()

    encontrados: list[tuple[Path, str]] = []
    for csv_path in sorted(pasta.glob("*.csv")):
        tabela = tabela_do_arquivo(csv_path.name)
        if tabela:
            encontrados.append((csv_path, tabela))

    if not encontrados:
        raise PnpError("sync_falhou", f"nenhum CSV do Extrator em {pasta}")

    carregados: list[str] = []
    falhas: list[str] = []
    for csv_path, tabela in encontrados:
        try:
            raw = csv_path.read_text(encoding="utf-8-sig")
            n = load_csv(
                settings.db_path,
                tabela,
                raw,
                ano_edicao=2025,
                edicao_pnp="2026",
            )
            carregados.append(f"{csv_path.name}->{tabela}:{n}")
        except Exception as exc:  # noqa: BLE001
            falhas.append(f"{csv_path.name}: {exc}")

    if falhas and not carregados:
        raise PnpError("sync_falhou", "; ".join(falhas))
    return {"ok": True, "origem": str(pasta), "carregados": carregados, "falhas": falhas}
