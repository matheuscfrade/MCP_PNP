from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_pnp.db.queries import consultar
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.registry import Indicador, get

_RAZAO = {"percentual", "indice", "razao", "reais_por_mateq"}


def _resolve(indicador: Indicador | str) -> Indicador:
    return indicador if isinstance(indicador, Indicador) else get(indicador)


def _nums(registros: list[dict[str, Any]]) -> list[float]:
    out: list[float] = []
    for row in registros:
        val = row.get("valor")
        if val is None:
            continue
        try:
            out.append(float(val))
        except (TypeError, ValueError):
            continue
    return out


def _agregar(indicador: Indicador, registros: list[dict[str, Any]]) -> float | None:
    vals = _nums(registros)
    if not vals:
        return None
    if indicador.unidade_medida in _RAZAO:
        return sum(vals) / len(vals)
    return sum(vals)


def _com_limite(filtros: dict[str, Any]) -> dict[str, Any]:
    out = dict(filtros)
    out.setdefault("limite", 500)
    return out


def _percentil(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    p = 50.0 if p < 0 or p > 100 else float(p)
    ordered = sorted(vals)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _mediana(vals: list[float]) -> float | None:
    if not vals:
        return None
    ordered = sorted(vals)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def comparar(
    db: Path,
    indicador: Indicador | str,
    esquerda: dict[str, Any],
    direita: dict[str, Any],
) -> dict[str, Any]:
    ind = _resolve(indicador)
    left = consultar(db, ind, _com_limite(esquerda))
    right = consultar(db, ind, _com_limite(direita))
    v_esq = _agregar(ind, left["registros"])
    v_dir = _agregar(ind, right["registros"])
    dif = None if v_esq is None or v_dir is None else v_esq - v_dir
    if dif is None or v_dir in (None, 0):
        pct: float | None = None
    else:
        pct = (dif / v_dir) * 100.0
    return ok(
        fonte="derivada",
        edicao_pnp=left.get("edicao_pnp") or right.get("edicao_pnp"),
        ano=esquerda.get("ano") or direita.get("ano") or left.get("ano"),
        indicador=ind.codigo,
        unidade_medida=ind.unidade_medida,
        filtros_aplicados={"esquerda": esquerda, "direita": direita},
        registros=[
            {
                "valores": {"esquerda": v_esq, "direita": v_dir},
                "diferenca": dif,
                "diferenca_pct": pct,
            }
        ],
        aviso="Comparação calculada no MCP; não é um indicador oficial.",
    )


def evolucao(
    db: Path,
    indicador: Indicador | str,
    filtros: dict[str, Any],
    ano_inicio: int,
    ano_fim: int,
) -> dict[str, Any]:
    ind = _resolve(indicador)
    serie: list[dict[str, Any]] = []
    prev: float | None = None
    for ano in range(int(ano_inicio), int(ano_fim) + 1):
        try:
            body = consultar(db, ind, _com_limite({**filtros, "ano": ano}))
        except PnpError:
            continue
        valor = _agregar(ind, body["registros"])
        if prev is None or prev == 0 or valor is None:
            yoy: float | None = None
        else:
            yoy = ((valor - prev) / prev) * 100.0
        serie.append({"ano": ano, "valor": valor, "variacao_yoy": yoy})
        if valor is not None:
            prev = valor
    return ok(
        fonte="derivada",
        edicao_pnp=None,
        ano=None,
        indicador=ind.codigo,
        unidade_medida=ind.unidade_medida,
        filtros_aplicados={
            **{k: v for k, v in filtros.items() if v is not None},
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
        },
        registros=serie,
        aviso="Série calculada no MCP; anos sem dado foram omitidos.",
    )


def ranking(
    db: Path,
    indicador: Indicador | str,
    nivel: str,
    ordem: str,
    ano: int | None,
    top: int,
) -> dict[str, Any]:
    ind = _resolve(indicador)
    if nivel not in {"instituicao", "unidade"}:
        raise PnpError("sem_registros", f"nível inválido: {nivel}")
    chave = "instituicao_sigla" if nivel == "instituicao" else "unidade"
    filtros: dict[str, Any] = {"limite": 500}
    if ano is not None:
        filtros["ano"] = ano
    body = consultar(db, ind, filtros)
    grupos: dict[str, list[float]] = {}
    for row in body["registros"]:
        nome = row.get(chave)
        if not nome:
            continue
        val = row.get("valor")
        if val is None:
            continue
        try:
            grupos.setdefault(str(nome), []).append(float(val))
        except (TypeError, ValueError):
            continue
    itens: list[dict[str, Any]] = []
    for nome, vals in grupos.items():
        if ind.unidade_medida in _RAZAO:
            valor = sum(vals) / len(vals)
        else:
            valor = sum(vals)
        itens.append({nivel: nome, "valor": valor})
    reverse = str(ordem).lower() != "asc"
    itens.sort(key=lambda item: item["valor"], reverse=reverse)
    n = max(1, int(top or 10))
    itens = itens[:n]
    for pos, item in enumerate(itens, start=1):
        item["posicao"] = pos
    return ok(
        fonte="derivada",
        edicao_pnp=body.get("edicao_pnp"),
        ano=body.get("ano"),
        indicador=ind.codigo,
        unidade_medida=ind.unidade_medida,
        filtros_aplicados={"nivel": nivel, "ordem": ordem, "ano": body.get("ano"), "top": n},
        registros=itens,
        aviso="Ranking calculado no MCP a partir dos valores oficiais.",
    )


def estatisticas(
    db: Path,
    indicador: Indicador | str,
    filtros: dict[str, Any],
    estatistica: str,
) -> dict[str, Any]:
    ind = _resolve(indicador)
    kind = estatistica.strip().lower()
    recorte = consultar(db, ind, _com_limite(filtros))
    vals = _nums(recorte["registros"])
    if kind == "media":
        resultado = (sum(vals) / len(vals)) if vals else None
    elif kind == "mediana":
        resultado = _mediana(vals)
    elif kind == "percentil":
        resultado = _percentil(vals, float(filtros.get("percentil") or 50))
    elif kind == "participacao":
        rec = _agregar(ind, recorte["registros"])
        rede_filtros = {
            k: v
            for k, v in _com_limite(filtros).items()
            if k not in {"instituicao", "unidade"}
        }
        try:
            rede = consultar(db, ind, rede_filtros)
            total = _agregar(ind, rede["registros"])
        except PnpError:
            total = None
        if rec is None or not total:
            resultado = None
        else:
            resultado = (rec / total) * 100.0
    else:
        raise PnpError("sem_registros", f"estatística inválida: {estatistica}")
    return ok(
        fonte="derivada",
        edicao_pnp=recorte.get("edicao_pnp"),
        ano=recorte.get("ano"),
        indicador=ind.codigo,
        unidade_medida=ind.unidade_medida,
        filtros_aplicados={
            **{k: v for k, v in filtros.items() if v is not None},
            "estatistica": kind,
        },
        registros=[{"estatistica": kind, "valor": resultado, "n": len(vals)}],
        aviso="Estatística calculada no MCP; não é um indicador oficial.",
    )
