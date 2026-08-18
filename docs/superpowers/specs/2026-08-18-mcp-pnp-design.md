# MCP PNP — Plataforma Nilo Peçanha

Data: 2026-08-18  
Idioma do produto: português brasileiro (nomes de tools, descrições, campos de resposta e mensagens de erro)  
Status: aprovado em brainstorming; aguardando review do spec antes do plano de implementação

## Problema

Gestores da Rede Federal de Educação Profissional, Científica e Tecnológica (RFEPCT) consultam a PNP por Power BI e pelo Extrator CSV. Isso não serve para agentes em Grok, Claude e similares: não há API REST oficial, o painel não é consultável por ferramenta, e o Extrator só mostra 100 linhas na tela.

O MCP PNP expõe os **indicadores oficiais de gestão** da PNP como ferramentas MCP, em português, para diagnóstico institucional em toda a Rede (sem instituição padrão).

## Público e sucesso

- **Público:** gestores de IF/CEFET/escolas vinculadas, SETEC e áreas de planejamento/controle.
- **Perguntas-alvo:** “qual a RAP do IFMG em 2025?”, “a evasão está acima da Rede?”, “cumpre os 50% técnicos?”, “como evoluiu a Mateq desde 2021?”, “quanto gasta por Mateq?”.
- **Sucesso:** o agente responde com o número oficial da PNP, a edição/ano, a definição do indicador e, quando pedido, comparação, ranking ou série histórica — sem inventar dado ausente e sem recalcular indicador oficial.

## Fora de escopo (esta versão)

- Recalcular indicadores a partir de microdados (risco de divergir do número oficial).
- Portal `pnp.mec.gov.br` (oferta “quero estudar”, Rede Integra).
- Scraping do Power BI como fonte.
- Instituição padrão configurável.
- Transporte HTTP/SSE (fica preparado na estrutura; não é entrega do MVP).
- Autenticação, multi-tenant e hospedagem compartilhada.
- UI web.

## Decisões

1. **Fonte da verdade:** CSVs do Extrator PNP (`https://moduloextratorpnp.mec.gov.br/`), já calculados pelo modelo semântico oficial. Não se recalcula evasão, RAP, eficiência, percentuais legais nem gasto por Mateq.
2. **Loja local:** SQLite. Consultas leem só a base local. Sem fallback online na consulta.
3. **Stack:** Python 3.12+, FastMCP (stdio no MVP; o mesmo objeto de servidor deve poder subir HTTP/SSE depois sem reescrever tools).
4. **Granularidade:** uma tool por indicador/recorte nomeável (56 tools). Filtros (ano, instituição, campus, tipo de curso) não viram tool.
5. **Análise derivada:** `pnp_comparar`, `pnp_evolucao`, `pnp_ranking` e `pnp_estatisticas` existem, mas toda resposta derivada leva `fonte: derivada`.
6. **Rede inteira:** sem `PNP_INSTITUICAO` padrão. Comparações entre IFs entram no MVP.
7. **Idioma:** tools, schemas, descrições e erros em pt-BR. Código e identificadores internos em inglês (`snake_case`).
8. **Sync:** tool `pnp_sincronizar` + CLI `mcp-pnp sync`. Consulta com base vazia falha com instrução para sincronizar.

## Arquitetura

```
Cliente MCP (Grok, Claude, …)
        │  stdio (MVP)
        ▼
   FastMCP server
        │
        ├─ tools pnp_*          (só leem SQLite, exceto pnp_sincronizar)
        ├─ resources pnp://     (glossário, metodologia, catálogo)
        └─ prompts              (diagnóstico, pares, percentuais legais)
                │
                ▼
        query layer (filtros comuns + envelope JSON)
                │
                ▼
        SQLite  data/pnp.sqlite
                ▲
                │
        ingest (httpx)  ←  Extrator PNP (CSV oficial)
```

Pacote: `mcp_pnp`. Entrada: `python -m mcp_pnp`. Config por env:

