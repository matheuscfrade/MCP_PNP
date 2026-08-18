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


def test_limite_zero_invalido(db_path):
    with pytest.raises(PnpError) as ei:
        consultar(db_path, get("ENME"), {"limite": 0, "ano": 2025})
    assert ei.value.codigo == "limite_invalido"


def test_limite_nao_inteiro(db_path):
    with pytest.raises(PnpError) as ei:
        consultar(db_path, get("ENME"), {"limite": "abc", "ano": 2025})
    assert ei.value.codigo == "limite_invalido"


def test_instituicao_sem_registros(db_path):
    with pytest.raises(PnpError) as ei:
        consultar(db_path, get("ENME"), {"instituicao": "IFINEXISTENTE", "ano": 2025})
    assert ei.value.codigo == "sem_registros"


def test_ano_indisponivel(db_path):
    with pytest.raises(PnpError) as ei:
        consultar(db_path, get("ENME"), {"ano": 2010})
    assert ei.value.codigo == "ano_indisponivel"


def test_tabela_fora_do_allowlist(db_path):
    from mcp_pnp.registry import Indicador

    fake = Indicador(
        codigo="X",
        nome="x",
        familia="x",
        tabela="nao_existe",
        coluna="mateq",
        unidade_medida="x",
        tool="x",
        oficial=False,
    )
    with pytest.raises(ValueError):
        consultar(db_path, fake, {"ano": 2025})
