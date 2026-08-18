from mcp_pnp.config import Settings


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("PNP_DB_PATH", raising=False)
    monkeypatch.delenv("PNP_CACHE_DIR", raising=False)
    monkeypatch.delenv("PNP_EXTRATOR_BASE", raising=False)
    monkeypatch.delenv("PNP_MAX_REGISTROS", raising=False)
    s = Settings.from_env()
    assert s.db_path.name == "pnp.sqlite"
    assert s.extrator_base == "https://moduloextratorpnp.mec.gov.br"
    assert s.max_registros == 200


def test_max_registros_capped(monkeypatch):
    monkeypatch.setenv("PNP_MAX_REGISTROS", "9999")
    s = Settings.from_env()
    assert s.max_registros == 500
