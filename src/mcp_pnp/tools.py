from __future__ import annotations

import inspect
import sqlite3
from typing import Any

from fastmcp import FastMCP

from mcp_pnp.analysis import agregar, comparar, estatisticas, evolucao, ranking
from mcp_pnp.config import Settings
from mcp_pnp.db.queries import _connect, cobertura_edicoes, consultar, listar_valores_campo
from mcp_pnp.db.schema import TABLES
from mcp_pnp.dimensions import extras_da_assinatura, filtros_nativos
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.glossary import explicar
from mcp_pnp.ingest.sync import sync
from mcp_pnp.registry import INDICADORES_MVP, Indicador, get, listar

_COMMON: tuple[tuple[str, type], ...] = (
    ("ano", int | None),
    ("instituicao", str | None),
    ("unidade", str | None),
    ("uf", str | None),
    ("regiao", str | None),
    ("organizacao_academica", str | None),
    ("limite", int | None),
    ("offset", int | None),
)

def _descricao(ind: Indicador) -> str:
    aliases = f" Aliases: {', '.join(ind.aliases)}." if ind.aliases else ""
    meta = f" Meta: {ind.meta}." if ind.meta is not None else ""
    recortes = filtros_nativos(ind)
    painel = (
        f" Recortes do painel: {', '.join(recortes)}."
        if recortes
        else " Sem recorte além de ano/instituição/unidade/UF/região."
    )
    return (
        f"{ind.codigo} — {ind.nome}.{aliases}{meta}{painel} "
        f"O número institucional/oficial está em valor_oficial "
        f"(fórmula do Guia: soma do numerador / soma do denominador). "
        f"Não use a média do campo valor nas linhas de registros. "
        f"Exemplo: Qual a {ind.codigo} do IFMG em 2025?"
    )


def _make_consulta(indicador: Indicador):
    def _consulta(**filtros: Any) -> dict[str, Any]:
        try:
            return consultar(Settings.from_env().db_path, indicador, filtros)
        except PnpError as err:
            return err.as_dict()

    params = [
        inspect.Parameter(
            name,
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=ann,
        )
        for name, ann in _COMMON
    ]
    for extra, ann in extras_da_assinatura(indicador):
        params.append(
            inspect.Parameter(
                extra,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=ann,
            )
        )
    _consulta.__signature__ = inspect.Signature(
        params, return_annotation=dict[str, Any]
    )
    _consulta.__annotations__ = {p.name: p.annotation for p in params}
    _consulta.__annotations__["return"] = dict[str, Any]
    _consulta.__name__ = indicador.tool
    _consulta.__doc__ = _descricao(indicador)
    return _consulta


def _rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def pnp_listar_edicoes() -> dict[str, Any]:
    """Lista anos carregados, edição PNP e data do último sync."""
    try:
        conn = _connect(Settings.from_env().db_path)
    except PnpError as err:
        return err.as_dict()
    try:
        registros = cobertura_edicoes(conn)
        return ok(
            fonte="oficial",
            edicao_pnp=None,
            ano=None,
            indicador="edicoes",
            unidade_medida="contagem",
            filtros_aplicados={},
            registros=registros,
            aviso="cobertura lista tabelas com linha naquele ano (não é presença de todo indicador).",
        )
    finally:
        conn.close()