| variável | padrão | função |
|---|---|---|
| `PNP_DB_PATH` | `data/pnp.sqlite` | caminho do SQLite |
| `PNP_CACHE_DIR` | `data/cache` | CSVs baixados |
| `PNP_EXTRATOR_BASE` | `https://moduloextratorpnp.mec.gov.br` | origem |
| `PNP_MAX_REGISTROS` | `200` | teto por resposta (máx. 500) |

## Componentes

| unidade | responsabilidade | depende de |
|---|---|---|
| `server.py` | registra tools, resources, prompts; stdio | tools, resources |
| `ingest/catalog.py` | mapa query_id Extrator → tabela SQLite → tools | — |
| `ingest/client.py` | baixa CSV (não a tabela HTML de 100 linhas) | catalog, httpx |
| `ingest/loader.py` | valida colunas, normaliza dimensões, upsert | client, db |
| `db/schema.py` | DDL, metadados (`edicoes`, `sync_log`, `indicadores`) | — |
| `db/queries.py` | SELECT parametrizado + filtros comuns | schema |
| `tools/` | um módulo por família; thin wrappers | queries, envelope |
| `analysis.py` | comparar, evolução, ranking, estatística | queries |
| `glossary.py` | verbetes da Portaria 146/2021 e do site PNP | — |
| `envelope.py` | JSON padrão de resposta | — |

Cada módulo de tool faz uma coisa: montar o SELECT daquela métrica. Não há um mega-dispatcher com 50 ramos.

## Modelo de dados

Uma tabela bruta por conjunto do Extrator (colunas originais preservadas) + colunas normalizadas de dimensão, sempre que existirem no CSV:

- `ano` INTEGER
- `regiao` TEXT
- `uf` TEXT
- `estado` TEXT
- `organizacao_academica` TEXT
- `instituicao_sigla` TEXT
- `instituicao_nome` TEXT
- `unidade` TEXT  (`nomeUnidadeRecente`)

Tabelas de metadados:

- `edicoes(ano, edicao_pnp, sincronizado_em, n_linhas, checksum_csv)`
- `sync_log(id, iniciado_em, status, detalhe)`
- `indicadores(codigo, nome, familia, tabela_origem, coluna_metrica, unidade_medida, oficial)`

Catálogo de ingestão (query IDs confirmados no Extrator 2.3.0):

| id | conjunto Extrator | tabela SQLite | tools que leem |
|---|---|---|---|
| 1 | Panorama orçamentário | `orcamento` | dotação, empenho, liquidação, despesa paga, restos a pagar, crédito disponível |
| 2 | Cargos da carreira | `cargos` | cargos |
| 3 | Curso, matrícula e oferta | `oferta` | cursos, matrículas, mateq, vagas, inscritos, ingressantes, concluintes |
| 4 | Situação matrícula | `situacao_matricula` | em curso, evadidos, retidos (concluintes desta tabela reforçam a tool de concluintes quando o recorte for situação) |
| 5 | Cor/raça, renda, sexo, faixa etária | `perfil_discente` | cor_raca, renda, sexo, faixa_etaria |
| 6 | Percentuais legais | `percentuais_legais` | % técnicos, % formação de professores, % PROEJA |
| 7 | Reserva de vagas | `reserva_vagas` | reserva de vagas |
| 8 | Oferta de vagas noturnas | `vagas_noturnas` | vagas noturnas |
| 9 | Relação inscritos/vagas | `inscritos_vagas` | inscritos/vaga |
| 10 | Taxa de evasão | `evasao` | evasão |
| 11 | Eficiência acadêmica | `eficiencia` | eficiência acadêmica |
| 12 | Relação aluno/professor (RAP) | `rap` | RAP, professor-equivalente |
| 13 | Índice de verticalização | `verticalizacao` | verticalização |
| 14 | Taxa de ocupação | `ocupacao` | ocupação |
| 15 | Titulação docente | `docentes` | docentes, ITCD, servidores |
| 16 | TAE por nível | `tae` | TAE |
| 18 | Indicadores de gastos | `gastos` | gasto por Mateq e decomposições |

A implementação deve descobrir a URL real de download do CSV de cada `/pnpquery/{id}` (a página HTML não é fonte). O contrato encontrado fica em `ingest/catalog.py`, não espalhado nas tools.

