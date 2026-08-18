from __future__ import annotations

import sqlite3

DIM = """
    ano INTEGER,
    regiao TEXT,
    uf TEXT,
    estado TEXT,
    organizacao_academica TEXT,
    instituicao_sigla TEXT,
    instituicao_nome TEXT,
    unidade TEXT,
    municipio TEXT
"""

TABLES = {
    "edicoes": """
        CREATE TABLE IF NOT EXISTS edicoes (
            ano INTEGER PRIMARY KEY,
            edicao_pnp TEXT NOT NULL,
            sincronizado_em TEXT NOT NULL,
            n_linhas INTEGER NOT NULL,
            checksum_csv TEXT
        )
    """,
    "sync_log": """
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iniciado_em TEXT NOT NULL,
            status TEXT NOT NULL,
            detalhe TEXT
        )
    """,
    "oferta": f"CREATE TABLE IF NOT EXISTS oferta ({DIM}, n_cursos REAL, n_matriculas REAL, mateq REAL, n_vagas REAL, n_inscritos REAL, n_ingressantes REAL, n_concluintes REAL, n_estruturas REAL, n_unidades REAL, n_ciclos REAL, tipo_curso TEXT, tipo_oferta TEXT, modalidade TEXT, turno TEXT, eixo TEXT, subeixo TEXT, nome_curso TEXT, fonte_financiamento TEXT, programa TEXT)",
    "situacao_matricula": f"CREATE TABLE IF NOT EXISTS situacao_matricula ({DIM}, categoria_situacao TEXT, nome_situacao TEXT, fluxo_retido TEXT, motivo TEXT, n_matriculas REAL)",
    "evasao": f"CREATE TABLE IF NOT EXISTS evasao ({DIM}, taxa_evasao REAL, n_evadidos REAL, n_matriculas REAL, nome_curso TEXT, tipo_curso TEXT, eixo TEXT)",
    "eficiencia": f"CREATE TABLE IF NOT EXISTS eficiencia ({DIM}, iea REAL, taxa_conclusao_ciclo REAL, taxa_evasao_ciclo REAL, taxa_retencao_ciclo REAL, n_concluidos REAL, n_evadidos REAL, n_retidos REAL)",
    "rap": f"CREATE TABLE IF NOT EXISTS rap ({DIM}, rap REAL, rap_presencial REAL, mateq_rap REAL, profeq REAL)",
    "verticalizacao": f"CREATE TABLE IF NOT EXISTS verticalizacao ({DIM}, iv REAL, vagas_cg REAL, vagas_ct REAL, vagas_pg REAL, vagas_qp REAL)",
    "ocupacao": f"CREATE TABLE IF NOT EXISTS ocupacao ({DIM}, taxa_ocupacao REAL, matriculas_ciclos_vigentes REAL, vagas_ciclos_vigentes REAL)",
    "percentuais_legais": f"CREATE TABLE IF NOT EXISTS percentuais_legais ({DIM}, almtec REAL, almprof REAL, almeja REAL, alvtec REAL, alvprof REAL, alveja REAL, mateq_tecnicos REAL, mateq_formacao REAL, mateq_proeja REAL, mateq_geral REAL)",
    "vagas_noturnas": f"CREATE TABLE IF NOT EXISTS vagas_noturnas ({DIM}, alvcn REAL, alvgn REAL, algn REAL, almgn REAL, vagas_noturnas REAL, vagas_graduacao REAL)",
    "inscritos_vagas": f"CREATE TABLE IF NOT EXISTS inscritos_vagas ({DIM}, n_inscritos REAL, n_vagas REAL, relacao_inscrito_vaga REAL)",
    "reserva_vagas": f"CREATE TABLE IF NOT EXISTS reserva_vagas ({DIM}, tipo_reserva TEXT, vagas_regulares REAL, vagas_regulares_pct REAL)",
    "gastos": f"CREATE TABLE IF NOT EXISTS gastos ({DIM}, gasto_por_mateq REAL, gastos_totais REAL, gastos_correntes REAL, gastos_pessoal REAL, gastos_custeio REAL, gastos_investimento REAL, gastos_inativos REAL, gastos_precatorios REAL)",
    "docentes": f"CREATE TABLE IF NOT EXISTS docentes ({DIM}, n_docentes REAL, n_docentes_efetivos REAL, n_servidores REAL, itcd REAL, titulacao TEXT)",
    "tae": f"CREATE TABLE IF NOT EXISTS tae ({DIM}, n_tae REAL, titulacao TEXT)",
    "orcamento": f"CREATE TABLE IF NOT EXISTS orcamento ({DIM}, dotacao_atualizada REAL, despesa_empenhada REAL, despesa_liquidada REAL, despesa_paga REAL, empenhado_a_liquidar REAL, credito_disponivel REAL, resultado_primario TEXT, relacao_orgao TEXT)",
    "perfil_discente": f"CREATE TABLE IF NOT EXISTS perfil_discente ({DIM}, cor_raca TEXT, renda_familiar TEXT, sexo TEXT, faixa_etaria TEXT, n_matriculas REAL, n_concluintes REAL, n_ingressantes REAL, n_vagas REAL)",
}


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    for ddl in TABLES.values():
        conn.execute(ddl)
    conn.commit()
