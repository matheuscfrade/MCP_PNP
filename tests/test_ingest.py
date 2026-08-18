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


def test_tabela_do_arquivo_extrator():
    from mcp_pnp.ingest.catalog import tabela_do_arquivo

    assert tabela_do_arquivo("DadosGerais.csv") == "oferta"
    assert tabela_do_arquivo("RelacaoAlunoProfessorRAP.csv") == "rap"
    assert tabela_do_arquivo("CassificacaoRacialRendaSexo.csv") == "perfil_discente"


def test_sync_from_dir_percentuais(tmp_path: Path):
    csv = tmp_path / "PercentuaisLegais.csv"
    csv.write_text(
        "Ano;Região;UF;Estado;Organização Acadêmica PNP;Instituicao;"
        "Instituição (Nome);nomeUnidadeRecente;"
        "Matrícula Equivalente | Formação de Professores;"
        "Matrícula Equivalente | Técnicos;"
        "Matrícula Equivalente | Proeja;"
        "Matrícula Equivalente | Geral\n"
        "2025;Sudeste;MG;Minas Gerais;Instituto Federal;IFMG;"
        "Instituto Federal de Minas Gerais;Campus BH;20;50;5;100\n",
        encoding="utf-8",
    )
    settings = Settings(
        db_path=tmp_path / "pnp.sqlite",
        cache_dir=tmp_path / "cache",
        extrator_base="https://extrator.test",
        max_registros=200,
    )
    result = sync(settings, from_dir=tmp_path)
    assert result["ok"] is True
    body = consultar(settings.db_path, get("ALMTEC"), {"instituicao": "IFMG", "ano": 2025})
    assert body["registros"][0]["valor"] == 50.0
