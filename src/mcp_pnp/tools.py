from __future__ import annotations

import inspect
import sqlite3
from typing import Any

from fastmcp import FastMCP

from mcp_pnp.analysis import comparar, estatisticas, evolucao, ranking
from mcp_pnp.config import Settings
from mcp_pnp.db.queries import _connect, consultar
from mcp_pnp.db.schema import TABLES
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.glossary import explicar
from mcp_pnp.ingest.sync import sync
from mcp_pnp.registry import INDICADORES_MVP, Indicador, listar

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
    return (
        f"{ind.codigo} — {ind.nome}.{aliases}{meta} "
        f"Consulta o indicador oficial da PNP. "
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
    for extra in indicador.extra_filtros:
        params.append(
            inspect.Parameter(
                extra,
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=str | None,
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
        registros = _rows(conn, "SELECT * FROM edicoes ORDER BY ano")
        return ok(
            fonte="oficial",
            edicao_pnp=None,
            ano=None,
            indicador="edicoes",
            unidade_medida="contagem",
            filtros_aplicados={},
            registros=registros,
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
            return PnpError("unidade_desconhecida", instituicao).as_dict()
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


def pnp_comparar(
    indicador: str,
    esquerda: dict[str, Any],
    direita: dict[str, Any],
) -> dict[str, Any]:
    """Compara um indicador entre dois recortes. Resposta com fonte=derivada."""
    try:
        return comparar(Settings.from_env().db_path, indicador, esquerda, direita)
    except PnpError as err:
        return err.as_dict()


def pnp_evolucao(
    indicador: str,
    ano_inicio: int,
    ano_fim: int,
    instituicao: str | None = None,
    unidade: str | None = None,
    uf: str | None = None,
    regiao: str | None = None,
    organizacao_academica: str | None = None,
) -> dict[str, Any]:
    """Série anual e variação YoY. Resposta com fonte=derivada."""
    filtros = {
        "instituicao": instituicao,
        "unidade": unidade,
        "uf": uf,
        "regiao": regiao,
        "organizacao_academica": organizacao_academica,
    }
    try:
        return evolucao(
            Settings.from_env().db_path,
            indicador,
            {k: v for k, v in filtros.items() if v is not None},
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
) -> dict[str, Any]:
    """Ranking de instituições ou unidades. Resposta com fonte=derivada."""
    try:
        return ranking(Settings.from_env().db_path, indicador, nivel, ordem, ano, top)
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
    percentil: float | None = None,
) -> dict[str, Any]:
    """Média, mediana, percentil ou participação % na Rede. fonte=derivada."""
    filtros: dict[str, Any] = {
        "ano": ano,
        "instituicao": instituicao,
        "unidade": unidade,
        "uf": uf,
        "regiao": regiao,
        "organizacao_academica": organizacao_academica,
    }
    if percentil is not None:
        filtros["percentil"] = percentil
    try:
        return estatisticas(
            Settings.from_env().db_path,
            indicador,
            {k: v for k, v in filtros.items() if v is not None},
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
        pnp_comparar,
        "pnp_comparar",
        "Compara um indicador entre dois recortes. fonte=derivada.",
    ),
    (
        pnp_evolucao,
        "pnp_evolucao",
        "Série anual e variação YoY de um indicador. fonte=derivada.",
    ),
    (
        pnp_ranking,
        "pnp_ranking",
        "Ranking de instituições ou unidades. fonte=derivada.",
    ),
    (
        pnp_estatisticas,
        "pnp_estatisticas",
        "Média, mediana, percentil ou participação na Rede. fonte=derivada.",
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
