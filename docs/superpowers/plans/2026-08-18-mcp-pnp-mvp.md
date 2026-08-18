# MCP PNP MVP (Extrator) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um servidor MCP stdio em português que consulta indicadores oficiais da PNP (ensino, legal, pessoal, gastos, Tesouro) a partir de um SQLite local carregado dos CSVs do Extrator.

**Architecture:** Pacote `mcp_pnp` com FastMCP. Um registro `Indicador` (sigla do Guia → tabela/coluna) alimenta um único `consultar()`. O ingest baixa CSVs do Extrator (`pnpquery/{id}`), normaliza dimensões e grava no SQLite. Tools de pesquisa/extensão/polos/sustentabilidade/INEP **não** são registradas neste plano.

**Tech Stack:** Python 3.12+, FastMCP, httpx, pytest. Sem DuckDB.

**Spec:** `docs/superpowers/specs/2026-08-18-mcp-pnp-design.md` (recorte MVP Extrator).

---

## File structure

| path | responsibility |
|---|---|
| `pyproject.toml` | pacote, deps, script `mcp-pnp` |
| `src/mcp_pnp/__init__.py` | versão |
| `src/mcp_pnp/__main__.py` | `python -m mcp_pnp` |
| `src/mcp_pnp/config.py` | env `PNP_DB_PATH`, `PNP_CACHE_DIR`, `PNP_EXTRATOR_BASE`, `PNP_MAX_REGISTROS` |
| `src/mcp_pnp/errors.py` | `PnpError` com códigos estáveis |
| `src/mcp_pnp/envelope.py` | monta o JSON padrão |
| `src/mcp_pnp/registry.py` | `Indicador` + `INDICADORES_MVP` |
| `src/mcp_pnp/db/schema.py` | DDL SQLite |
| `src/mcp_pnp/db/queries.py` | SELECT parametrizado + filtros |
| `src/mcp_pnp/ingest/catalog.py` | query_id Extrator → tabela |
| `src/mcp_pnp/ingest/client.py` | download CSV |
| `src/mcp_pnp/ingest/loader.py` | valida, normaliza, carrega |
| `src/mcp_pnp/ingest/sync.py` | orquestra sync |
| `src/mcp_pnp/glossary.py` | verbetes do Guia |
| `src/mcp_pnp/analysis.py` | comparar, evolução, ranking, estatísticas |
| `src/mcp_pnp/tools.py` | registra tools FastMCP a partir do registry |
| `src/mcp_pnp/server.py` | FastMCP + resources + prompts |
| `src/mcp_pnp/cli.py` | `mcp-pnp` / `mcp-pnp sync` |
| `tests/conftest.py` | SQLite temporário + fixture mínima |
| `tests/fixtures/oferta.csv` | 4 linhas (IFMG + IFB, 2024–2025) |
| `tests/test_envelope.py` | contrato de resposta |
| `tests/test_queries.py` | filtros e `base_vazia` |
| `tests/test_ingest.py` | client/loader com HTTP mock |
| `tests/test_tools.py` | 1 consulta por família + análise + contrato de nomes |
| `README.md` | instalar, sync, config Grok/Claude |

---

### Task 1: Skeleton do pacote

**Files:**
- Create: `pyproject.toml`
- Create: `src/mcp_pnp/__init__.py`
- Create: `src/mcp_pnp/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from mcp_pnp.config import Settings


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("PNP_DB_PATH", raising=False)
    monkeypatch.delenv("PNP_CACHE_DIR", raising=False)
    monkeypatch.delenv("PNP_EXTRATOR_BASE", raising=False)
    monkeypatch.delenv("PNP_MAX_REGISTROS", raising=False)
    s = Settings.from_env()
    assert s.db_path.name == "pnp.sqlite"
    assert s.extrator_base == "https://moduloextratorpnp.mec.gov.br"
    assert s.max_registros == 200


def test_max_registros_capped(monkeypatch):
    monkeypatch.setenv("PNP_MAX_REGISTROS", "9999")
    s = Settings.from_env()
    assert s.max_registros == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: mcp_pnp`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-pnp"
