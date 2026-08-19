"""Fórmulas oficiais: soma(numerador)/soma(denominador), nunca média de taxas."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mcp_pnp.analysis import comparar, estatisticas, evolucao, ranking
from mcp_pnp.db.queries import consultar
from mcp_pnp.db.schema import apply_schema
from mcp_pnp.formulas import FORMULAS, formula_de
from mcp_pnp.registry import INDICADORES_MVP, get


@pytest.fixture
def db_formulas(tmp_path: Path) -> Path:
    path = tmp_path / "formulas.sqlite"
    conn = sqlite3.connect(path)
    apply_schema(conn)
    conn.executemany(
        "INSERT INTO edicoes(ano, edicao_pnp, sincronizado_em, n_linhas, checksum_csv) "
        "VALUES (?, ?, '2026-08-18T00:00:00', 1, 'x')",
        [(2024, "2025"), (2025, "2026")],
    )
    # ENEVA: curso pequeno com taxa alta + curso grande com taxa baixa + linha sem taxa.
    # Oficial 2025 IFMG-like: (10+20)/ (100+10+50) = 18,75%. Média das taxas ≠ isso.
    conn.executemany(
        """INSERT INTO evasao(
            ano, instituicao_sigla, unidade, n_evadidos, n_matriculas, taxa_evasao,
            tipo_curso, modalidade
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "Campus A", 10, 100, 0.10, "Técnico", "Educação Presencial"),
            (2025, "IFMG", "Campus B", 20, 10, 2.00, "Qualificação Profissional (FIC)", "Educação a Distância"),
            (2025, "IFMG", "Campus C", None, 50, None, "Técnico", "Educação Presencial"),
            (2025, "IFB", "Campus X", 5, 200, 0.025, "Técnico", "Educação Presencial"),
            (2024, "IFMG", "Campus A", 8, 80, 0.10, "Técnico", "Educação Presencial"),
        ],
    )
    # ENIEA/ENCC/ENEC/ENREC — dois campi IFMG.
    # A: C=20 E=8 R=12 → IEA = 20/28*100; ciclo den=40
    # B: C=10 E=10 R=0  → IEA = 50
    # Instituição: C=30 E=18 R=12 → IEA = 30/48*100 = 62,5
    conn.executemany(
        """INSERT INTO eficiencia(
            ano, instituicao_sigla, unidade,
            n_concluidos, n_evadidos, n_retidos, iea,
            taxa_conclusao_ciclo, taxa_evasao_ciclo, taxa_retencao_ciclo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "A", 20, 8, 12, 71.4286, 50.0, 20.0, 30.0),
            (2025, "IFMG", "B", 10, 10, 0, 50.0, 50.0, 50.0, 0.0),
        ],
    )
    # ALRMP: 400/20 e 10/10 → oficial 410/30; média das RAPs = 10,5
    conn.executemany(
        """INSERT INTO rap(
            ano, instituicao_sigla, unidade, rap, mateq_rap, profeq
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "A", 20.0, 400, 20),
            (2025, "IFMG", "B", 1.0, 10, 10),
        ],
    )
    # ALMTEC: 80/100 e 10/400 → oficial 90/500 = 18%; média das % = 41,25
    conn.executemany(
        """INSERT INTO percentuais_legais(
            ano, instituicao_sigla, unidade,
            mateq_tecnicos, mateq_formacao, mateq_proeja, mateq_geral,
            almtec, almprof, almeja
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "A", 80, 20, 5, 100, 80.0, 20.0, 5.0),
            (2025, "IFMG", "B", 10, 40, 0, 400, 2.5, 10.0, 0.0),
        ],
    )
    # GACM: 1000/10 → mateq 100; 100/50 → mateq 2; oficial 1100/102
    conn.executemany(
        """INSERT INTO gastos(
            ano, instituicao_sigla, gastos_correntes, gasto_por_mateq, gastos_totais
        ) VALUES (?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", 1000, 10, 1200),
            (2025, "IFB", 100, 50, 110),
        ],
    )
    # PETCD: 5,0×10 e 3,0×90 → oficial 3,2; média 4,0
    conn.executemany(
        """INSERT INTO docentes(
            ano, instituicao_sigla, itcd, n_docentes_efetivos, n_docentes, n_servidores
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", 5.0, 10, 12, 20),
            (2025, "IFB", 3.0, 90, 100, 150),
        ],
    )
    # ENIV: Guia agrega instituição pela média dos IVs inferiores.
    conn.executemany(
        """INSERT INTO verticalizacao(
            ano, instituicao_sigla, unidade, iv, vagas_cg, vagas_ct, vagas_pg, vagas_qp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "A", 20.0, 100, 191, 251, 9697),
            (2025, "IFMG", "B", 40.0, 394, 287, 82, 4919),
        ],
    )
    # ALVCN / ALVGN: 100/200 e 10/400 → 110/600
    conn.executemany(
        """INSERT INTO vagas_noturnas(
            ano, instituicao_sigla, unidade,
            vagas_noturnas, vagas_graduacao, alvcn
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", "A", 100, 200, 50.0),
            (2025, "IFMG", "B", 10, 400, 2.5),
        ],
    )
    conn.executemany(
        """INSERT INTO ocupacao(
            ano, instituicao_sigla, matriculas_ciclos_vigentes, vagas_ciclos_vigentes, taxa_ocupacao
        ) VALUES (?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", 90, 100, 90.0),
            (2025, "IFB", 10, 50, 20.0),
        ],
    )
    conn.executemany(
        """INSERT INTO inscritos_vagas(
            ano, instituicao_sigla, n_inscritos, n_vagas, relacao_inscrito_vaga
        ) VALUES (?, ?, ?, ?, ?)""",
        [
            (2025, "IFMG", 400, 100, 4.0),
            (2025, "IFMG", 10, 50, 0.2),
        ],
    )
    conn.execute(
        """INSERT INTO situacao_matricula(
            ano, instituicao_sigla, categoria_situacao, fluxo_retido, n_matriculas
        ) VALUES
        (2025, 'IFMG', 'Evadidos', 'Em fluxo', 7),
        (2025, 'IFMG', 'Em curso', 'Em fluxo', 30),
        (2025, 'IFMG', 'Em curso', 'Retido', 4)
        """
    )
    conn.commit()
    conn.close()
    return path


