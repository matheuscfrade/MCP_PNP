from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_pnp.db.queries import (
    _connect,
    agregar_oficial,
    consultar,
    intervalo_anos,
    ultimo_ano,
)
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.formulas import formula_de
from mcp_pnp.registry import Indicador, get


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
    """Não usar para taxas. Preferir agregar_oficial (SQL, fórmula do Guia)."""
    vals = _nums(registros)
    if not vals:
        return None
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
    v_esq = left.get("valor_oficial")
    v_dir = right.get("valor_oficial")
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
        aviso=(
            f"Comparação com fórmula oficial ({formula_de(ind.codigo).expressao}). "
            "Não é um recálculo dos microdados."
        ),
    )


def evolucao(
    db: Path,
    indicador: Indicador | str,
    filtros: dict[str, Any],
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> dict[str, Any]:
    ind = _resolve(indicador)
    inicio, fim = ano_inicio, ano_fim
    if inicio is None or fim is None:
        conn = _connect(db)
        try:
            minimo, maximo = intervalo_anos(conn, ind.tabela)
        finally:
            conn.close()
        inicio = minimo if inicio is None else inicio
        fim = maximo if fim is None else fim
    serie: list[dict[str, Any]] = []
    prev: float | None = None
    for ano in range(int(inicio), int(fim) + 1):
        try:
            body = consultar(db, ind, _com_limite({**filtros, "ano": ano}))
        except PnpError:
            continue
        valor = body.get("valor_oficial")
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
            "ano_inicio": inicio,
            "ano_fim": fim,
        },
        registros=serie,
        aviso=(
            f"Série com fórmula oficial ({formula_de(ind.codigo).expressao}). "
            "Anos sem dado foram omitidos."
        ),
    )


def ranking(
    db: Path,
    indicador: Indicador | str,
    nivel: str,
    ordem: str,
    ano: int | None,
    top: int,
    filtros: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from mcp_pnp.dimensions import GROUPABLES, coluna_agrupavel

    ind = _resolve(indicador)
    try:
        chave = coluna_agrupavel(nivel, ind)
    except KeyError as exc:
        raise PnpError("agrupamento_invalido", f"nível inválido: {nivel}") from exc
    rotulo = nivel if nivel in GROUPABLES else chave
    applied: dict[str, Any] = dict(filtros or {})
    applied["limite"] = 500
    if ano is not None:
        applied["ano"] = ano
    body = consultar(db, ind, applied)
    oficiais = agregar_oficial(
        db, ind, {k: v for k, v in applied.items() if k != "limite"}, group_by=chave
    )
    itens: list[dict[str, Any]] = []
    for rec in oficiais:
        nome = rec.get(chave)
        if not nome or rec.get("valor") is None:
            continue
        itens.append({rotulo: nome, "valor": rec["valor"]})
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
        filtros_aplicados={
            **{k: v for k, v in applied.items() if v is not None and k != "limite"},
            "nivel": nivel,
            "ordem": ordem,
            "top": n,
        },
        registros=itens,
        aviso=(
            f"Ranking com fórmula oficial ({formula_de(ind.codigo).expressao})."
        ),
    )


def agregar(
    db: Path,
    indicador: Indicador | str,
    group_by: str,
    filtros: dict[str, Any],
) -> dict[str, Any]:
    from mcp_pnp.dimensions import GROUPABLES, coluna_agrupavel

    ind = _resolve(indicador)
    try:
        chave = coluna_agrupavel(group_by, ind)
    except KeyError as exc:
        raise PnpError("agrupamento_invalido", f"group_by inválido: {group_by}") from exc
    rotulo = group_by if group_by in GROUPABLES else chave
    applied = dict(filtros)
    if applied.get("ano") is None:
        conn = _connect(db)
        try:
            applied["ano"] = ultimo_ano(conn)
        finally:
            conn.close()
    oficiais = agregar_oficial(db, ind, applied, group_by=chave)
    itens = []
    for rec in oficiais:
        nome = rec.get(chave)
        if nome is None or rec.get("valor") is None:
            continue
        itens.append(
            {
                rotulo: nome,
                "valor": rec["valor"],
                "numerador": rec.get("numerador"),
                "denominador": rec.get("denominador"),
            }
        )
    itens.sort(key=lambda item: item["valor"], reverse=True)
    return ok(
        fonte="derivada",
        edicao_pnp=None,
        ano=applied.get("ano"),
        indicador=ind.codigo,
        unidade_medida=ind.unidade_medida,
        filtros_aplicados={
            **{k: v for k, v in applied.items() if v is not None},
            "group_by": group_by,
        },
        registros=itens,
        aviso=(
            f"Agregação com fórmula oficial ({formula_de(ind.codigo).expressao}). "
            f"Quebra nativa por {chave}."
        ),
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
        # Média de linhas NÃO é indicador oficial. Expor o valor oficial agregado.
        resultado = recorte.get("valor_oficial")
        kind = "oficial"
    elif kind == "mediana":
        resultado = _mediana(vals)
    elif kind == "percentil":
        resultado = _percentil(vals, float(filtros.get("percentil") or 50))
    elif kind == "participacao":
        rec = recorte.get("valor_oficial")
        rede_filtros = {
            k: v
            for k, v in _com_limite(filtros).items()
            if k not in {"instituicao", "unidade"}
        }
        try:
            rede = consultar(db, ind, rede_filtros)
            total = rede.get("valor_oficial")
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
        aviso=(
            f"Estatística derivada. Valor institucional usa "
            f"{formula_de(ind.codigo).expressao}."
        ),
    )
