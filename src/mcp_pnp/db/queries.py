from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp_pnp.config import Settings
from mcp_pnp.db.schema import TABLES
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
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

        where = []
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

        sql = (
            f"SELECT * FROM {indicador.tabela} "
            + ("WHERE " + " AND ".join(where) if where else "")
            + " LIMIT ? OFFSET ?"
        )
        params.extend([limite + 1, offset])
        rows = conn.execute(sql, params).fetchall()
        if not rows:
            raise PnpError("sem_registros")

        truncado = len(rows) > limite
        rows = rows[:limite]
        registros = []
        for row in rows:
            item = dict(row)
            item["valor"] = item.get(indicador.coluna)
            registros.append(item)

        ed = conn.execute(
            "SELECT edicao_pnp FROM edicoes WHERE ano = ?", (applied["ano"],)
        ).fetchone()
        return ok(
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
    finally:
        conn.close()
