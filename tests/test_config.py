from pathlib import Path

from mcp_pnp.config import Settings


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("PNP_DB_PATH", raising=False)
    monkeypatch.delenv("PNP_CACHE_DIR", raising=False)
    monkeypatch.delenv("PNP_EXTRATOR_BASE", raising=False)
    monkeypatch.delenv("PNP_MAX_REGISTROS", raising=False)
    monkeypatch.delenv("FASTMCP_CLOUD_URL", raising=False)
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("LAMBDA_TASK_ROOT", raising=False)
    s = Settings.from_env()
    assert s.db_path.name == "pnp.sqlite"
    assert s.extrator_base == "https://moduloextratorpnp.mec.gov.br"
    assert s.max_registros == 200


def test_hosted_usa_tmp(monkeypatch):
    monkeypatch.delenv("PNP_DB_PATH", raising=False)
    monkeypatch.delenv("PNP_CACHE_DIR", raising=False)
    monkeypatch.setenv("FASTMCP_CLOUD_URL", "https://pnp.fastmcp.app")
    s = Settings.from_env()
    assert s.db_path == Path("/tmp/pnp/pnp.sqlite")
    assert s.cache_dir == Path("/tmp/pnp/cache")


def test_max_registros_capped(monkeypatch):
    monkeypatch.setenv("PNP_MAX_REGISTROS", "9999")
    s = Settings.from_env()
    assert s.max_registros == 500