version = "0.1.0"
description = "Servidor MCP da Plataforma Nilo Peçanha (indicadores oficiais)"
requires-python = ">=3.12"
dependencies = [
  "fastmcp>=2.10.0",
  "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
mcp-pnp = "mcp_pnp.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_pnp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# src/mcp_pnp/__init__.py
__version__ = "0.1.0"
```

```python
# src/mcp_pnp/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    cache_dir: Path
    extrator_base: str
    max_registros: int

    @classmethod
    def from_env(cls) -> Settings:
        root = Path.cwd() / "data"
        max_reg = int(os.environ.get("PNP_MAX_REGISTROS", "200"))
        if max_reg < 1:
            max_reg = 1
        if max_reg > 500:
            max_reg = 500
        return cls(
            db_path=Path(os.environ.get("PNP_DB_PATH", str(root / "pnp.sqlite"))),
            cache_dir=Path(os.environ.get("PNP_CACHE_DIR", str(root / "cache"))),
            extrator_base=os.environ.get(
                "PNP_EXTRATOR_BASE", "https://moduloextratorpnp.mec.gov.br"
            ).rstrip("/"),
            max_registros=max_reg,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e ".[dev]"` then `pytest tests/test_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/mcp_pnp/__init__.py src/mcp_pnp/config.py tests/test_config.py
git commit -m "chore: scaffold mcp-pnp package and settings"
```

---

### Task 2: Envelope e erros

**Files:**
- Create: `src/mcp_pnp/errors.py`
- Create: `src/mcp_pnp/envelope.py`
- Create: `tests/test_envelope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_envelope.py
import pytest
from mcp_pnp.envelope import ok, PnpError


def test_ok_oficial():
    body = ok(
        fonte="oficial",
        edicao_pnp="2026",
        ano=2025,
        indicador="ENME",
        unidade_medida="matriculas_equivalentes",
        filtros_aplicados={"instituicao": "IFMG", "ano": 2025},
        registros=[{"instituicao_sigla": "IFMG", "valor": 10.0}],
    )
    assert body["fonte"] == "oficial"
    assert body["indicador"] == "ENME"
    assert body["total_registros"] == 1
    assert body["truncado"] is False
    assert body["aviso"] is None


def test_erro_base_vazia_mensagem_pt():
    err = PnpError("base_vazia")
    assert err.codigo == "base_vazia"
    assert "pnp_sincronizar" in err.message
    assert "mcp-pnp sync" in err.message


def test_limite_invalido():
    with pytest.raises(PnpError) as ei:
        raise PnpError("limite_invalido")
    assert "500" in ei.value.message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_envelope.py -v`

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcp_pnp/errors.py
from __future__ import annotations


MENSAGENS = {
    "base_vazia": (
        "Base local vazia. Execute pnp_sincronizar ou `mcp-pnp sync`."
    ),
    "ano_indisponivel": "Ano pedido não está carregado. Use pnp_listar_edicoes.",
    "instituicao_desconhecida": (
        "Instituição não encontrada. Use pnp_listar_instituicoes."
    ),
    "unidade_desconhecida": "Unidade não encontrada. Use pnp_listar_unidades.",
    "indicador_desconhecido": (
        "Indicador desconhecido. Use pnp_listar_indicadores."
    ),
    "sem_registros": "Nenhum registro para os filtros informados.",
    "sync_falhou": "Falha ao sincronizar o Extrator PNP.",
    "fonte_indisponivel": (
        "Indicador oficial sem CSV na base. Não está no MVP do Extrator."
    ),
    "limite_invalido": "limite deve estar entre 1 e 500.",
}


class PnpError(Exception):
    def __init__(self, codigo: str, detalhe: str | None = None) -> None:
        self.codigo = codigo
        base = MENSAGENS.get(codigo, "Erro na consulta PNP.")
        self.message = f"{base} {detalhe}".strip() if detalhe else base
        super().__init__(self.message)

    def as_dict(self) -> dict:
        return {"erro": True, "codigo": self.codigo, "mensagem": self.message}
```

```python
# src/mcp_pnp/envelope.py
from __future__ import annotations

from typing import Any

from mcp_pnp.errors import PnpError

ok_fonte = {"oficial", "derivada"}


def ok(
    *,
    fonte: str,
    edicao_pnp: str | None,
    ano: int | None,
    indicador: str,
    unidade_medida: str,
    filtros_aplicados: dict[str, Any],
    registros: list[dict[str, Any]],
    truncado: bool = False,
    aviso: str | None = None,
) -> dict[str, Any]:
    if fonte not in ok_fonte:
        raise ValueError(fonte)
    return {
        "fonte": fonte,
        "edicao_pnp": edicao_pnp,
        "ano": ano,
        "indicador": indicador,
        "unidade_medida": unidade_medida,
        "filtros_aplicados": filtros_aplicados,
        "total_registros": len(registros),
        "truncado": truncado,
        "registros": registros,
        "aviso": aviso,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_envelope.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_pnp/errors.py src/mcp_pnp/envelope.py tests/test_envelope.py
git commit -m "feat: add PNP response envelope and stable error codes"
```

---

### Task 3: Registry dos indicadores do MVP

**Files:**
- Create: `src/mcp_pnp/registry.py`
- Create: `tests/test_registry.py`

Cada consulta nomeável do MVP é um `Indicador`. Tools de descoberta/análise/ops não entram aqui.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
from mcp_pnp.registry import INDICADORES_MVP, get, listar


def test_siglas_ensino_obrigatorias():
    codigos = {i.codigo for i in INDICADORES_MVP}
    for sigla in (
        "ENCT", "ENC", "ENEV", "ENEMA", "ENING", "ENIC", "ENM", "ENME",
        "ENUND", "ENV", "ENIEA", "ENIV", "ENCC", "ENEVA", "ENEC", "ENREC",
        "ENRIV", "ENOC", "ALMTEC", "ALMPROF", "ALMEJA", "ALVTEC", "ALVPROF",
        "ALVEJA", "ALGN", "ALMGN", "ALVGN", "ALVCN", "ALRMP", "ALRAPE",
        "GACM", "GAT", "GAC", "GAPE", "GAOC", "GAIV", "GAIP", "GAPRE",
        "PETCD", "PEDO", "PEDE", "PES", "PETAE",
    ):
        assert sigla in codigos, sigla


def test_get_por_alias():
    assert get("mateq").codigo == "ENME"
    assert get("rap").codigo == "ALRMP"
    assert get("almtec").codigo == "ALMTEC"


def test_fora_do_mvp_nao_registra_pesquisa():
    assert all(not i.codigo.startswith("PI") for i in INDICADORES_MVP)
    assert all(not i.codigo.startswith("EX") for i in INDICADORES_MVP)


def test_listar_so_oficiais_quando_pedido():
    oficiais = listar(somente_oficial=True)
    assert all(i.oficial for i in oficiais)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_registry.py -v`

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/mcp_pnp/registry.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Indicador:
    codigo: str
    nome: str
    familia: str
    tabela: str
    coluna: str
    unidade_medida: str
    tool: str
    oficial: bool
    aliases: tuple[str, ...] = ()
    extra_filtros: tuple[str, ...] = ()
    meta: float | None = None


def _i(*args, **kwargs) -> Indicador:
    return Indicador(*args, **kwargs)


# tabela/coluna = nomes JÁ normalizados pelo loader (Task 5)
INDICADORES_MVP: tuple[Indicador, ...] = (
    _i("ENEMA", "Número de estruturas com matrícula", "ensino", "oferta", "n_estruturas", "contagem", "pnp_consultar_estruturas", True, ("estruturas",)),
    _i("ENUND", "Número de unidades acadêmicas", "ensino", "oferta", "n_unidades", "contagem", "pnp_consultar_unidades_academicas", True, ("unidades_academicas",)),
    _i("ENC", "Número de cursos", "ensino", "oferta", "n_cursos", "contagem", "pnp_consultar_cursos", True, ("cursos",)),
    _i("ENM", "Número de matrículas", "ensino", "oferta", "n_matriculas", "matriculas", "pnp_consultar_matriculas", True, ("matriculas", "enm")),
    _i("ENME", "Número de matrículas equivalentes", "ensino", "oferta", "mateq", "matriculas_equivalentes", "pnp_consultar_mateq", True, ("mateq", "enme")),
    _i("ENV", "Número de vagas", "ensino", "oferta", "n_vagas", "vagas", "pnp_consultar_vagas", True, ("vagas",)),
    _i("ENIC", "Número de inscritos", "ensino", "oferta", "n_inscritos", "inscritos", "pnp_consultar_inscritos", True, ("inscritos",)),
    _i("ENING", "Número de ingressantes", "ensino", "oferta", "n_ingressantes", "ingressantes", "pnp_consultar_ingressantes", True, ("ingressantes",)),
    _i("ENCT", "Número de concluintes", "ensino", "oferta", "n_concluintes", "concluintes", "pnp_consultar_concluintes", True, ("concluintes",)),
    _i("CICLOS", "Número de ciclos", "ensino", "oferta", "n_ciclos", "contagem", "pnp_consultar_ciclos", False, ("ciclos",)),
    _i("EM_CURSO", "Matrículas em curso", "situacao", "situacao_matricula", "n_matriculas", "matriculas", "pnp_consultar_em_curso", False, (), ("categoria_situacao",)),
    _i("ENEV", "Número de evadidos", "situacao", "situacao_matricula", "n_matriculas", "matriculas", "pnp_consultar_evadidos", True, ("evadidos",), ("motivo",)),
    _i("RETIDOS", "Matrículas retidas", "situacao", "situacao_matricula", "n_matriculas", "matriculas", "pnp_consultar_retidos", False, (), ("fluxo_retido",)),
    _i("ENEVA", "Percentual de evasão anual", "academico", "evasao", "taxa_evasao", "percentual", "pnp_consultar_evasao", True, ("evasao", "evasao_anual")),
    _i("ENEC", "Percentual de evasão por ciclo", "academico", "eficiencia", "taxa_evasao_ciclo", "percentual", "pnp_consultar_evasao_ciclo", True, ("evasao_ciclo",)),
    _i("ENCC", "Percentual de conclusão por ciclo", "academico", "eficiencia", "taxa_conclusao_ciclo", "percentual", "pnp_consultar_conclusao_ciclo", True, ("conclusao_ciclo",)),
    _i("ENREC", "Percentual de retenção por ciclo", "academico", "eficiencia", "taxa_retencao_ciclo", "percentual", "pnp_consultar_retencao_ciclo", True, ("retencao_ciclo",)),
    _i("ENIEA", "Índice de eficiência acadêmica", "academico", "eficiencia", "iea", "percentual", "pnp_consultar_eficiencia_academica", True, ("eficiencia", "iea")),
    _i("ALRMP", "Relação matrícula-equivalente / professor-equivalente", "academico", "rap", "rap", "razao", "pnp_consultar_rap", True, ("rap", "rmp", "alrmp")),
    _i("ALRAPE", "RAP presencial", "academico", "rap", "rap_presencial", "razao", "pnp_consultar_rap_presencial", True, ("rap_presencial", "alrape"), (), 20.0),
    _i("ENIV", "Índice de verticalização", "academico", "verticalizacao", "iv", "indice", "pnp_consultar_verticalizacao", True, ("verticalizacao",)),
    _i("ENOC", "Taxa de ocupação", "academico", "ocupacao", "taxa_ocupacao", "percentual", "pnp_consultar_ocupacao", True, ("ocupacao",)),
    _i("ALMTEC", "Percentual de Mateq em EPTNM", "legal", "percentuais_legais", "almtec", "percentual", "pnp_consultar_percentual_tecnicos", True, ("almtec",), (), 50.0),
    _i("ALMPROF", "Percentual de Mateq em formação de professores", "legal", "percentuais_legais", "almprof", "percentual", "pnp_consultar_percentual_formacao_professores", True, ("almprof",), (), 20.0),
    _i("ALMEJA", "Percentual de Mateq em EJA/EPT", "legal", "percentuais_legais", "almeja", "percentual", "pnp_consultar_percentual_proeja", True, ("almeja",), (), 10.0),
    _i("ALVTEC", "Percentual de vagas em EPTNM", "legal", "percentuais_legais", "alvtec", "percentual", "pnp_consultar_percentual_vagas_tecnicos", True, ("alvtec",)),
    _i("ALVPROF", "Percentual de vagas em formação de professores", "legal", "percentuais_legais", "alvprof", "percentual", "pnp_consultar_percentual_vagas_formacao_professores", True, ("alvprof",)),
    _i("ALVEJA", "Percentual de vagas em EJA/EPT", "legal", "percentuais_legais", "alveja", "percentual", "pnp_consultar_percentual_vagas_proeja", True, ("alveja",)),
    _i("ALGN", "Percentual de cursos de graduação noturna presencial", "legal", "vagas_noturnas", "algn", "percentual", "pnp_consultar_percentual_cursos_graduacao_noturna", True, ("algn",)),
    _i("ALMGN", "Percentual de Mateq de graduação noturna presencial", "legal", "vagas_noturnas", "almgn", "percentual", "pnp_consultar_percentual_mateq_graduacao_noturna", True, ("almgn",)),
    _i("ALVGN", "Percentual de vagas de graduação noturna presencial", "legal", "vagas_noturnas", "alvgn", "percentual", "pnp_consultar_percentual_vagas_graduacao_noturna", True, ("alvgn",)),
    _i("ALVCN", "Percentual de vagas em cursos noturnos presenciais", "legal", "vagas_noturnas", "alvcn", "percentual", "pnp_consultar_vagas_noturnas", True, ("vagas_noturnas", "alvcn")),
    _i("ENRIV", "Relação inscritos/vaga", "legal", "inscritos_vagas", "relacao_inscrito_vaga", "razao", "pnp_consultar_inscritos_vagas", True, ("inscritos_vagas",)),
    _i("RESERVA", "Reserva de vagas e matrículas (Lei 14.723)", "legal", "reserva_vagas", "vagas_regulares", "vagas", "pnp_consultar_reserva_vagas", True, ("alvac", "alvres", "alvtg", "almac", "almres", "almtg"), ("tipo_reserva",)),
    _i("GACM", "Gastos correntes por matrícula equivalente", "gastos", "gastos", "gasto_por_mateq", "reais_por_mateq", "pnp_consultar_gasto_por_mateq", True, ("gacm",)),
    _i("GAT", "Gastos totais", "gastos", "gastos", "gastos_totais", "reais", "pnp_consultar_gastos_totais", True, ("gat",)),
    _i("GAC", "Gastos correntes", "gastos", "gastos", "gastos_correntes", "reais", "pnp_consultar_gastos_correntes", True, ("gac",)),
    _i("GAPE", "Gastos de pessoal", "gastos", "gastos", "gastos_pessoal", "reais", "pnp_consultar_gastos_pessoal", True, ("gape",)),
    _i("GAOC", "Outros custeios", "gastos", "gastos", "gastos_custeio", "reais", "pnp_consultar_gastos_custeio", True, ("gaoc",)),
    _i("GAIV", "Investimentos e inversões", "gastos", "gastos", "gastos_investimento", "reais", "pnp_consultar_gastos_investimento", True, ("gaiv",)),
    _i("GAIP", "Inativos e pensionistas", "gastos", "gastos", "gastos_inativos", "reais", "pnp_consultar_gastos_inativos", True, ("gaip",)),
    _i("GAPRE", "Precatórios", "gastos", "gastos", "gastos_precatorios", "reais", "pnp_consultar_gastos_precatorios", True, ("gapre",)),
    _i("PEDO", "Número de pessoas docentes", "pessoas", "docentes", "n_docentes", "pessoas", "pnp_consultar_docentes", True, ("docentes",), ("titulacao",)),
    _i("PEDE", "Número de pessoas docentes efetivas", "pessoas", "docentes", "n_docentes_efetivos", "pessoas", "pnp_consultar_docentes_efetivos", True, ("docentes_efetivos",)),
    _i("PETAE", "Número de pessoas TAE", "pessoas", "tae", "n_tae", "pessoas", "pnp_consultar_tae", True, ("tae",), ("titulacao",)),
    _i("PES", "Número de pessoas servidoras", "pessoas", "docentes", "n_servidores", "pessoas", "pnp_consultar_servidores", True, ("servidores",)),
    _i("PETCD", "Índice de titulação do corpo docente efetivo", "pessoas", "docentes", "itcd", "indice", "pnp_consultar_itcd", True, ("itcd", "petcd")),
    _i("PROFE", "Professor-equivalente", "pessoas", "rap", "profeq", "professores_equivalentes", "pnp_consultar_profeq", False, ("profeq",)),
    _i("DOTACAO", "Dotação atualizada", "tesouro", "orcamento", "dotacao_atualizada", "reais", "pnp_consultar_dotacao", True, (), ("resultado_primario", "relacao_orgao")),
    _i("EMPENHO", "Despesa empenhada", "tesouro", "orcamento", "despesa_empenhada", "reais", "pnp_consultar_empenho", True, (), ("resultado_primario", "relacao_orgao")),
    _i("LIQUIDACAO", "Despesa liquidada", "tesouro", "orcamento", "despesa_liquidada", "reais", "pnp_consultar_liquidacao", True, (), ("resultado_primario", "relacao_orgao")),
    _i("PAGA", "Despesa paga", "tesouro", "orcamento", "despesa_paga", "reais", "pnp_consultar_despesa_paga", True, (), ("resultado_primario", "relacao_orgao")),
    _i("A_LIQUIDAR", "Empenho a liquidar", "tesouro", "orcamento", "empenhado_a_liquidar", "reais", "pnp_consultar_empenhado_a_liquidar", True, (), ("resultado_primario", "relacao_orgao")),
    _i("CREDITO", "Crédito disponível", "tesouro", "orcamento", "credito_disponivel", "reais", "pnp_consultar_credito_disponivel", True, (), ("resultado_primario", "relacao_orgao")),
    _i("COR_RACA", "Matrículas por cor/raça", "perfil", "perfil_discente", "n_matriculas", "matriculas", "pnp_consultar_cor_raca", False, (), ("cor_raca",)),
    _i("RENDA", "Matrículas por renda familiar", "perfil", "perfil_discente", "n_matriculas", "matriculas", "pnp_consultar_renda", False, (), ("renda_familiar",)),
    _i("SEXO", "Matrículas por sexo", "perfil", "perfil_discente", "n_matriculas", "matriculas", "pnp_consultar_sexo", False, (), ("sexo",)),
    _i("FAIXA_ETARIA", "Matrículas por faixa etária", "perfil", "perfil_discente", "n_matriculas", "matriculas", "pnp_consultar_faixa_etaria", False, (), ("faixa_etaria",)),
)

def get(chave: str) -> Indicador:
    k = chave.strip().lower()
    for i in INDICADORES_MVP:
        if i.codigo.lower() == k or k in i.aliases or i.tool == chave:
            return i
    from mcp_pnp.errors import PnpError
    raise PnpError("indicador_desconhecido", chave)


def listar(*, somente_oficial: bool = False) -> list[Indicador]:
    items = list(INDICADORES_MVP)
    if somente_oficial:
        items = [i for i in items if i.oficial]
    return items
```

A assinatura de `_i` é a do dataclass: após `oficial` vêm `aliases`, `extra_filtros`, `meta`. Para indicadores com `meta` e sem extras, passe `()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_registry.py -v`

Expected: PASS. Se `ALRAPE` quebrar por ordem de argumentos, ajuste só essa entrada.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_pnp/registry.py tests/test_registry.py
git commit -m "feat: register official PNP indicator catalog for Extrator MVP"
```

---

### Task 4: Schema SQLite e queries

**Files:**
- Create: `src/mcp_pnp/db/__init__.py`
- Create: `src/mcp_pnp/db/schema.py`
- Create: `src/mcp_pnp/db/queries.py`
- Create: `tests/conftest.py`
- Create: `tests/test_queries.py`

- [ ] **Step 1: Write fixture + failing test**

```python
# tests/conftest.py
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
```

```python
# tests/test_queries.py
import pytest
from mcp_pnp.db.queries import consultar
from mcp_pnp.errors import PnpError
from mcp_pnp.registry import get


def test_filtra_instituicao(db_path):
    body = consultar(db_path, get("ENME"), {"instituicao": "ifmg", "ano": 2025})
    assert body["fonte"] == "oficial"
    assert body["indicador"] == "ENME"
    assert body["total_registros"] == 1
    assert body["registros"][0]["instituicao_sigla"] == "IFMG"
    assert body["registros"][0]["valor"] == 80.5


def test_base_vazia(tmp_path):
    missing = tmp_path / "nope.sqlite"
    with pytest.raises(PnpError) as ei:
        consultar(missing, get("ENME"), {})
    assert ei.value.codigo == "base_vazia"


def test_ano_omitido_usa_ultimo(db_path):
    body = consultar(db_path, get("ENM"), {"instituicao": "IFMG"})
    assert body["filtros_aplicados"]["ano"] == 2025
    assert body["aviso"] and "último ano" in body["aviso"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_queries.py -v`

Expected: FAIL with missing module

- [ ] **Step 3: Write schema + queries**

```python
# src/mcp_pnp/db/__init__.py
```

```python
# src/mcp_pnp/db/schema.py
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
    unidade TEXT
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
    "situacao_matricula": f"CREATE TABLE IF NOT EXISTS situacao_matricula ({DIM}, categoria_situacao TEXT, nome_situacao TEXT, fluxo_retido TEXT, n_matriculas REAL)",
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
```

```python
# src/mcp_pnp/db/queries.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from mcp_pnp.config import Settings
from mcp_pnp.envelope import ok
from mcp_pnp.errors import PnpError
from mcp_pnp.registry import Indicador

DIM_FILTERS = {
    "instituicao": "instituicao_sigla",
    "unidade": "unidade",
    "uf": "uf",
    "regiao": "regiao",
    "municipio": "municipio",
    "organizacao_academica": "organizacao_academica",
    "ano": "ano",
}


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise PnpError("base_vazia")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    n = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='edicoes'"
    ).fetchone()[0]
    if n == 0:
        conn.close()
        raise PnpError("base_vazia")
    return conn


def ultimo_ano(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(ano) FROM edicoes").fetchone()
    if row is None or row[0] is None:
        raise PnpError("base_vazia")
    return int(row[0])


def consultar(
    db_path: Path,
    indicador: Indicador,
    filtros: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    limite = int(filtros.get("limite") or settings.max_registros)
    offset = int(filtros.get("offset") or 0)
    if limite < 1 or limite > 500:
        raise PnpError("limite_invalido")

    conn = _connect(db_path)
    try:
        applied = dict(filtros)
        aviso = None
        if applied.get("ano") is None:
            applied["ano"] = ultimo_ano(conn)
            aviso = f"Ano omitido; usando o último ano carregado ({applied['ano']})."

        where = []
        params: list[Any] = []
        mapping = dict(DIM_FILTERS)
        for extra in indicador.extra_filtros:
            mapping[extra] = extra
        for key, col in mapping.items():
            val = applied.get(key)
            if val is None or key in {"limite", "offset"}:
                continue
            if key == "instituicao":
                where.append(f"UPPER({col}) = UPPER(?)")
            else:
                where.append(f"{col} = ?")
            params.append(val)

        sql = (
            f"SELECT * FROM {indicador.tabela} "
            + ("WHERE " + " AND ".join(where) if where else "")
            + " LIMIT ? OFFSET ?"
        )
        params.extend([limite + 1, offset])
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise PnpError("sem_registros", str(exc)) from exc

        truncado = len(rows) > limite
        rows = rows[:limite]
        registros = []
        for row in rows:
            item = dict(row)
            item["valor"] = item.get(indicador.coluna)
            registros.append(item)

        ed = conn.execute(
            "SELECT edicao_pnp FROM edicoes WHERE ano = ?", (applied["ano"],)
        ).fetchone()
        return ok(
            fonte="oficial",
            edicao_pnp=ed["edicao_pnp"] if ed else None,
            ano=applied["ano"],
            indicador=indicador.codigo,
            unidade_medida=indicador.unidade_medida,
            filtros_aplicados={k: v for k, v in applied.items() if v is not None},
            registros=registros,
            truncado=truncado,
            aviso=aviso,
        )
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_queries.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_pnp/db tests/conftest.py tests/test_queries.py
git commit -m "feat: add SQLite schema and filtered indicator queries"
```

---

### Task 5: Ingest (CSV do Extrator, HTTP mockado)

**Files:**
- Create: `src/mcp_pnp/ingest/__init__.py`
- Create: `src/mcp_pnp/ingest/catalog.py`
- Create: `src/mcp_pnp/ingest/client.py`
- Create: `src/mcp_pnp/ingest/loader.py`
- Create: `src/mcp_pnp/ingest/sync.py`
- Create: `tests/fixtures/oferta.csv`
- Create: `tests/test_ingest.py`

O HTML de `/pnpquery/{id}` **não** é fonte (só 100 linhas). O client tenta, nesta ordem, e fica com o primeiro CSV cujo header tenha `Ano` e `Instituicao` (ou `Instituição`):

1. `{base}/pnpquery/{id}/csv`
2. `{base}/pnpquery/{id}?format=csv`
3. `{base}/api/pnpquery/{id}/download`

- [ ] **Step 1: Write fixture + failing test**

```csv
Ano,Região,UF,Estado,Organização Acadêmica PNP,Instituicao,Instituição (Nome),nomeUnidadeRecente,Número de cursos,Número de Matrículas,Matrícula Equivalente | Geral,Número de vagas,Número de inscritos,Número de ingressantes,Número de concluintes
2025,Sudeste,MG,Minas Gerais,Instituto Federal,IFMG,Instituto Federal de Minas Gerais,Campus BH,2,100,80.5,50,200,40,30
```

```python
# tests/test_ingest.py
from pathlib import Path

import httpx
import pytest

from mcp_pnp.config import Settings
from mcp_pnp.db.queries import consultar
from mcp_pnp.db.schema import apply_schema
from mcp_pnp.ingest.client import ExtratorClient
from mcp_pnp.ingest.loader import load_csv
from mcp_pnp.ingest.sync import sync
from mcp_pnp.registry import get


def test_client_escolhe_csv(tmp_path: Path):
    csv = (Path(__file__).parent / "fixtures" / "oferta.csv").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/csv"):
            return httpx.Response(200, text=csv, headers={"content-type": "text/csv"})
        return httpx.Response(404, text="no")

    transport = httpx.MockTransport(handler)
    client = ExtratorClient("https://extrator.test", transport=transport)
    text = client.download_csv(3)
    assert "Número de Matrículas" in text


def test_loader_normaliza_e_consulta(tmp_path: Path, monkeypatch):
    db = tmp_path / "pnp.sqlite"
    import sqlite3
    conn = sqlite3.connect(db)
    apply_schema(conn)
    conn.close()
    raw = (Path(__file__).parent / "fixtures" / "oferta.csv").read_text(encoding="utf-8")
    load_csv(db, "oferta", raw, ano_edicao=2025, edicao_pnp="2026")
    body = consultar(db, get("ENME"), {"instituicao": "IFMG", "ano": 2025})
    assert body["registros"][0]["valor"] == 80.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`

Expected: FAIL missing module

- [ ] **Step 3: Implement catalog, client, loader, sync**

```python
# src/mcp_pnp/ingest/catalog.py
EXTRATOR_CONJUNTOS = (
    {"id": 1, "tabela": "orcamento"},
    {"id": 3, "tabela": "oferta"},
    {"id": 4, "tabela": "situacao_matricula"},
    {"id": 5, "tabela": "perfil_discente"},
    {"id": 6, "tabela": "percentuais_legais"},
    {"id": 7, "tabela": "reserva_vagas"},
    {"id": 8, "tabela": "vagas_noturnas"},
    {"id": 9, "tabela": "inscritos_vagas"},
    {"id": 10, "tabela": "evasao"},
    {"id": 11, "tabela": "eficiencia"},
    {"id": 12, "tabela": "rap"},
    {"id": 13, "tabela": "verticalizacao"},
    {"id": 14, "tabela": "ocupacao"},
    {"id": 15, "tabela": "docentes"},
    {"id": 16, "tabela": "tae"},
    {"id": 18, "tabela": "gastos"},
)
```

```python
# src/mcp_pnp/ingest/client.py
from __future__ import annotations

import httpx

from mcp_pnp.errors import PnpError

SUFIXOS = ("/csv", "?format=csv", "/download")


class ExtratorClient:
    def __init__(self, base: str, transport: httpx.BaseTransport | None = None) -> None:
        self.base = base.rstrip("/")
        self._transport = transport

    def download_csv(self, query_id: int) -> str:
        with httpx.Client(transport=self._transport, timeout=60.0, follow_redirects=True) as http:
            last = None
            for suf in SUFIXOS:
                url = f"{self.base}/pnpquery/{query_id}{suf}"
                resp = http.get(url)
                last = resp
                if resp.status_code == 200 and _parece_csv(resp.text):
                    return resp.text
        detalhe = f"query {query_id} status={getattr(last, 'status_code', '?')}"
        raise PnpError("sync_falhou", detalhe)


def _parece_csv(text: str) -> bool:
    head = text.splitlines()[0] if text else ""
    return ("Ano" in head) and ("Instituicao" in head or "Instituição" in head)
```

No `loader.py`, mapeie headers conhecidos do Extrator para colunas do schema. Implemente `load_csv(db_path, tabela, csv_text, ano_edicao, edicao_pnp)`:

- parse com `csv.DictReader` (`delimiter=','`; se houver `;` no header, use `;`)
- normalize chave com um dicionário `HEADER_MAP` contendo pelo menos:

```python
HEADER_MAP = {
    "Ano": "ano",
    "Região": "regiao",
    "UF": "uf",
    "Estado": "estado",
    "Organização Acadêmica PNP": "organizacao_academica",
    "Instituicao": "instituicao_sigla",
    "Instituição (Nome)": "instituicao_nome",
    "nomeUnidadeRecente": "unidade",
    "Número de cursos": "n_cursos",
    "Número de Matrículas": "n_matriculas",
    "Matrícula Equivalente | Geral": "mateq",
    "Número de vagas": "n_vagas",
    "Número de inscritos": "n_inscritos",
    "Número de ingressantes": "n_ingressantes",
    "Número de concluintes": "n_concluintes",
}
```

- converta números trocando `,` por `.`
- `DELETE FROM tabela` + insert em transação
- atualize `edicoes` para `ano_edicao`

`sync.py`:

```python
def sync(settings, client: ExtratorClient | None = None) -> dict:
    from datetime import datetime, timezone
    import sqlite3
    from mcp_pnp.db.schema import apply_schema
    from mcp_pnp.ingest.catalog import EXTRATOR_CONJUNTOS

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    apply_schema(conn)
    conn.execute(
        "INSERT INTO sync_log(iniciado_em, status, detalhe) VALUES (?, 'ok', ?)",
        (datetime.now(timezone.utc).isoformat(), "inicio"),
    )
    conn.commit()
    conn.close()
    client = client or ExtratorClient(settings.extrator_base)
    falhas = []
    for item in EXTRATOR_CONJUNTOS:
        try:
            raw = client.download_csv(item["id"])
            (settings.cache_dir / f"{item['tabela']}.csv").write_text(raw, encoding="utf-8")
            load_csv(settings.db_path, item["tabela"], raw, ano_edicao=2025, edicao_pnp="2026")
        except Exception as exc:  # noqa: BLE001 — registra e segue o próximo conjunto
            falhas.append(f"{item['tabela']}: {exc}")
    if falhas and len(falhas) == len(EXTRATOR_CONJUNTOS):
        from mcp_pnp.errors import PnpError
        raise PnpError("sync_falhou", "; ".join(falhas))
    return {"ok": True, "falhas": falhas}
```

O ano/edição no MVP pode ser lido da coluna `ano` do próprio CSV (max) e `edicao_pnp = str(max_ano + 1)` (PNP 2026 = ano-base 2025). Faça isso no `load_csv` em vez de hardcodar se o teste passar com os argumentos explícitos.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_pnp/ingest tests/fixtures/oferta.csv tests/test_ingest.py
git commit -m "feat: ingest Extrator CSVs into SQLite with mocked HTTP"
```

---

### Task 6: FastMCP server, tools, CLI

**Files:**
- Create: `src/mcp_pnp/tools.py`
- Create: `src/mcp_pnp/server.py`
- Create: `src/mcp_pnp/cli.py`
- Create: `src/mcp_pnp/__main__.py`
- Create: `src/mcp_pnp/glossary.py`
- Create: `src/mcp_pnp/analysis.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tools.py
from mcp_pnp.registry import INDICADORES_MVP
from mcp_pnp.server import create_server


def test_tools_mvp_registradas():
    mcp = create_server()
    names = {t.name for t in mcp.list_tools()}
    for ind in INDICADORES_MVP:
        assert ind.tool in names, ind.tool
    for extra in (
        "pnp_listar_edicoes",
        "pnp_listar_instituicoes",
        "pnp_listar_unidades",
        "pnp_listar_indicadores",
        "pnp_comparar",
        "pnp_evolucao",
        "pnp_ranking",
        "pnp_estatisticas",
        "pnp_glossario",
        "pnp_status_base",
        "pnp_sincronizar",
    ):
        assert extra in names
    assert "pnp_consultar_igc" not in names
    assert "pnp_consultar_acordos_pesquisa" not in names


def test_glossario_enme():
    from mcp_pnp.glossary import explicar
    g = explicar("ENME")
    assert "equivalente" in g["definicao"].lower()
```

A API exata do FastMCP para listar tools varia (`mcp.list_tools()` vs `mcp._tool_manager.list_tools()`). No teste, use o que a versão instalada expuser; se `list_tools` for coroutine, rode com `pytest-asyncio` ou `anyio.run`. Se o nome do método for outro, adapte o teste ao objeto real **sem** registrar IGC/pesquisa.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`

Expected: FAIL missing `create_server`

- [ ] **Step 3: Implement tools, analysis, glossary, server, CLI**

`glossary.py` — dicionário com pelo menos: `ENME`, `ENM`, `ENEMA`, `ENUND`, `ENIEA`, `ENEVA`, `ENEC`, `ALMTEC`, `ALMPROF`, `ALMEJA`, `ALRMP`, `ALRAPE`, `GACM`, `PETCD`, `matricula_atendida`. Cada entrada: `definicao`, `formula`, `fonte`, `ressalva`.

`analysis.py` — quatro funções que leem via `consultar` e devolvem envelope `fonte="derivada"`:

- `comparar(db, indicador, esquerda: dict, direita: dict)` — diferença absoluta e %
- `evolucao(db, indicador, filtros, ano_inicio, ano_fim)` — uma consulta por ano
- `ranking(db, indicador, nivel, ordem, ano, top)`
- `estatisticas(db, indicador, filtros, estatistica)` — media|mediana|percentil|participacao

`tools.py` — para cada `Indicador` do registry, registre uma tool FastMCP cujo nome é `ind.tool`, descrição em pt-BR contendo a sigla e um exemplo (“Qual a ENME do IFMG em 2025?”). Parâmetros comuns: `ano`, `instituicao`, `unidade`, `uf`, `regiao`, `organizacao_academica`, `limite`, `offset` + `extra_filtros`. Corpo: `consultar(settings.db_path, ind, filtros)` e, em `PnpError`, `return err.as_dict()`.

Tools extras (não saem do registry):

- `pnp_listar_edicoes` → `SELECT * FROM edicoes`
- `pnp_listar_instituicoes` → distinct de `oferta`
- `pnp_listar_unidades` → exige `instituicao`
- `pnp_listar_indicadores` → `listar()`
- `pnp_glossario` → `explicar(termo)`
- `pnp_status_base` → path, edições, contagem por tabela
- `pnp_sincronizar` → `sync(settings)`
- as quatro de análise

`server.py`:

```python
from fastmcp import FastMCP
from mcp_pnp.tools import register_all

def create_server() -> FastMCP:
    mcp = FastMCP("pnp")
    register_all(mcp)
    return mcp
```

Resources: `pnp://glossario/{termo}`, `pnp://indicadores`.  
Prompts: `diagnostico_gestao`, `comparar_pares`, `checar_percentuais_legais`.

`cli.py`:

```python
import sys
from mcp_pnp.server import create_server
from mcp_pnp.config import Settings
from mcp_pnp.ingest.sync import sync

def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["sync"]:
        print(sync(Settings.from_env()))
        return
    create_server().run()
```

`__main__.py`: `from mcp_pnp.cli import main; main()`

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_tools.py tests/test_queries.py tests/test_ingest.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mcp_pnp/tools.py src/mcp_pnp/server.py src/mcp_pnp/cli.py src/mcp_pnp/__main__.py src/mcp_pnp/glossary.py src/mcp_pnp/analysis.py tests/test_tools.py
git commit -m "feat: expose Extrator MVP indicators as Portuguese MCP tools"
```

---

### Task 7: README e config de clientes

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README** (sem teste de código; verificação = arquivo existe e contém os blocos abaixo)

Conteúdo mínimo:

```markdown
# MCP PNP

Servidor MCP da Plataforma Nilo Peçanha (indicadores oficiais de gestão).

## Instalação

```powershell
cd D:\OneDrive\Documentos\devProjects\projects\MCP_PNP
pip install -e ".[dev]"
mcp-pnp sync
```

## Grok (`~/.grok/config.toml`)

```toml
[mcp_servers.pnp]
command = "mcp-pnp"
enabled = true
```

## Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "pnp": { "command": "mcp-pnp" }
  }
}
```

Primeiro uso: `pnp_status_base`. Perguntas: “Qual a ENME do IFMG em 2025?”, “A ALMTEC está nos 50%?”, “Compare a ALRMP do IFMG com a Rede.”
```

- [ ] **Step 2: Commit**

```bash
git add README.md docs/superpowers/specs/2026-08-18-mcp-pnp-design.md
git commit -m "docs: add MCP PNP install and client configuration"
```

---

## Self-review

1. **Spec coverage (MVP Extrator):** registry + tools cobrem EN*, AL* (exceto desagregar ALMAC/ALVRES em tools próprias — ficam em `pnp_consultar_reserva_vagas`), GA*, PE*, Tesouro 6, perfil, análise, glossário, sync. Pesquisa/extensão/polos/sustentabilidade/INEP explicitamente fora (teste `test_tools_mvp_registradas`).
2. **Placeholders:** nenhum TBD. URL do CSV tem três sufixos concretos e teste mockado.
3. **Tipos:** `Indicador`, `Settings`, `PnpError`, `consultar(db_path, indicador, filtros)` usados iguais em todas as tasks.

---
