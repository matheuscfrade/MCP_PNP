import pytest
from mcp_pnp.db.queries import consultar
from mcp_pnp.errors import PnpError
from mcp_pnp.registry import get


def test_filtra_instituicao(db_path):
    body = consultar(db_path, get("ENME"), {"instituicao": "ifmg", "ano": 2025})
    assert body["fonte"] == "oficial"
    assert body["indicador"] == "ENME"
    assert body["total_registros"] == 1
    assert body["registros"][0]["instituicao_sigla"] == "IFMG"
    assert body["registros"][0]["valor"] == 80.5


def test_base_vazia(tmp_path):
    missing = tmp_path / "nope.sqlite"
    with pytest.raises(PnpError) as ei:
        consultar(missing, get("ENME"), {})
    assert ei.value.codigo == "base_vazia"


def test_ano_omitido_usa_ultimo(db_path):
    body = consultar(db_path, get("ENM"), {"instituicao": "IFMG"})
    assert body["filtros_aplicados"]["ano"] == 2025
    assert body["aviso"] and "último ano" in body["aviso"]
