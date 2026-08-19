"""Fórmulas oficiais de agregação da PNP (Guia de Indicadores).

Taxas e índices NÃO são média das linhas. Sempre:
  soma(numerador) / soma(denominador)  [× 100 se percentual]
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Formula:
    tipo: str  # soma | razao | count_distinct | ponderado | gacm
    numerador: str | None = None
    denominador: tuple[str, ...] = ()
    escala: float = 1.0
    filtros: tuple[tuple[str, str], ...] = ()
    count_col: str | None = None
    peso: str | None = None
    expressao: str = ""


def _soma(col: str, **kw: object) -> Formula:
    return Formula(tipo="soma", numerador=col, expressao=f"SUM({col})", **kw)


def _razao(num: str, *den: str, escala: float = 1.0, **kw: object) -> Formula:
    dens = " + ".join(f"SUM({c})" for c in den)
    exp = f"SUM({num}) / ({dens})"
    if escala != 1.0:
        exp = f"{escala} * {exp}"
    return Formula(
        tipo="razao",
        numerador=num,
        denominador=den,
        escala=escala,
        expressao=exp,
        **kw,
    )


# Filtros implícitos das tools de situação (Guia: categorias oficiais).
_EVADIDOS = (("categoria_situacao", "Evadidos"),)
_EM_CURSO = (("categoria_situacao", "Em curso"),)
_RETIDOS = (("fluxo_retido", "Retido"),)

FORMULAS: dict[str, Formula] = {
    "ENEMA": Formula(tipo="count_distinct", count_col="unidade", expressao="COUNT(DISTINCT unidade)"),
    "ENUND": Formula(tipo="count_distinct", count_col="unidade", expressao="COUNT(DISTINCT unidade)"),
    "ENC": _soma("n_cursos"),
    "ENM": _soma("n_matriculas"),
    "ENME": _soma("mateq"),
    "ENV": _soma("n_vagas"),
    "ENIC": _soma("n_inscritos"),
    "ENING": _soma("n_ingressantes"),
    "ENCT": _soma("n_concluintes"),
    "CICLOS": _soma("n_ciclos"),
    "EM_CURSO": _soma("n_matriculas", filtros=_EM_CURSO),
    "ENEV": _soma("n_matriculas", filtros=_EVADIDOS),
    "RETIDOS": _soma("n_matriculas", filtros=_RETIDOS),
    # ENEVA oficial = Σ evadidos / Σ matrículas (todas as linhas, inclusive sem taxa).
    "ENEVA": _razao("n_evadidos", "n_matriculas", escala=100.0),
    "ENEC": _razao("n_evadidos", "n_concluidos", "n_evadidos", "n_retidos", escala=100.0),
    "ENCC": _razao("n_concluidos", "n_concluidos", "n_evadidos", "n_retidos", escala=100.0),
    "ENREC": _razao("n_retidos", "n_concluidos", "n_evadidos", "n_retidos", escala=100.0),
    # IEA = concluídos / (concluídos + evadidos), sem retidos.
    "ENIEA": _razao("n_concluidos", "n_concluidos", "n_evadidos", escala=100.0),
    "ALRMP": _razao("mateq_rap", "profeq"),
    "ALRAPE": Formula(
        tipo="indisponivel",
        expressao=(
            "ALRAPE exige Mateq presencial / professor-equivalente; "
            "o CSV de RAP do Extrator não separa o recorte presencial"
        ),
    ),
    # Guia: em unidade/instituição a PNP usa a média dos IVs do nível inferior
    # (eixo). O Extrator já traz o IV oficial da unidade — não recomputar
    # Herfindahl nem razão de vagas somadas.
    "ENIV": Formula(
        tipo="media",
        numerador="iv",
        expressao="AVG(iv) — média dos índices oficiais do nível inferior (Guia ENIV)",
    ),
    "ENOC": _razao("matriculas_ciclos_vigentes", "vagas_ciclos_vigentes", escala=100.0),
    "ALMTEC": _razao("mateq_tecnicos", "mateq_geral", escala=100.0),
    "ALMPROF": _razao("mateq_formacao", "mateq_geral", escala=100.0),
    "ALMEJA": _razao("mateq_proeja", "mateq_geral", escala=100.0),
    # PercentuaisLegais.csv do Extrator não traz vagas — só Mateq.
    "ALVTEC": Formula(
        tipo="indisponivel",
        expressao="ALVTEC exige vagas EPTNM / vagas totais; o CSV do Extrator não traz o numerador",
    ),
    "ALVPROF": Formula(
        tipo="indisponivel",
        expressao="ALVPROF exige vagas de formação / vagas totais; o CSV do Extrator não traz o numerador",
    ),
    "ALVEJA": Formula(
        tipo="indisponivel",
        expressao="ALVEJA exige vagas EJA/EPT / vagas totais; o CSV do Extrator não traz o numerador",
    ),
    "ALGN": Formula(
        tipo="indisponivel",
        expressao="ALGN exige nº de cursos de graduação noturna / cursos de graduação presencial; o CSV não traz esses totais",
    ),
    "ALMGN": Formula(
        tipo="indisponivel",
        expressao="ALMGN exige Mateq de graduação noturna / Mateq de graduação presencial; o CSV não traz esses totais",
    ),
    # OfertaVagasNoturnas e o cartão PBI "Vagas Noturnas" são ALVGN
    # (noturnas de graduação / graduação presencial). ALVCN é outro recorte.
    "ALVGN": _razao("vagas_noturnas", "vagas_graduacao", escala=100.0),
    "ALVCN": Formula(
        tipo="indisponivel",
        expressao=(
            "ALVCN exige vagas noturnas presenciais / vagas presenciais totais; "
            "o CSV do Extrator só traz o recorte de graduação (ALVGN)"
        ),
    ),
    "ENRIV": _razao("n_inscritos", "n_vagas"),
    "RESERVA": _soma("vagas_regulares"),
    "GACM": Formula(
        tipo="gacm",
        numerador="gastos_correntes",
        denominador=("gasto_por_mateq",),
        expressao="SUM(gastos_correntes) / SUM(gastos_correntes / gasto_por_mateq)",
    ),
    "GAT": _soma("gastos_totais"),
    "GAC": _soma("gastos_correntes"),
    "GAPE": _soma("gastos_pessoal"),
    "GAOC": _soma("gastos_custeio"),
    "GAIV": _soma("gastos_investimento"),
    "GAIP": _soma("gastos_inativos"),
    "GAPRE": _soma("gastos_precatorios"),
    "PEDO": _soma("n_docentes"),
    "PEDE": _soma("n_docentes_efetivos"),
    "PETAE": _soma("n_tae"),
    "PES": _soma("n_servidores"),
    "PETCD": Formula(
        tipo="ponderado",
        numerador="itcd",
        peso="n_docentes_efetivos",
        expressao="SUM(itcd * n_docentes_efetivos) / SUM(n_docentes_efetivos)",
    ),
    "PROFE": _soma("profeq"),
    "DOTACAO": _soma("dotacao_atualizada"),
    "EMPENHO": _soma("despesa_empenhada"),
    "LIQUIDACAO": _soma("despesa_liquidada"),
    "PAGA": _soma("despesa_paga"),
    "A_LIQUIDAR": _soma("empenhado_a_liquidar"),
    "CREDITO": _soma("credito_disponivel"),
    "COR_RACA": _soma("n_matriculas"),
    "RENDA": _soma("n_matriculas"),
    "SEXO": _soma("n_matriculas"),
    "FAIXA_ETARIA": _soma("n_matriculas"),
}


def formula_de(codigo: str) -> Formula:
    try:
        return FORMULAS[codigo]
    except KeyError as exc:
        raise KeyError(codigo) from exc