Anos: todas as edições presentes no CSV oficial, inclusive série histórica (o Extrator atual já cobre 2017–2025 em vários conjuntos). Não filtrar “só o último ano” no ingest.

## Contrato das tools

### Envelope de resposta (todas as `pnp_consultar_*`, análise e listagens)

```json
{
  "fonte": "oficial",
  "edicao_pnp": "2025",
  "ano": 2025,
  "indicador": "rap",
  "unidade_medida": "razao",
  "filtros_aplicados": {"instituicao": "IFMG", "ano": 2025},
  "total_registros": 18,
  "truncado": false,
  "registros": [],
  "aviso": null
}
```

- `fonte` é `oficial` quando o valor veio da coluna do Extrator; `derivada` quando foi média, percentil, variação ou ranking calculado no MCP.
- Sem registro: HTTP-equivalente de erro de tool (ver Erros). Não devolver lista vazia fingindo sucesso silencioso, exceto em listagens cujo resultado legítimo é vazio (ex.: filtro de UF sem IF — aí `total_registros: 0` e `aviso` explicando).

### Filtros comuns das consultoras

`ano` (int, opcional — se omitido, usa o último ano carregado e declara isso em `filtros_aplicados`), `instituicao` (sigla, case-insensitive), `unidade`, `uf`, `regiao`, `organizacao_academica`, `limite` (default 200, max 500), `offset`.

Filtros extras só quando a tabela tiver a coluna: `tipo_curso`, `tipo_oferta`, `modalidade`, `turno`, `eixo`.

### Catálogo (56)

**Descoberta**

| tool | faz |
|---|---|
| `pnp_listar_edicoes` | anos na base, edição PNP, data do sync |
| `pnp_listar_instituicoes` | sigla, nome, tipo; filtros região/UF/organização |
| `pnp_listar_unidades` | campi de uma instituição (instituição obrigatória) |
| `pnp_listar_indicadores` | código, nome, família, se é oficial |

**Oferta e volume**

| tool | métrica oficial |
|---|---|
| `pnp_consultar_cursos` | número de cursos / linhas de oferta |
| `pnp_consultar_matriculas` | número de matrículas (Mat) |
| `pnp_consultar_mateq` | matrícula-equivalente |
| `pnp_consultar_vagas` | vagas |
| `pnp_consultar_inscritos` | inscritos |
| `pnp_consultar_ingressantes` | ingressantes |
| `pnp_consultar_concluintes` | concluintes |

**Situação**

| tool | métrica |
|---|---|
| `pnp_consultar_em_curso` | matrículas em curso |
| `pnp_consultar_evadidos` | evadidos; filtro `motivo` (abandono, desligamento, transferencia) |
| `pnp_consultar_retidos` | retidos / fluxo |

**Indicadores acadêmicos oficiais**

| tool | métrica |
|---|---|
| `pnp_consultar_evasao` | taxa de evasão |
| `pnp_consultar_eficiencia_academica` | eficiência acadêmica e componentes publicados na mesma tabela |
| `pnp_consultar_rap` | RAP e, na mesma linha oficial, Mateq RAP e professor-equivalente |
| `pnp_consultar_verticalizacao` | índice de verticalização |
| `pnp_consultar_ocupacao` | taxa de ocupação |

**Percentuais legais (Lei 11.892 e recortes PNP)**

| tool | métrica |
|---|---|
| `pnp_consultar_percentual_tecnicos` | Mateq técnicos e participação |
| `pnp_consultar_percentual_formacao_professores` | Mateq formação de professores |
| `pnp_consultar_percentual_proeja` | Mateq PROEJA |
| `pnp_consultar_vagas_noturnas` | vagas noturnas e % |
| `pnp_consultar_reserva_vagas` | ampla vs cota |
| `pnp_consultar_inscritos_vagas` | relação inscritos/vaga |

**Orçamento**

