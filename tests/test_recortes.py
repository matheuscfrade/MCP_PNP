"""Recortes nativos (modalidade, tipo_curso) sem cruzar tabelas."""

from __future__ import annotations

pytest_plugins = ["test_formulas"]


from pathlib import Path

import pytest

from mcp_pnp.analysis import agregar, evolucao, ranking
from mcp_pnp.db.queries import consultar, listar_valores_campo
from mcp_pnp.db.schema import apply_schema, fields_of
from mcp_pnp.errors import PnpError
from mcp_pnp.ingest.loader import load_csv
from mcp_pnp.registry import get
from mcp_pnp.tools import pnp_listar_edicoes


def test_evasao_schema_tem_modalidade():
    assert "modalidade" in fields_of("evasao")
    assert "tipo_oferta" in fields_of("evasao")
    assert "turno" in fields_of("evasao")


def test_loader_grava_modalidade(tmp_path: Path):
    import sqlite3

    db = tmp_path / "pnp.sqlite"
    conn = sqlite3.connect(db)
    apply_schema(conn)
    conn.close()
    raw = (Path(__file__).parent / "fixtures" / "evasao.csv").read_text(encoding="utf-8")
    load_csv(db, "evasao", raw, ano_edicao=2025, edicao_pnp="2026")
    presencial = consultar(
        db,
        get("ENEVA"),
        {"instituicao": "IFMG", "ano": 2025, "modalidade": "Educação Presencial"},
    )
    assert presencial["valor_oficial"] == pytest.approx(10.0)
    assert presencial["numerador"] == 10
    assert presencial["denominador"] == 100
    ead = consultar(
        db,
        get("ENEVA"),
        {"instituicao": "IFMG", "ano": 2025, "modalidade": "Educação a Distância"},
    )
    assert ead["valor_oficial"] == pytest.approx(40.0)


def test_eneva_filtro_modalidade(db_formulas):
    body = consultar(
        db_formulas,
        get("ENEVA"),
        {
            "instituicao": "IFMG",
            "ano": 2025,
            "modalidade": "Educação Presencial",
        },
    )
    # 10 / 150 (Campus A + C)
    assert body["valor_oficial"] == pytest.approx(10 / 150 * 100)


def test_excluir_fic_nao_e_recorte_do_painel(db_formulas):
    with pytest.raises(PnpError) as ei:
        consultar(
            db_formulas,
            get("ENEVA"),
            {"instituicao": "IFMG", "ano": 2025, "excluir_fic": True},
        )
    assert ei.value.codigo == "filtro_indisponivel"


def test_enme_nao_expoe_turno(db_path):
    from mcp_pnp.dimensions import filtros_nativos

    assert "turno" not in filtros_nativos(get("ENM"))
    assert "modalidade" in filtros_nativos(get("ENM"))
    assert "modalidade" not in filtros_nativos(get("ENEC"))
    assert "modalidade" not in filtros_nativos(get("ALRMP"))
    with pytest.raises(PnpError) as ei:
        consultar(db_path, get("ENM"), {"ano": 2025, "turno": "Noturno"})
    assert ei.value.codigo == "filtro_indisponivel"


def test_enec_nao_inventa_modalidade(db_formulas):
    with pytest.raises(PnpError) as ei:
        consultar(
            db_formulas,
            get("ENEC"),
            {"instituicao": "IFMG", "ano": 2025, "modalidade": "Educação Presencial"},
        )
    assert ei.value.codigo == "filtro_indisponivel"
    assert "ENEVA" in ei.value.message


def test_rap_nao_agrega_por_modalidade(db_formulas):
    with pytest.raises(PnpError) as ei:
        agregar(db_formulas, "ALRMP", "modalidade", {"ano": 2025})
    assert ei.value.codigo == "agrupamento_invalido"


def test_agregar_por_tipo_curso(db_formulas):
    body = agregar(
        db_formulas,
        "ENEVA",
        "tipo_curso",
        {"instituicao": "IFMG", "ano": 2025},
    )
    por_tipo = {r["tipo_curso"]: r["valor"] for r in body["registros"]}
    assert por_tipo["Técnico"] == pytest.approx(10 / 150 * 100)
    assert por_tipo["Qualificação Profissional (FIC)"] == pytest.approx(200.0)


def test_ranking_por_modalidade(db_formulas):
    body = ranking(db_formulas, "ENEVA", "modalidade", "desc", 2025, 10)
    assert body["registros"][0]["modalidade"]


def test_evolucao_default_intervalo(db_formulas):
    body = evolucao(db_formulas, "ENEVA", {"instituicao": "IFMG"})
    anos = [r["ano"] for r in body["registros"]]
    assert anos == [2024, 2025]


def test_taxa_evasao_exibida_em_percentual(db_formulas):
    body = consultar(db_formulas, get("ENEVA"), {"instituicao": "IFMG", "ano": 2025})
    valores = [r["valor"] for r in body["registros"] if r["valor"] is not None]
    assert 10.0 in valores


def test_listar_valores_modalidade(db_formulas):
    body = listar_valores_campo(db_formulas, "modalidade", {"ano": 2025})
    encontrados = {r["valor"] for r in body["registros"]}
    assert "Educação Presencial" in encontrados


def test_cobertura_edicoes(db_formulas, monkeypatch):
    monkeypatch.setenv("PNP_DB_PATH", str(db_formulas))
    body = pnp_listar_edicoes()
    rec_2025 = next(r for r in body["registros"] if r["ano"] == 2025)
    assert rec_2025["cobertura"]["evasao"] >= 1
    assert "eficiencia" in rec_2025["cobertura"]
