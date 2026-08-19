from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp_pnp.config import Settings
from mcp_pnp.db.schema import TABLES
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.formulas import Formula, formula_de
from mcp_pnp.registry import Indicador

# Table/column identifiers come only from the static registry / DIM_FILTERS;
# filter values are bound parameters.
DIM_FILTERS = {
    "instituicao": "instituicao_sigla",
    "unidade": "unidade",
    "uf": "uf",
    "regiao": "regiao",
    "municipio": "municipio",
    "organizacao_academica": "organizacao_academica",
    "ano": "ano",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise PnpError("base_vazia")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    n = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='edicoes'"
    ).fetchone()[0]
    if n == 0:
        conn.close()
        raise PnpError("base_vazia")
    return conn


def ultimo_ano(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(ano) FROM edicoes").fetchone()
    if row is None or row[0] is None:
        raise PnpError("base_vazia")
    return int(row[0])


def _filtros_sql(
    indicador: Indicador,
    applied: dict[str, Any],
    formula: Formula | None = None,
) -> tuple[list[str], list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    mapping = dict(DIM_FILTERS)
    for extra in indicador.extra_filtros:
        mapping[extra] = extra
    for key, col in mapping.items():
        val = applied.get(key)
        if val is None or key in {"limite", "offset"}:
            continue
        if key == "instituicao":
            where.append(f"UPPER({col}) = UPPER(?)")
        else:
            where.append(f"{col} = ?")
        params.append(val)
    if formula is not None:
        for col, esperado in formula.filtros:
            if applied.get(col) is None:
                where.append(f"{col} = ?")
                params.append(esperado)
    return where, params


def valor_oficial(
    conn: sqlite3.Connection,
    indicador: Indicador,
    applied: dict[str, Any],
    group_by: str | None = None,
) -> list[dict[str, Any]]:
    """Agrega sem LIMIT, com a fórmula oficial do Guia."""
    formula = formula_de(indicador.codigo)
    where, params = _filtros_sql(indicador, applied, formula)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    table = indicador.tabela
    if table not in TABLES:
        raise ValueError(f"tabela não permitida: {table}")

    select = _sql_agregacao(formula)
    group_sql = ""
    group_select = ""
    if group_by:
        if group_by not in DIM_FILTERS.values() and group_by not in {
            "instituicao_sigla",
            "unidade",
        }:
            raise ValueError(group_by)
        group_select = f"{group_by} AS grupo, "
        group_sql = f" GROUP BY {group_by}"
    sql = f"SELECT {group_select}{select} FROM {table} {clause}{group_sql}"
    rows = conn.execute(sql, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        valor = _valor_da_agregacao(formula, item)
        rec: dict[str, Any] = {
            "valor": valor,
            "formula": formula.expressao,
            "numerador": item.get("numerador"),
            "denominador": item.get("denominador"),
        }
        if group_by:
            rec[group_by] = item.get("grupo")
            if group_by == "instituicao_sigla":
                rec["instituicao_sigla"] = item.get("grupo")
            if group_by == "unidade":
                rec["unidade"] = item.get("grupo")
        out.append(rec)
    return out


def _sql_agregacao(formula: Formula) -> str:
    if formula.tipo == "soma":
        return f"SUM({formula.numerador}) AS numerador, NULL AS denominador"
    if formula.tipo == "razao":
        dens = " + ".join(f"COALESCE(SUM({c}), 0)" for c in formula.denominador)
        return f"SUM({formula.numerador}) AS numerador, ({dens}) AS denominador"
    if formula.tipo == "count_distinct":
        return f"COUNT(DISTINCT {formula.count_col}) AS numerador, NULL AS denominador"
    if formula.tipo == "ponderado":
        return (
            f"SUM({formula.numerador} * {formula.peso}) AS numerador, "
            f"SUM({formula.peso}) AS denominador"
        )
    if formula.tipo == "gacm":
        return (
            "SUM(gastos_correntes) AS numerador, "
            "SUM(CASE WHEN gasto_por_mateq > 0 "
            "THEN gastos_correntes / gasto_por_mateq END) AS denominador"
        )
    if formula.tipo == "media":
        return (
            f"AVG({formula.numerador}) AS numerador, "
            f"COUNT({formula.numerador}) AS denominador"
        )
    if formula.tipo == "indisponivel":
        return "NULL AS numerador, NULL AS denominador"
    raise ValueError(formula.tipo)


def _valor_da_agregacao(formula: Formula, item: dict[str, Any]) -> float | None:
    if formula.tipo == "indisponivel":
        return None
    num = item.get("numerador")
    if formula.tipo in {"soma", "count_distinct", "media"}:
        return None if num is None else float(num)
    den = item.get("denominador")
    if num is None or den in (None, 0, 0.0):
        return None
    return float(formula.escala) * float(num) / float(den)


def agregar_oficial(
    db_path: Path,
    indicador: Indicador,
    filtros: dict[str, Any],
    group_by: str | None = None,
) -> list[dict[str, Any]]:
    conn = _connect(db_path)
    try:
        applied = dict(filtros)
        if applied.get("ano") is None:
            applied["ano"] = ultimo_ano(conn)
        elif conn.execute(
            "SELECT 1 FROM edicoes WHERE ano = ?", (applied["ano"],)
        ).fetchone() is None:
            raise PnpError("ano_indisponivel")
        return valor_oficial(conn, indicador, applied, group_by)
    finally:
        conn.close()


def consultar(
    db_path: Path,
    indicador: Indicador,
    filtros: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    raw_limite = filtros["limite"] if "limite" in filtros and filtros["limite"] is not None else settings.max_registros
    try:
        limite = int(raw_limite)
    except (TypeError, ValueError) as exc:
        raise PnpError("limite_invalido") from exc
    if limite < 1 or limite > 500:
        raise PnpError("limite_invalido")
    offset = int(filtros.get("offset") or 0)

    if indicador.tabela not in TABLES:
        raise ValueError(f"tabela não permitida: {indicador.tabela}")

    conn = _connect(db_path)
    try:
        applied = dict(filtros)
        aviso = None
        if applied.get("ano") is None:
            applied["ano"] = ultimo_ano(conn)
            aviso = f"Ano omitido; usando o último ano carregado ({applied['ano']})."
        elif conn.execute(
            "SELECT 1 FROM edicoes WHERE ano = ?", (applied["ano"],)
        ).fetchone() is None:
            raise PnpError("ano_indisponivel")

        formula = formula_de(indicador.codigo)
        where, params = _filtros_sql(indicador, applied, formula)

        sql = (
            f"SELECT * FROM {indicador.tabela} "
            + ("WHERE " + " AND ".join(where) if where else "")
            + " LIMIT ? OFFSET ?"
        )
        detail_params = list(params) + [limite + 1, offset]
        rows = conn.execute(sql, detail_params).fetchall()
        if not rows:
            raise PnpError("sem_registros")

        truncado = len(rows) > limite
        rows = rows[:limite]
        registros = []
        for row in rows:
            item = dict(row)
            item["valor"] = item.get(indicador.coluna)
            registros.append(item)

        oficial = valor_oficial(conn, indicador, applied)
        valor = oficial[0]["valor"] if oficial else None
        componentes = oficial[0] if oficial else {}

        ed = conn.execute(
            "SELECT edicao_pnp FROM edicoes WHERE ano = ?", (applied["ano"],)
        ).fetchone()
        if formula.tipo == "indisponivel":
            aviso = formula.expressao if not aviso else f"{aviso} {formula.expressao}."
        elif aviso and valor is not None:
            aviso = f"{aviso} Valor oficial ({formula.expressao}) = {valor}."
        elif valor is not None:
            aviso = f"Valor oficial ({formula.expressao}) = {valor}."
        if indicador.meta is not None and valor is not None:
            aviso = f"{aviso} Meta: {indicador.meta}. Desvio: {valor - indicador.meta}."
        body = ok(
            fonte="oficial",
            edicao_pnp=ed["edicao_pnp"] if ed else None,
            ano=applied["ano"],
            indicador=indicador.codigo,
            unidade_medida=indicador.unidade_medida,
            filtros_aplicados={k: v for k, v in applied.items() if v is not None},
            registros=registros,
            truncado=truncado,
            aviso=aviso,
        )
        body["valor_oficial"] = valor
        body["formula"] = formula.expressao
        body["numerador"] = componentes.get("numerador")
        body["denominador"] = componentes.get("denominador")
        return body
    finally:
        conn.close()