| tool | métrica |
|---|---|
| `pnp_consultar_dotacao` | dotação atualizada |
| `pnp_consultar_empenho` | despesa empenhada |
| `pnp_consultar_liquidacao` | despesa liquidada |
| `pnp_consultar_despesa_paga` | despesa paga |
| `pnp_consultar_restos_a_pagar` | liq & RP / restos |
| `pnp_consultar_credito_disponivel` | crédito disponível |

Todas aceitam filtro `resultado_primario` (obrigatorio, discricionario, emenda_bancada, emenda_individual, financeiro) e `relacao_orgao` quando a coluna existir.

**Gastos**

| tool | métrica |
|---|---|
| `pnp_consultar_gasto_por_mateq` | gastos correntes por Mateq |
| `pnp_consultar_gastos_totais` | gastos totais |
| `pnp_consultar_gastos_correntes` | gastos correntes |
| `pnp_consultar_gastos_pessoal` | pessoal |
| `pnp_consultar_gastos_custeio` | outros custeios |
| `pnp_consultar_gastos_investimento` | investimentos e inversões |
| `pnp_consultar_gastos_inativos` | inativos e pensionistas |
| `pnp_consultar_gastos_precatorios` | precatórios |

**Pessoas**

| tool | métrica |
|---|---|
| `pnp_consultar_docentes` | docentes efetivos e totais; filtro titulação |
| `pnp_consultar_tae` | TAE por titulação/nível |
| `pnp_consultar_cargos` | carreira (PCCTAE etc.) |
| `pnp_consultar_servidores` | total de servidores |
| `pnp_consultar_profeq` | professor-equivalente (tabela RAP) |
| `pnp_consultar_itcd` | ITCD |

**Perfil**

| tool | dimensão |
|---|---|
| `pnp_consultar_cor_raca` | cor/raça |
| `pnp_consultar_renda` | renda familiar |
| `pnp_consultar_sexo` | sexo |
| `pnp_consultar_faixa_etaria` | faixa etária |

**Análise (sempre `fonte: derivada`)**

| tool | faz |
|---|---|
| `pnp_comparar` | um indicador entre A e B (instituição, UF, Rede, organização acadêmica). Parâmetros: `indicador`, `esquerda`, `direita`, `ano` |
| `pnp_evolucao` | série anual + variação YoY. Parâmetros: `indicador`, filtros, `ano_inicio`, `ano_fim` |
| `pnp_ranking` | ordena instituições ou unidades. Parâmetros: `indicador`, `nivel` (instituicao\|unidade), `ordem` (asc\|desc), `ano`, `top` |
| `pnp_estatisticas` | média, mediana, percentil, desvio, participação % na Rede. Parâmetro `estatistica` |

Códigos de `indicador` nas tools de análise = código de `pnp_listar_indicadores` (ex.: `rap`, `evasao`, `mateq`, `gasto_por_mateq`).

**Glossário e operação**

| tool | faz |
|---|---|
| `pnp_glossario` | definição, fórmula, fonte (Sistec/Siape/Siafi), ressalva. Parâmetro `termo` |
| `pnp_status_base` | caminho do DB, edições, linhas por tabela, último sync |
| `pnp_sincronizar` | baixa CSVs, valida, recarrega SQLite. Parâmetro opcional `forcar` |

### Resources e prompts

- `pnp://glossario/{termo}`
- `pnp://metodologia`
- `pnp://indicadores`
- Prompts: `diagnostico_gestao`, `comparar_pares`, `checar_percentuais_legais`

## Fluxo de dados

1. Operador roda `mcp-pnp sync` ou o agente chama `pnp_sincronizar`.
2. Cliente HTTP baixa cada CSV do catálogo para `PNP_CACHE_DIR` (checksum).
3. Loader recusa CSV se faltar coluna obrigatória de dimensão (`ano`, `Instituicao`/`instituicao`) ou a coluna da métrica.
4. Transação: apaga/recarrega a tabela daquele conjunto; atualiza `edicoes` e `sync_log`. Falha em um conjunto não deixa tabela pela metade (rollback daquele conjunto); os demais já gravados permanecem e o log registra o conjunto falho.
5. Tool de consulta monta SELECT com placeholders, nunca interpola SQL.
6. Resposta passa pelo envelope. Agregações oficiais (soma de matrículas de vários campi quando o usuário pediu a instituição) são permitidas e continuam `fonte: oficial` se forem soma/contagem direta da coluna oficial. Média, percentil e posição de ranking são `derivada`.

