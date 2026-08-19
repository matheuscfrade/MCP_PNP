from __future__ import annotations

from typing import Any

from mcp_pnp.errors import PnpError
from mcp_pnp.registry import get

# Aliases que não estão no registry (conceito do Guia, não sigla).
_EXTRA_ALIASES = {
    "matricula_atendida": "ENM",
    "matrícula_atendida": "ENM",
    "matricula atendida": "ENM",
}

VERBETES: dict[str, dict[str, Any]] = {
    "ENME": {
        "codigo": "ENME",
        "definicao": (
            "Número de matrículas equivalentes: a matrícula atendida ponderada "
            "pela carga horária e pelo tipo de curso, para comparar ofertas distintas."
        ),
        "formula": "Soma das matrículas ponderadas pelos fatores oficiais de equivalência.",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Não confundir com ENM (matrícula atendida, sem ponderação).",
    },
    "ENM": {
        "codigo": "ENM",
        "definicao": (
            "Número de matrículas (matrícula atendida) no ciclo de referência, "
            "sem ponderação por carga horária."
        ),
        "formula": "Contagem das matrículas atendidas no ano/ciclo.",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "A matrícula atendida não é a matrícula equivalente (ENME).",
    },
    "ENEMA": {
        "codigo": "ENEMA",
        "definicao": "Número de estruturas com matrícula (campi/unidades com ao menos uma matrícula).",
        "formula": "Contagem distinta de estruturas que possuem matrícula no recorte.",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Distinto de ENUND (unidades acadêmicas).",
    },
    "ENUND": {
        "codigo": "ENUND",
        "definicao": "Número de unidades acadêmicas da instituição.",
        "formula": "Contagem distinta de unidades acadêmicas no recorte.",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Não é o mesmo que ENEMA (estruturas com matrícula).",
    },
    "ENIEA": {
        "codigo": "ENIEA",
        "definicao": (
            "Índice de eficiência acadêmica do ciclo: concluintes do ciclo "
            "acrescidos da projeção dos retidos que devem concluir "
            "(ponderador = concluintes / (concluintes + evadidos))."
        ),
        "formula": (
            "ENIEA = [C + (C / (C + Ev)) × R] / (C + Ev + R) × 100, "
            "algebricamente igual a C / (C + Ev) × 100."
        ),
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Indicador de ciclo, não de evasão anual (ENEVA).",
    },
    "ENEVA": {
        "codigo": "ENEVA",
        "definicao": "Percentual de evasão anual das matrículas no ano de referência.",
        "formula": "Σ evadidos / Σ matrículas × 100 (não é média das taxas por curso).",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Diferente da evasão por ciclo (ENEC).",
    },
    "ENEC": {
        "codigo": "ENEC",
        "definicao": "Percentual de evasão por ciclo de matrícula.",
        "formula": "Evadidos do ciclo / (concluintes + evadidos + retidos) × 100.",
        "fonte": "Sistec / Guia PNP Indicadores",
        "ressalva": "Complementa ENCC e ENREC no mesmo ciclo.",
    },
    "ALMTEC": {
        "codigo": "ALMTEC",
        "definicao": "Percentual de matrícula equivalente em educação profissional técnica de nível médio (EPTNM).",
        "formula": "Mateq EPTNM / Mateq geral × 100.",
        "fonte": "Sistec / Lei 11.892/2008",
        "ressalva": "Meta legal de 50% para Institutos Federais.",
    },
    "ALMPROF": {
        "codigo": "ALMPROF",
        "definicao": "Percentual de matrícula equivalente em cursos de formação de professores.",
        "formula": "Mateq formação de professores / Mateq geral × 100.",
        "fonte": "Sistec / Lei 11.892/2008",
        "ressalva": "Meta legal de 20% para Institutos Federais.",
    },
    "ALMEJA": {
        "codigo": "ALMEJA",
        "definicao": "Percentual de matrícula equivalente em EJA/EPT (PROEJA).",
        "formula": "Mateq EJA/EPT / Mateq geral × 100.",
        "fonte": "Sistec / Decreto 5.840/2006",
        "ressalva": "Meta de 10% para Institutos Federais.",
    },
    "ALRMP": {
        "codigo": "ALRMP",
        "definicao": (
            "Relação matrícula-equivalente / professor-equivalente (RAP consagrada)."
        ),
        "formula": "ENME / professor-equivalente.",
        "fonte": "Sistec e Siape / Guia PNP Indicadores",
        "ressalva": "Não confundir com RAP orçamentário (restos a pagar).",
    },
    "ALRAPE": {
        "codigo": "ALRAPE",
        "definicao": "RAP presencial: matrícula equivalente presencial / professor-equivalente.",
        "formula": "Mateq presencial / professor-equivalente.",
        "fonte": "Sistec e Siape / Guia PNP Indicadores",
        "ressalva": "Meta de referência 20. Só considera matrículas presenciais.",
    },
    "GACM": {
        "codigo": "GACM",
        "definicao": "Gastos correntes por matrícula equivalente.",
        "formula": "Gastos correntes / ENME.",
        "fonte": "Siafi / Guia PNP Indicadores",
        "ressalva": "Valor oficial do Extrator; não recalcular a partir de rubricas avulsas.",
    },
    "PETCD": {
        "codigo": "PETCD",
        "definicao": "Índice de titulação do corpo docente efetivo.",
        "formula": "Pontuação ponderada da titulação dos docentes efetivos / docentes efetivos.",
        "fonte": "Siape / Guia PNP Indicadores",
        "ressalva": "Incide sobre o corpo docente efetivo, não sobre substitutos.",
    },
}


def explicar(termo: str) -> dict[str, Any]:
    chave = termo.strip()
    extra = _EXTRA_ALIASES.get(chave.lower())
    if extra:
        codigo = extra
    else:
        codigo = get(chave).codigo
    if codigo in VERBETES:
        return dict(VERBETES[codigo])
    raise PnpError("indicador_desconhecido", termo)
