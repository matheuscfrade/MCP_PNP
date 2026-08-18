from pathlib import Path

import httpx
import pytest

from mcp_pnp.config import Settings
from mcp_pnp.db.queries import consultar
from mcp_pnp.db.schema import apply_schema
from mcp_pnp.ingest.client import ExtratorClient
from mcp_pnp.ingest.loader import load_csv
from mcp_pnp.ingest.sync import sync
from mcp_pnp.registry import get


def test_client_escolhe_csv(tmp_path: Path):
    csv = (Path(__file__).parent / "fixtures" / "oferta.csv").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/csv"):
            return httpx.Response(200, text=csv, headers={"content-type": "text/csv"})
        return httpx.Response(404, text="no")

    transport = httpx.MockTransport(handler)
    client = ExtratorClient("https://extrator.test", transport=transport)
    text = client.download_csv(3)
    assert "Número de Matrículas" in text


def test_loader_normaliza_e_consulta(tmp_path: Path, monkeypatch):
    db = tmp_path / "pnp.sqlite"
    import sqlite3
    conn = sqlite3.connect(db)
    apply_schema(conn)
    conn.close()
    raw = (Path(__file__).parent / "fixtures" / "oferta.csv").read_text(encoding="utf-8")
    load_csv(db, "oferta", raw, ano_edicao=2025, edicao_pnp="2026")
    body = consultar(db, get("ENME"), {"instituicao": "IFMG", "ano": 2025})
    assert body["registros"][0]["valor"] == 80.5
