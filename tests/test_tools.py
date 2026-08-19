from fastmcp.tools.base import Tool

from mcp_pnp.registry import INDICADORES_MVP
from mcp_pnp.server import create_server


def _tool_names(mcp) -> set[str]:
    """Nomes das tools registradas no FastMCP instalado (3.x, list_tools async)."""
    provider = getattr(mcp, "_local_provider", None)
    if provider is not None:
        return {c.name for c in provider._components.values() if isinstance(c, Tool)}
    listed = mcp.list_tools()
    if hasattr(listed, "__await__"):
        import anyio

        listed = anyio.run(mcp.list_tools)
    return {t.name for t in listed}


def test_tools_mvp_registradas():
    mcp = create_server()
    names = _tool_names(mcp)
    for ind in INDICADORES_MVP:
        assert ind.tool in names, ind.tool
    for extra in (
        "pnp_listar_edicoes",
        "pnp_listar_instituicoes",
        "pnp_listar_unidades",
        "pnp_listar_indicadores",
        "pnp_consultar",
        "pnp_listar_valores",
        "pnp_comparar",
        "pnp_evolucao",
        "pnp_ranking",
        "pnp_agregar",
        "pnp_estatisticas",
        "pnp_glossario",
        "pnp_status_base",
        "pnp_sincronizar",
    ):
        assert extra in names
    assert "pnp_consultar_igc" not in names
    assert "pnp_consultar_acordos_pesquisa" not in names


def test_glossario_enme():
    from mcp_pnp.glossary import explicar

    g = explicar("ENME")
    assert "equivalente" in g["definicao"].lower()


def test_comparar_fonte_derivada(db_path):
    from mcp_pnp.analysis import comparar

    body = comparar(
        db_path,
        "ENME",
        {"instituicao": "IFMG", "ano": 2025},
        {"instituicao": "IFB", "ano": 2025},
    )
    assert body["fonte"] == "derivada"
    rec = body["registros"][0]
    assert rec["valores"]["esquerda"] == 80.5
    assert rec["valores"]["direita"] == 40.0
    assert rec["diferenca"] == 40.5


def test_listar_unidades_instituicao_desconhecida(db_path, monkeypatch):
    from mcp_pnp.tools import pnp_listar_unidades

    monkeypatch.setenv("PNP_DB_PATH", str(db_path))
    body = pnp_listar_unidades(instituicao="XXXX")
    assert body["codigo"] == "instituicao_desconhecida"
