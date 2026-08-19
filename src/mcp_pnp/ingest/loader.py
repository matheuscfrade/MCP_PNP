from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mcp_pnp.db.schema import TABLES, apply_schema
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
    "nomeIdCurso": "nome_curso",
    "tipoCurso": "tipo_curso",
    "tipoOferta": "tipo_oferta",
    "ModalidadeEnsino": "modalidade",
    "turnoCurso": "turno",
    "tipoEixoTecnologico": "eixo",
    "SubeixoTecnologico": "subeixo",
    "nomePrograma": "programa",
    "nomeCurso": "nome_curso",
    "Número de cursos": "n_cursos",
    "Número de Matrículas": "n_matriculas",
    "Matrícula Equivalente | Geral": "mateq",
    "Matrícula Equivalente | Técnicos": "mateq_tecnicos",
    "Matrícula Equivalente | Formação de Professores": "mateq_formacao",
    "Matrícula Equivalente | Proeja": "mateq_proeja",
    "Número de vagas": "n_vagas",
    "Número de inscritos": "n_inscritos",
    "Número de ingressantes": "n_ingressantes",
    "Número de concluintes": "n_concluintes",
    "categoriaSituacao": "categoria_situacao",
    "nomeSituacao": "nome_situacao",
    "FluxoRetido": "fluxo_retido",
    "CorRaca": "cor_raca",
    "RendaFamiliar": "renda_familiar",
    "FaixaEtaria": "faixa_etaria",
    "Sexo": "sexo",
    "tipoReservaVaga": "tipo_reserva",
    "Vagas Regulares": "vagas_regulares",
    "Vagas Regulares %": "vagas_regulares_pct",
    "Oferta de Vagas | Curso Noturno": "vagas_noturnas",
    "Oferta de Vagas | Curso Noturno %": "alvcn",
    "Oferta de Vagas | Graduação": "vagas_graduacao",
    "Relação Inscrito Vaga": "relacao_inscrito_vaga",
    "Matrículas | Número de Evadidos": "n_evadidos",
    "Matrículas | Taxa de Evasão %": "taxa_evasao",
    "Eficiência Acadêmica | Concluídos": "n_concluidos",
    "Eficiência Acadêmica | Concluídos %": "taxa_conclusao_ciclo",
    "Eficiência Acadêmica | Índice de Eficiência Acadêmica %": "iea",
    "Eficiência Acadêmica | Número de Evadidos": "n_evadidos",
    "Eficiência Acadêmica | Retidos": "n_retidos",
    "Eficiência Acadêmica | Retidos %": "taxa_retencao_ciclo",
    "Eficiência Acadêmica | Taxa de Evasão %": "taxa_evasao_ciclo",
    "RAP | RAP": "rap",
    "RAP | Matrículas RAP": "mateq_rap",
    "RAP | Professor Equivalente": "profeq",
    "Índice de Verticalização | Vagas - CG": "vagas_cg",
    "Índice de Verticalização | Vagas - CT": "vagas_ct",
    "Índice de Verticalização | Vagas - PG": "vagas_pg",
    "Índice de Verticalização | Vagas - QP": "vagas_qp",
    "Índice de Verticalização | Eixo Tecnológico": "iv",
    "Taxa de Ocupação | Matriculas Ciclos Vigentes": "matriculas_ciclos_vigentes",
    "Taxa de Ocupação | Vagas Ciclos Vigentes": "vagas_ciclos_vigentes",
    "Taxa de Ocupação | Taxa de Ocupação": "taxa_ocupacao",
    "Servidores | Docente Efetivo": "n_docentes_efetivos",
    "Servidores | Número de Docentes": "n_docentes",
    "Servidores | Número de Servidores": "n_servidores",
    "Servidores | ITCD": "itcd",
    "Servidores | Número de TAE": "n_tae",
    "Titulação": "titulacao",
    "Jornada_de_Trabalho": "jornada",
    "CarreiraSigla": "carreira_sigla",
    "Número de servidores (Siafi)": "n_servidores",
    "Relação do Órgão": "relacao_orgao",
    "Resultado Primário (Cidadã)": "resultado_primario",
    "Dotação atualizada": "dotacao_atualizada",
    "Despesa empenhada": "despesa_empenhada",
    "Despesa liquidada": "despesa_liquidada",
    "Despesa paga": "despesa_paga",
    "Despesa empenhada a liquidar": "empenhado_a_liquidar",
    "Crédito Disponível": "credito_disponivel",
    "Gastos Correntes por matrícula equivalente": "gasto_por_mateq",
    "Gastos Correntes | Gastos Totais": "gastos_totais",
    "Gastos Correntes | Gastos Correntes": "gastos_correntes",
    "Gastos Correntes | Inativos e Pensionistas": "gastos_inativos",
    "Gastos Correntes | Investimentos e Inversões Financeiras": "gastos_investimento",
    "Gastos Correntes | Precatórios": "gastos_precatorios",
    "Gastos Correntes | Outros Custeios": "gastos_custeio",
    "Gastos Correntes | Pessoal": "gastos_pessoal",
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
        apply_schema(conn)
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
                if dest == "mateq" and dest not in allowed and "mateq_geral" in allowed:
                    dest = "mateq_geral"
                if dest is None or dest not in allowed:
                    continue
                item[dest] = _coerce(value, col_types[dest])
            _enriquecer(item, tabela)
            if item:
                rows.append(item)

        used_cols = sorted({col for row in rows for col in row if col in allowed})
        now = datetime.now(timezone.utc).isoformat()
        checksum = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
        anos = sorted(
            {
                int(row["ano"])
                for row in rows
                if row.get("ano") is not None
            }
        )
        if not anos:
            anos = [ano_edicao]

        with conn:
            conn.execute(f"DELETE FROM {tabela}")
            if used_cols:
                placeholders = ", ".join("?" * len(used_cols))
                col_sql = ", ".join(used_cols)
                sql = f"INSERT INTO {tabela} ({col_sql}) VALUES ({placeholders})"
                conn.executemany(
                    sql, [[row.get(col) for col in used_cols] for row in rows]
                )
            for ano in anos:
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
                    (ano, str(ano + 1), now, len(rows), checksum),
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
        try:
            number = _parse_number(text)
        except ValueError:
            return None
        if col_type in {"INTEGER", "INT"}:
            return int(number)
        return number
    return text


def _parse_number(text: str) -> float:
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def _pct(parte: object, todo: object) -> float | None:
    if parte is None or todo in (None, 0, 0.0):
        return None
    return 100.0 * float(parte) / float(todo)


def _enriquecer(item: dict[str, object], tabela: str) -> None:
    if tabela == "percentuais_legais":
        if item.get("mateq") is not None:
            item["mateq_geral"] = item["mateq"]
        geral = item.get("mateq_geral")
        item["almtec"] = _pct(item.get("mateq_tecnicos"), geral)
        item["almprof"] = _pct(item.get("mateq_formacao"), geral)
        item["almeja"] = _pct(item.get("mateq_proeja"), geral)
    if tabela == "situacao_matricula" and not item.get("motivo"):
        item["motivo"] = item.get("nome_situacao")
