import pytest
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError


def test_ok_oficial():
    body = ok(
        fonte="oficial",
        edicao_pnp="2026",
        ano=2025,
        indicador="ENME",
        unidade_medida="matriculas_equivalentes",
        filtros_aplicados={"instituicao": "IFMG", "ano": 2025},
        registros=[{"instituicao_sigla": "IFMG", "valor": 10.0}],
    )
    assert body["fonte"] == "oficial"
    assert body["indicador"] == "ENME"
    assert body["total_registros"] == 1
    assert body["truncado"] is False
    assert body["aviso"] is None


def test_erro_base_vazia_mensagem_pt():
    err = PnpError("base_vazia")
    assert err.codigo == "base_vazia"
    assert "pnp_sincronizar" in err.message
    assert "mcp-pnp sync" in err.message


def test_limite_invalido():
    with pytest.raises(PnpError) as ei:
        raise PnpError("limite_invalido")
    assert "500" in ei.value.message