def test_todo_indicador_mvp_tem_formula():
    for ind in INDICADORES_MVP:
        formula_de(ind.codigo)


def test_eneva_e_razao_das_somas_nao_media_de_taxas(db_formulas):
    body = consultar(db_formulas, get("ENEVA"), {"instituicao": "IFMG", "ano": 2025})
    # 30 / 160 * 100. Linha sem taxa entra no denominador.
    assert body["valor_oficial"] == pytest.approx(18.75)
    assert body["numerador"] == 30
    assert body["denominador"] == 160
    taxas = [r["valor"] for r in body["registros"] if r["valor"] is not None]
    media = sum(taxas) / len(taxas)
    assert body["valor_oficial"] != pytest.approx(media)
    assert "SUM(n_evadidos)" in body["formula"]


def test_eneva_comparar_usa_valor_oficial(db_formulas):
    body = comparar(
        db_formulas,
        "ENEVA",
        {"instituicao": "IFMG", "ano": 2025},
        {"instituicao": "IFB", "ano": 2025},
    )
    rec = body["registros"][0]
    assert rec["valores"]["esquerda"] == pytest.approx(18.75)
    assert rec["valores"]["direita"] == pytest.approx(2.5)


def test_eneva_evolucao_usa_valor_oficial(db_formulas):
    body = evolucao(db_formulas, "ENEVA", {"instituicao": "IFMG"}, 2024, 2025)
    por_ano = {r["ano"]: r["valor"] for r in body["registros"]}
    assert por_ano[2024] == pytest.approx(10.0)
    assert por_ano[2025] == pytest.approx(18.75)


def test_eneva_ranking_usa_razao_oficial(db_formulas):
    body = ranking(db_formulas, "ENEVA", "instituicao", "desc", 2025, 10)
    valores = {r["instituicao"]: r["valor"] for r in body["registros"]}
    assert valores["IFMG"] == pytest.approx(18.75)
    assert valores["IFB"] == pytest.approx(2.5)
    assert body["registros"][0]["instituicao"] == "IFMG"


def test_eneva_estatistica_media_e_oficial(db_formulas):
    body = estatisticas(
        db_formulas, "ENEVA", {"instituicao": "IFMG", "ano": 2025}, "media"
    )
    rec = body["registros"][0]
    assert rec["estatistica"] == "oficial"
    assert rec["valor"] == pytest.approx(18.75)