Não há job em background no processo MCP. Sync é síncrono e deve informar progresso em `aviso` se passar de alguns segundos; timeout configurável (default 180s) devolve erro parcial com o que já estava na base.

## Erros

Mensagens em pt-BR, estáveis o bastante para o modelo agir:

| código | quando | o que dizer |
|---|---|---|
| `base_vazia` | SQLite inexistente ou sem `edicoes` | “Base local vazia. Execute pnp_sincronizar ou `mcp-pnp sync`.” |
| `ano_indisponivel` | ano pedido não carregado | listar anos disponíveis |
| `instituicao_desconhecida` | sigla não existe | sugerir `pnp_listar_instituicoes` |
| `unidade_desconhecida` | campus não bate | sugerir `pnp_listar_unidades` |
| `indicador_desconhecido` | código inválido em comparar/evolução | sugerir `pnp_listar_indicadores` |
| `sem_registros` | filtros sem linha | repetir filtros e sugerir alargar recorte |
| `sync_falhou` | Extrator indisponível / CSV inválido | conjunto, status HTTP ou coluna faltante |
| `limite_invalido` | limite > 500 ou < 1 | lembrar o teto |

Nunca completar número faltante com estimativa. Célula vazia no CSV oficial vira `null`, não zero.

## Testes

Pirâmide sem rede no CI:

1. **Envelope e filtros** — `tests/test_envelope.py`, `tests/test_filtros.py`.
2. **Queries com fixture** — SQLite temporário carregado de CSVs mínimos em `tests/fixtures/` (recorte de 2 instituições, 2 anos, 2 campi). Uma suíte por família de tools.
3. **Análise** — comparar IF vs Rede, YoY, ranking e percentil sobre a fixture; assert `fonte == derivada`.
4. **Glossário** — termos obrigatórios: `mateq`, `rap`, `evadidos`, `gastos_correntes`, `profeq`, `fech`, `fec`, `fcg`.
5. **Ingest unitário** — `client` e `loader` com HTTP mockado (resposta CSV fixa). Nenhum teste de CI bate no MEC.
6. **Contrato MCP** — lista as 56 tools, verifica nome em pt-BR e que cada uma declara o envelope.

Comando: `pytest`. Marcador `@pytest.mark.integration` reservado para um teste opcional de download real, não roda no default.

## Empacotamento e clientes

- Pacote instalável (`pip install -e .`) com script `mcp-pnp`.
- README com bloco JSON/TOML para Claude Desktop, Claude Code, Grok e Cursor apontando `command: mcp-pnp` (stdio).
- Primeiro uso documentado: instalar → `mcp-pnp sync` → configurar cliente → `pnp_status_base`.

## Riscos e mitigação

| risco | mitigação |
|---|---|
| Extrator muda URL ou colunas | catálogo isolado; loader valida header; teste de fixture quebra no CI |
| Cloudflare / instabilidade do MEC | sync explícito; consultas offline; erro `sync_falhou` |
| 56 tools saturam o modelo | nomes estáveis `pnp_consultar_<indicador>`; `pnp_listar_indicadores` como índice; descrições curtas com exemplo de pergunta |
| Confundir derivado com oficial | campo `fonte` obrigatório; descrições das 4 tools de análise repetem isso |
| HTML de 100 linhas no lugar do CSV | ingest recusa arquivo sem o header esperado ou com menos colunas que o catálogo |

## Review do spec

- Sem TBD/TODO.
- Um servidor, um domínio (indicadores oficiais de gestão). Não precisa decompor em vários projetos.
- “Indicador oficial” = coluna do Extrator. “Derivada” = cálculo do MCP. Sem ambiguidade.
- HTTP/SSE fica só como extensão futura da mesma instância FastMCP, sem design de auth nesta versão.
