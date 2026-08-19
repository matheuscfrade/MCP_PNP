from pathlib import Path

import httpx
import pytest

from mcp_pnp.bootstrap import DEFAULT_DB_URL, ensure_database, hydrate_if_needed
from mcp_pnp.config import Settings
from mcp_pnp.errors import PnpError


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "pnp.sqlite",
        cache_dir=tmp_path / "cache",
        extrator_base="https://extrator.test",
        max_registros=200,
    )


def test_nao_baixa_se_sqlite_existe(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.db_path.write_bytes(b"SQLite format 3\x00local")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"não deveria baixar: {request.url}")

    path = ensure_database(settings, transport=httpx.MockTransport(handler))
    assert path.read_bytes().startswith(b"SQLite format 3")


def test_baixa_quando_falta(tmp_path: Path):
    settings = _settings(tmp_path)
    payload = b"SQLite format 3\x00remoto"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == DEFAULT_DB_URL
        return httpx.Response(200, content=payload)

    path = ensure_database(settings, transport=httpx.MockTransport(handler))
    assert path.read_bytes() == payload


def test_url_override(tmp_path: Path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setenv("PNP_DB_URL", "https://cdn.test/pnp.sqlite")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=b"SQLite format 3\x00ok")

    ensure_database(settings, transport=httpx.MockTransport(handler))
    assert seen == ["https://cdn.test/pnp.sqlite"]


def test_rejeita_arquivo_invalido(tmp_path: Path):
    settings = _settings(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"nao e sqlite")

    with pytest.raises(PnpError) as err:
        ensure_database(settings, transport=httpx.MockTransport(handler))
    assert err.value.codigo == "download_falhou"
    assert not settings.db_path.exists()
    assert not (settings.db_path.parent / "pnp.sqlite.part").exists()


def test_hydrate_ignora_outro_caminho(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PNP_DB_PATH", str(tmp_path / "oficial.sqlite"))
    outro = tmp_path / "nope.sqlite"
    hydrate_if_needed(outro)
    assert not outro.exists()
    assert not (tmp_path / "oficial.sqlite").exists()


def test_skip_download(tmp_path: Path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setenv("PNP_SKIP_DB_DOWNLOAD", "1")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria baixar")

    path = ensure_database(settings, transport=httpx.MockTransport(handler))
    assert path == settings.db_path
    assert not path.exists()
