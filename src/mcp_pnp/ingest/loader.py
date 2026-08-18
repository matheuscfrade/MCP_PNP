from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mcp_pnp.db.schema import TABLES
from mcp_pnp.errors import PnpError

HEADER_MAP = {
    "Ano": "ano",
    "Região": "regiao",
    "UF": "uf",
    "Estado": "estado",
    "Organização Acadêmica PNP": "organizacao_academica",
    "Instituicao": "instituicao_sigla",
    "Instituição (Nome)": "instituicao_nome",
    "nomeUnidadeRecente": "unidade",
    "Número de cursos": "n_cursos",
    "Número de Matrículas": "n_matriculas",
    "Matrícula Equivalente | Geral": "mateq",
    "Número de vagas": "n_vagas",
    "Número de inscritos": "n_inscritos",
    "Número de ingressantes": "n_ingressantes",
    "Número de concluintes": "n_concluintes",
}

_NUMERIC_TYPES = {"INTEGER", "REAL", "NUMERIC", "INT", "FLOAT", "DOUBLE"}


def load_csv(
    db_path: Path,
    tabela: str,
    csv_text: str,
    ano_edicao: int,
    edicao_pnp: str,
) -> int:
    if tabela not in TABLES:
        raise PnpError("sync_falhou", f"tabela desconhecida: {tabela}")

    text = csv_text.lstrip("\ufeff")
    first = text.splitlines()[0] if text else ""
    delimiter = ";" if ";" in first else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    conn = sqlite3.connect(db_path)
    try:
        cols_info = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
        col_types = {row[1]: (row[2] or "").upper() for row in cols_info}
        allowed = set(col_types)

        rows: list[dict[str, object]] = []
        for raw in reader:
            item: dict[str, object] = {}
            for key, value in raw.items():
                if key is None:
                    continue
                dest = HEADER_MAP.get(key.strip())
                if dest is None or dest not in allowed:
                    continue
                item[dest] = _coerce(value, col_types[dest])
            if item:
                rows.append(item)

        used_cols = sorted({col for row in rows for col in row})
        now = datetime.now(timezone.utc).isoformat()
        checksum = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()

        with conn:
            conn.execute(f"DELETE FROM {tabela}")
            if used_cols:
                placeholders = ", ".join("?" * len(used_cols))
                col_sql = ", ".join(used_cols)
                sql = f"INSERT INTO {tabela} ({col_sql}) VALUES ({placeholders})"
                conn.executemany(
                    sql, [[row.get(col) for col in used_cols] for row in rows]
                )
            conn.execute(
                """
                INSERT INTO edicoes(
                    ano, edicao_pnp, sincronizado_em, n_linhas, checksum_csv
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ano) DO UPDATE SET
                    edicao_pnp = excluded.edicao_pnp,
                    sincronizado_em = excluded.sincronizado_em,
                    n_linhas = excluded.n_linhas,
                    checksum_csv = excluded.checksum_csv
                """,
                (ano_edicao, edicao_pnp, now, len(rows), checksum),
            )
        return len(rows)
    finally:
        conn.close()


def _coerce(value: str | None, col_type: str) -> object:
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    if col_type in _NUMERIC_TYPES:
        normalized = text.replace(",", ".")
        try:
            number = float(normalized)
        except ValueError:
            return None
        if col_type in {"INTEGER", "INT"}:
            return int(number)
        return number
    return text