def pnp_listar_instituicoes(
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
) -> dict[str, Any]:
    """Lista instituições distintas da oferta, com filtros opcionais de UF/região."""
    try:
        conn = _connect(Settings.from_env().db_path)
    except PnpError as err:
        return err.as_dict()
    try:
        where: list[str] = []
        params: list[Any] = []
        if uf:
            where.append("uf = ?")
            params.append(uf)
        if regiao:
            where.append("regiao = ?")
            params.append(regiao)
        if organizacao_academica:
            where.append("organizacao_academica = ?")
            params.append(organizacao_academica)
        sql = (
            "SELECT DISTINCT instituicao_sigla, instituicao_nome, "
            "organizacao_academica, uf, regiao FROM oferta"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY instituicao_sigla"
        return ok(
            fonte="oficial",
            edicao_pnp=None,
            ano=None,
            indicador="instituicoes",
            unidade_medida="contagem",
            filtros_aplicados={
                k: v
                for k, v in {
                    "uf": uf,
                    "regiao": regiao,
                    "organizacao_academica": organizacao_academica,
                }.items()
                if v is not None
            },
            registros=_rows(conn, sql, tuple(params)),
        )
    finally:
        conn.close()


def pnp_listar_unidades(instituicao: str) -> dict[str, Any]:
    """Lista campi/unidades de uma instituição (instituição obrigatória)."""
    if not instituicao or not str(instituicao).strip():
        return PnpError("instituicao_desconhecida").as_dict()
    try:
        conn = _connect(Settings.from_env().db_path)
    except PnpError as err:
        return err.as_dict()
    try:
        registros = _rows(
            conn,
            "SELECT DISTINCT unidade, instituicao_sigla FROM oferta "
            "WHERE UPPER(instituicao_sigla) = UPPER(?) ORDER BY unidade",
            (instituicao,),
        )
        if not registros:
            return PnpError("instituicao_desconhecida", instituicao).as_dict()
        return ok(
            fonte="oficial",
            edicao_pnp=None,
            ano=None,
            indicador="unidades",
            unidade_medida="contagem",
            filtros_aplicados={"instituicao": instituicao},
            registros=registros,
        )
    finally:
        conn.close()


def pnp_listar_indicadores(somente_oficial: bool = False) -> dict[str, Any]:
    """Lista os indicadores do MVP (código, nome, família, se é oficial)."""
    items = listar(somente_oficial=somente_oficial)
    registros = [
        {
            "codigo": i.codigo,
            "nome": i.nome,
            "familia": i.familia,
            "oficial": i.oficial,
            "tool": i.tool,
            "unidade_medida": i.unidade_medida,
            "aliases": list(i.aliases),
            "meta": i.meta,
            "tabela": i.tabela,
            "filtros": list(filtros_nativos(i)),
        }
        for i in items
    ]
    return ok(
        fonte="oficial",
        edicao_pnp=None,
        ano=None,
        indicador="indicadores",
        unidade_medida="contagem",
        filtros_aplicados={"somente_oficial": somente_oficial},
        registros=registros,
    )


def pnp_glossario(termo: str) -> dict[str, Any]:
    """Definição, fórmula, fonte e ressalva de um indicador ou conceito do Guia."""
    try:
        return explicar(termo)
    except PnpError as err:
        return err.as_dict()


def pnp_status_base() -> dict[str, Any]:
    """Caminho do SQLite, edições carregadas, linhas por tabela e último sync."""
    settings = Settings.from_env()
    path = settings.db_path
    if not path.exists():
        return {
            "db_path": str(path),
            "existe": False,
            "edicoes": [],
            "contagem": {},
            "ultimo_sync": None,
        }
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        try:
            edicoes = _rows(conn, "SELECT * FROM edicoes ORDER BY ano")
        except sqlite3.Error:
            edicoes = []
        contagem: dict[str, int] = {}
        for tabela in TABLES:
            try:
                contagem[tabela] = conn.execute(
                    f"SELECT COUNT(*) FROM {tabela}"
                ).fetchone()[0]
            except sqlite3.Error:
                contagem[tabela] = 0
        try:
            ultimo = conn.execute(
                "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            ultimo_sync = dict(ultimo) if ultimo else None
        except sqlite3.Error:
            ultimo_sync = None
        return {
            "db_path": str(path),
            "existe": True,
            "edicoes": edicoes,
            "contagem": contagem,
            "ultimo_sync": ultimo_sync,
        }
    finally:
        conn.close()


def pnp_sincronizar(forcar: bool = False) -> dict[str, Any]:
    """Baixa os CSVs do Extrator e recarrega o SQLite local."""
    del forcar  # o sync do MVP sempre recarrega os conjuntos
    try:
        return sync(Settings.from_env())
    except PnpError as err:
        return err.as_dict()


def _filtros_recorte(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


def pnp_consultar(
    indicador: str,
    ano: int | None = None,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
    tipo_curso: str | None = None,
    tipo_oferta: str | None = None,
    modalidade: str | None = None,
    turno: str | None = None,
    eixo: str | None = None,
    subeixo: str | None = None,
    nome_curso: str | None = None,
    programa: str | None = None,
    limite: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """Consulta um indicador pela sigla. Recortes extras só os do painel daquele indicador."""
    filtros = _filtros_recorte(
        ano=ano,
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
        organizacao_academica=organizacao_academica,
        tipo_curso=tipo_curso,
        tipo_oferta=tipo_oferta,
        modalidade=modalidade,
        turno=turno,
        eixo=eixo,
        subeixo=subeixo,
        nome_curso=nome_curso,
        programa=programa,
        limite=limite,
        offset=offset,
    )
    try:
        return consultar(Settings.from_env().db_path, get(indicador), filtros)
    except PnpError as err:
        return err.as_dict()


def pnp_comparar(
    indicador: str,
    esquerda: dict[str, Any],
    direita: dict[str, Any],
) -> dict[str, Any]:
    """Compara um indicador entre dois recortes pela fórmula oficial. fonte=derivada."""
    try:
        return comparar(Settings.from_env().db_path, indicador, esquerda, direita)
    except PnpError as err:
        return err.as_dict()


def pnp_evolucao(
    indicador: str,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
    tipo_curso: str | None = None,
    tipo_oferta: str | None = None,
    modalidade: str | None = None,
    turno: str | None = None,
    eixo: str | None = None,
    subeixo: str | None = None,
    nome_curso: str | None = None,
    programa: str | None = None,
) -> dict[str, Any]:
    """Série anual e YoY pela fórmula oficial. Recortes só os do painel do indicador."""
    filtros = _filtros_recorte(
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
        organizacao_academica=organizacao_academica,
        tipo_curso=tipo_curso,
        tipo_oferta=tipo_oferta,
        modalidade=modalidade,
        turno=turno,
        eixo=eixo,
        subeixo=subeixo,
        nome_curso=nome_curso,
        programa=programa,
    )
    try:
        return evolucao(
            Settings.from_env().db_path,
            indicador,
            filtros,
            ano_inicio,
            ano_fim,
        )
    except PnpError as err:
        return err.as_dict()


def pnp_ranking(
    indicador: str,
    nivel: str = "instituicao",
    ordem: str = "desc",
    ano: int | None = None,
    top: int = 10,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
    tipo_curso: str | None = None,
    tipo_oferta: str | None = None,
    modalidade: str | None = None,
    turno: str | None = None,
    eixo: str | None = None,
) -> dict[str, Any]:
    """Ranking pela fórmula oficial. nivel só hierarquia ou recorte do painel daquele indicador."""
    filtros = _filtros_recorte(
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
        organizacao_academica=organizacao_academica,
        tipo_curso=tipo_curso,
        tipo_oferta=tipo_oferta,
        modalidade=modalidade,
        turno=turno,
        eixo=eixo,
    )
    try:
        return ranking(
            Settings.from_env().db_path, indicador, nivel, ordem, ano, top, filtros
        )
    except PnpError as err:
        return err.as_dict()


def pnp_agregar(
    indicador: str,
    group_by: str,
    ano: int | None = None,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
    tipo_curso: str | None = None,
    tipo_oferta: str | None = None,
    modalidade: str | None = None,
    turno: str | None = None,
    eixo: str | None = None,
) -> dict[str, Any]:
    """Quebra um indicador pela fórmula oficial. group_by só recorte do painel daquele indicador."""
    filtros = _filtros_recorte(
        ano=ano,
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
        organizacao_academica=organizacao_academica,
        tipo_curso=tipo_curso,
        tipo_oferta=tipo_oferta,
        modalidade=modalidade,
        turno=turno,
        eixo=eixo,
    )
    try:
        return agregar(Settings.from_env().db_path, indicador, group_by, filtros)
    except PnpError as err:
        return err.as_dict()


def pnp_listar_valores(
    campo: str,
    ano: int | None = None,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
) -> dict[str, Any]:
    """Valores distintos de uma dimensão (modalidade, tipo_curso, unidade…) em qualquer tabela que a tenha."""
    filtros = _filtros_recorte(
        ano=ano,
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
    )
    try:
        return listar_valores_campo(Settings.from_env().db_path, campo, filtros)
    except PnpError as err:
        return err.as_dict()


def pnp_estatisticas(
    indicador: str,
    estatistica: str,
    ano: int | None = None,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
    tipo_curso: str | None = None,
    modalidade: str | None = None,
    percentil: float | None = None,
) -> dict[str, Any]:
    """media = valor oficial do Guia; mediana/percentil = distribuição das linhas."""
    filtros: dict[str, Any] = _filtros_recorte(
        ano=ano,
        instituicao=instituicao,
        unidade=unidade,
        uf=uf,
        regiao=regiao,
        organizacao_academica=organizacao_academica,
        tipo_curso=tipo_curso,
        modalidade=modalidade,
    )
    if percentil is not None:
        filtros["percentil"] = percentil
    try:
        return estatisticas(
            Settings.from_env().db_path,
            indicador,
            filtros,
            estatistica,
        )
    except PnpError as err:
        return err.as_dict()


_EXTRAS: tuple[tuple[Any, str, str], ...] = (
    (
        pnp_listar_edicoes,
        "pnp_listar_edicoes",
        "Lista anos e edições PNP carregados na base local.",
    ),
    (
        pnp_listar_instituicoes,
        "pnp_listar_instituicoes",
        "Lista instituições distintas da oferta (filtros: uf, regiao, organizacao_academica).",
    ),
    (
        pnp_listar_unidades,
        "pnp_listar_unidades",
        "Lista unidades/campi de uma instituição. Parâmetro obrigatório: instituicao.",
    ),
    (
        pnp_listar_indicadores,
        "pnp_listar_indicadores",
        "Lista indicadores do MVP (código, nome, família, oficial).",
    ),
    (
        pnp_consultar,
        "pnp_consultar",
        "Consulta qualquer indicador do catálogo pela sigla (ENEVA, ENME…). "
        "Recortes extras só os do painel PNP daquele indicador "
        "(veja pnp_listar_indicadores.filtros). Recorte inexistente no painel é rejeitado.",
    ),
    (
        pnp_listar_valores,
        "pnp_listar_valores",
        "Valores distintos de uma dimensão em qualquer tabela que a tenha "
        "(modalidade, tipo_curso, unidade, eixo…).",
    ),
    (
        pnp_comparar,
        "pnp_comparar",
        "Compara um indicador entre dois recortes com a fórmula oficial do Guia "
        "(não é média de taxas). fonte=derivada. Recortes no dict esquerda/direita.",
    ),
    (
        pnp_evolucao,
        "pnp_evolucao",
        "Série anual e YoY com a fórmula oficial do Guia. "
        "ano_inicio/ano_fim opcionais (usa o intervalo com dado). "
        "Recortes extras só os do painel daquele indicador.",
    ),
    (
        pnp_ranking,
        "pnp_ranking",
        "Ranking com a fórmula oficial. nivel=instituição/unidade/UF/região "
        "ou recorte do painel daquele indicador (ex.: modalidade só em ENEVA/ENM).",
    ),
    (
        pnp_agregar,
        "pnp_agregar",
        "Quebra um indicador pela fórmula oficial. group_by só hierarquia ou "
        "recorte do painel daquele indicador. fonte=derivada.",
    ),
    (
        pnp_estatisticas,
        "pnp_estatisticas",
        "estatistica=media devolve o valor oficial do Guia (não a média das taxas). "
        "mediana/percentil descrevem a distribuição das linhas. fonte=derivada.",
    ),
    (
        pnp_glossario,
        "pnp_glossario",
        "Definição, fórmula, fonte e ressalva de um termo do Guia PNP.",
    ),
    (
        pnp_status_base,
        "pnp_status_base",
        "Caminho do SQLite, edições, linhas por tabela e último sync.",
    ),
    (
        pnp_sincronizar,
        "pnp_sincronizar",
        "Baixa CSVs do Extrator PNP e recarrega o SQLite local.",
    ),
)


def register_all(mcp: FastMCP) -> None:
    for ind in INDICADORES_MVP:
        mcp.tool(
            _make_consulta(ind),
            name=ind.tool,
            description=_descricao(ind),
        )
    for fn, name, description in _EXTRAS:
        mcp.tool(fn, name=name, description=description)
