"""Recortes que o painel/Extrator realmente publica, por conjunto.

Não se expõe dimensão só porque a coluna existe no SQLite, nem recorte
inventado (excluir_fic, campi homogêneos, join entre tabelas).
"""

from __future__ import annotations

from mcp_pnp.db.schema import TABLES, fields_of
from mcp_pnp.registry import INDICADORES_MVP, Indicador

# Hierarquia comum a todas as páginas do painel.
HIERARQUIA: tuple[str, ...] = (
    "ano",
    "regiao",
    "uf",
    "organizacao_academica",
    "instituicao",
    "unidade",
)

# Dimensões extras por conjunto do Extrator (colunas-slicer da página).
# Vazio = a página só recorta pela hierarquia.
RECORTES_PAINEL: dict[str, tuple[str, ...]] = {
    "oferta": ("tipo_curso", "tipo_oferta", "modalidade", "nome_curso"),
    "evasao": (
        "tipo_curso",
        "tipo_oferta",
        "modalidade",
        "turno",
        "eixo",
        "subeixo",
        "nome_curso",
        "programa",
    ),
    "situacao_matricula": (
        "categoria_situacao",
        "nome_situacao",
        "fluxo_retido",
        "motivo",
    ),
    "perfil_discente": ("cor_raca", "renda_familiar", "sexo", "faixa_etaria"),
    "reserva_vagas": ("tipo_reserva",),
    "docentes": ("titulacao", "jornada"),
    "docentes_jornada": ("titulacao", "jornada"),
    "tae": ("titulacao",),
    "orcamento": ("resultado_primario", "relacao_orgao"),
    "cargos": ("carreira_sigla",),
    "eficiencia": (),
    "rap": (),
    "gastos": (),
    "percentuais_legais": (),
    "verticalizacao": (),
    "ocupacao": (),
    "inscritos_vagas": (),
    "vagas_noturnas": (),
}

GROUPABLES: dict[str, str] = {
    "instituicao": "instituicao_sigla",
    "unidade": "unidade",
    "uf": "uf",
    "regiao": "regiao",
    "organizacao_academica": "organizacao_academica",
    "tipo_curso": "tipo_curso",
    "tipo_oferta": "tipo_oferta",
    "modalidade": "modalidade",
    "turno": "turno",
    "eixo": "eixo",
    "subeixo": "subeixo",
    "nome_curso": "nome_curso",
    "programa": "programa",
    "motivo": "motivo",
    "categoria_situacao": "categoria_situacao",
    "tipo_reserva": "tipo_reserva",
    "cor_raca": "cor_raca",
    "renda_familiar": "renda_familiar",
    "sexo": "sexo",
    "faixa_etaria": "faixa_etaria",
    "titulacao": "titulacao",
    "jornada": "jornada",
}

_IGNORE_KEYS = {
    "limite",
    "offset",
    "percentil",
    "group_by",
    "estatistica",
    "ano_inicio",
    "ano_fim",
    "nivel",
    "ordem",
    "top",
    "esquerda",
    "direita",
    "somente_oficial",
}

_META_TABLES = {"edicoes", "sync_log"}


def todos_recortes_painel() -> set[str]:
    out: set[str] = set()
    for dims in RECORTES_PAINEL.values():
        out.update(dims)
    return out


def recortes_do_indicador(indicador: Indicador) -> tuple[str, ...]:
    pagina = RECORTES_PAINEL.get(indicador.tabela, ())
    extras = [d for d in pagina if d in fields_of(indicador.tabela)]
    for extra in indicador.extra_filtros:
        if extra not in extras and extra in fields_of(indicador.tabela):
            extras.append(extra)
    return tuple(extras)


def tabelas_com(coluna: str) -> list[str]:
    if coluna in HIERARQUIA or coluna == "instituicao":
        col = "instituicao_sigla" if coluna == "instituicao" else coluna
        return [
            tabela
            for tabela in TABLES
            if tabela not in _META_TABLES and col in fields_of(tabela)
        ]
    return [
        tabela
        for tabela, dims in RECORTES_PAINEL.items()
        if coluna in dims and tabela in TABLES
    ]


def indicadores_com(coluna: str) -> list[str]:
    return [
        ind.codigo
        for ind in INDICADORES_MVP
        if coluna in recortes_do_indicador(ind)
    ]


def filtros_nativos(indicador: Indicador) -> tuple[str, ...]:
    return recortes_do_indicador(indicador)


def extras_da_assinatura(indicador: Indicador) -> tuple[tuple[str, type], ...]:
    return tuple((nome, str | None) for nome in recortes_do_indicador(indicador))


def mapeamento_filtros(indicador: Indicador) -> dict[str, str]:
    from mcp_pnp.db.queries import DIM_FILTERS

    mapping = dict(DIM_FILTERS)
    for dim in recortes_do_indicador(indicador):
        mapping[dim] = dim
    return mapping


def detalhe_indisponivel(coluna: str, indicador: Indicador) -> str:
    destinos = indicadores_com(coluna)
    if destinos:
        return (
            f"{indicador.codigo} não tem o recorte '{coluna}' no painel PNP. "
            f"Esse recorte existe em: {', '.join(destinos)}."
        )
    return (
        f"'{coluna}' não é recorte do painel PNP para nenhum indicador carregado."
    )


def coluna_agrupavel(nivel: str, indicador: Indicador) -> str:
    permitidos = set(HIERARQUIA) | set(recortes_do_indicador(indicador))
    if nivel not in permitidos and GROUPABLES.get(nivel) not in permitidos:
        raise KeyError(nivel)
    col = GROUPABLES.get(nivel, nivel)
    if col not in fields_of(indicador.tabela):
        raise KeyError(nivel)
    return col


def campos_listaveis() -> tuple[str, ...]:
    seen: list[str] = []
    for nome in (*HIERARQUIA, *sorted(todos_recortes_painel())):
        if nome == "ano" or nome in seen:
            continue
        seen.append(nome)
    return tuple(seen)
