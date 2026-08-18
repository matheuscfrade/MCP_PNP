import sqlite3
from pathlib import Path

import pytest

from mcp_pnp.db.schema import apply_schema


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "pnp.sqlite"
    conn = sqlite3.connect(path)
    apply_schema(conn)
    conn.execute(
        "INSERT INTO edicoes(ano, edicao_pnp, sincronizado_em, n_linhas, checksum_csv) "
        "VALUES (2025, '2026', '2026-08-18T00:00:00', 2, 'abc')"
    )
    conn.execute(
        """INSERT INTO oferta(
            ano, regiao, uf, estado, organizacao_academica,
            instituicao_sigla, instituicao_nome, unidade,
            n_cursos, n_matriculas, mateq, n_vagas, n_inscritos,
            n_ingressantes, n_concluintes, n_estruturas, n_unidades, n_ciclos
        ) VALUES
        (2025, 'Sudeste', 'MG', 'Minas Gerais', 'Instituto Federal',
         'IFMG', 'Instituto Federal de Minas Gerais', 'Campus BH',
         2, 100, 80.5, 50, 200, 40, 30, 1, 1, 2),
        (2025, 'Centro-Oeste', 'DF', 'Distrito Federal', 'Instituto Federal',
         'IFB', 'Instituto Federal de Brasília', 'Campus Brasília',
         1, 50, 40.0, 25, 80, 20, 10, 1, 1, 1)
        """
    )
    conn.commit()
    conn.close()
    return path
