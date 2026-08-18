from __future__ import annotations

from fastmcp import FastMCP

from mcp_pnp.glossary import explicar
from mcp_pnp.registry import listar
from mcp_pnp.tools import register_all


def _register_resources(mcp: FastMCP) -> None:
    @mcp.resource("pnp://glossario/{termo}")
    def glossario_resource(termo: str) -> dict:
        return explicar(termo)

    @mcp.resource("pnp://indicadores")
    def indicadores_resource() -> list:
        return [
            {
                "codigo": i.codigo,
                "nome": i.nome,
                "familia": i.familia,
                "oficial": i.oficial,
                "tool": i.tool,
            }
            for i in listar()
        ]


def _register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt("diagnostico_gestao")
    def diagnostico_gestao(instituicao: str, ano: int | None = None) -> str:
        ref = str(ano) if ano else "o último ano carregado"
        return (
            f"Faça o diagnóstico de gestão de {instituicao} em {ref}. "
            "Comece por pnp_status_base. Consulte ENME, ALRMP, ALMTEC, ENEVA e GACM. "
            "Use pnp_glossario para definir cada sigla. Não invente número ausente; "
            "declare fonte oficial ou derivada."
        )

    @mcp.prompt("comparar_pares")
    def comparar_pares(
        indicador: str,
        esquerda: str,
        direita: str,
        ano: int | None = None,
    ) -> str:
        ref = f" em {ano}" if ano else ""
        return (
            f"Compare {indicador} entre {esquerda} e {direita}{ref}. "
            "Use pnp_comparar e pnp_glossario. A resposta é fonte=derivada."
        )

    @mcp.prompt("checar_percentuais_legais")
    def checar_percentuais_legais(instituicao: str, ano: int | None = None) -> str:
        ref = f" em {ano}" if ano else ""
        return (
            f"Verifique os percentuais legais de {instituicao}{ref}: "
            "ALMTEC (meta 50%), ALMPROF (meta 20%) e ALMEJA (meta 10%). "
            "Informe valor, meta e desvio. Não recálcule; use as tools oficiais."
        )


def create_server() -> FastMCP:
    mcp = FastMCP("pnp")
    register_all(mcp)
    _register_resources(mcp)
    _register_prompts(mcp)
    return mcp