def test_eniea_e_concluidos_sobre_concluidos_mais_evadidos(db_formulas):
    body = consultar(db_formulas, get("ENIEA"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] == pytest.approx(62.5)
    media_iea = (71.4286 + 50.0) / 2
    assert body["valor_oficial"] != pytest.approx(media_iea)


def test_encc_enec_enrec_usam_ciclo_completo(db_formulas):
    enc = consultar(db_formulas, get("ENCC"), {"instituicao": "IFMG", "ano": 2025})
    ene = consultar(db_formulas, get("ENEC"), {"instituicao": "IFMG", "ano": 2025})
    enr = consultar(db_formulas, get("ENREC"), {"instituicao": "IFMG", "ano": 2025})
    # C+E+R = 30+18+12 = 60
    assert enc["valor_oficial"] == pytest.approx(50.0)
    assert ene["valor_oficial"] == pytest.approx(30.0)
    assert enr["valor_oficial"] == pytest.approx(20.0)


def test_alrmp_pondera_por_profeq(db_formulas):
    body = consultar(db_formulas, get("ALRMP"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] == pytest.approx(410 / 30)
    assert body["valor_oficial"] != pytest.approx(10.5)


def test_almtec_pondera_por_mateq_geral(db_formulas):
    body = consultar(db_formulas, get("ALMTEC"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] == pytest.approx(18.0)
    assert body["valor_oficial"] != pytest.approx(41.25)


def test_almprof_e_almeja_sao_razoes(db_formulas):
    prof = consultar(db_formulas, get("ALMPROF"), {"instituicao": "IFMG", "ano": 2025})
    eja = consultar(db_formulas, get("ALMEJA"), {"instituicao": "IFMG", "ano": 2025})
    assert prof["valor_oficial"] == pytest.approx(12.0)  # 60/500
    assert eja["valor_oficial"] == pytest.approx(1.0)  # 5/500


def test_gacm_e_gasto_sobre_mateq_implicito(db_formulas):
    rede = consultar(db_formulas, get("GACM"), {"ano": 2025})
    assert rede["valor_oficial"] == pytest.approx(1100 / 102)
    ifmg = consultar(db_formulas, get("GACM"), {"instituicao": "IFMG", "ano": 2025})
    assert ifmg["valor_oficial"] == pytest.approx(10.0)


def test_petcd_pondera_por_docentes_efetivos(db_formulas):
    body = consultar(db_formulas, get("PETCD"), {"ano": 2025})
    assert body["valor_oficial"] == pytest.approx(3.2)
    assert body["valor_oficial"] != pytest.approx(4.0)


def test_eniv_instituicao_e_media_dos_ivs(db_formulas):
    body = consultar(db_formulas, get("ENIV"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] == pytest.approx(30.0)
    # Herfindahl das vagas somadas não é a agregação oficial do Guia.
    assert body["valor_oficial"] != pytest.approx(71.45, abs=1)


def test_alvgn_e_vagas_noturnas_sobre_graduacao(db_formulas):
    alvgn = consultar(db_formulas, get("ALVGN"), {"instituicao": "IFMG", "ano": 2025})
    assert alvgn["valor_oficial"] == pytest.approx(110 / 600 * 100)


def test_alvcn_e_alrape_nao_inventam_recorte(db_formulas):
    alvcn = consultar(db_formulas, get("ALVCN"), {"instituicao": "IFMG", "ano": 2025})
    alrape = consultar(db_formulas, get("ALRAPE"), {"instituicao": "IFMG", "ano": 2025})
    assert alvcn["valor_oficial"] is None
    assert alrape["valor_oficial"] is None
    assert FORMULAS["ALVCN"].tipo == "indisponivel"
    assert FORMULAS["ALRAPE"].tipo == "indisponivel"


def test_enoc_e_enriv_sao_razoes(db_formulas):
    enoc = consultar(db_formulas, get("ENOC"), {"ano": 2025})
    enriv = consultar(db_formulas, get("ENRIV"), {"instituicao": "IFMG", "ano": 2025})
    assert enoc["valor_oficial"] == pytest.approx(100 / 150 * 100)
    assert enriv["valor_oficial"] == pytest.approx(410 / 150)


def test_enev_filtra_categoria_evadidos(db_formulas):
    body = consultar(db_formulas, get("ENEV"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] == 7


def test_em_curso_e_retidos_usam_filtro_implicito(db_formulas):
    curso = consultar(db_formulas, get("EM_CURSO"), {"instituicao": "IFMG", "ano": 2025})
    ret = consultar(db_formulas, get("RETIDOS"), {"instituicao": "IFMG", "ano": 2025})
    assert curso["valor_oficial"] == 34
    assert ret["valor_oficial"] == 4


def test_participacao_usa_oficial_nao_media(db_formulas):
    body = estatisticas(
        db_formulas, "ENEVA", {"instituicao": "IFMG", "ano": 2025}, "participacao"
    )
    # IFMG 30/160; rede 35/360 → 30/160 sobre 35/360
    rec = body["registros"][0]["valor"]
    ifmg = 30 / 160 * 100
    rede = 35 / 360 * 100
    assert rec == pytest.approx(ifmg / rede * 100)


def test_algn_nao_soma_percentuais(db_formulas):
    body = consultar(db_formulas, get("ALGN"), {"instituicao": "IFMG", "ano": 2025})
    assert body["valor_oficial"] is None
    assert FORMULAS["ALGN"].tipo == "indisponivel"
