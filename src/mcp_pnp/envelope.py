from __future__ import annotations

from typing import Any

from mcp_pnp.errors import PnpError

ok_fonte = {"oficial", "derivada"}


def ok(
    *,
    fonte: str,
    edicao_pnp: str | None,
    ano: int | None,
    indicador: str,
    unidade_medida: str,
    filtros_aplicados: dict[str, Any],
    registros: list[dict[str, Any]],
    truncado: bool = False,
    aviso: str | None = None,
) -> dict[str, Any]:
    if fonte not in ok_fonte:
        raise ValueError(fonte)
    return {
        "fonte": fonte,
        "edicao_pnp": edicao_pnp,
        "ano": ano,
        "indicador": indicador,
        "unidade_medida": unidade_medida,
        "filtros_aplicados": filtros_aplicados,
        "total_registros": len(registros),
        "truncado": truncado,
        "registros": registros,
        "aviso": aviso,
    }
