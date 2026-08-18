# MCP PNP — Plataforma Nilo Peçanha

Data: 2026-08-18  
Idioma do produto: português brasileiro (nomes de tools, descrições, campos de resposta e mensagens de erro)  
Status: aprovado em brainstorming; catálogo alinhado ao Guia PNP Indicadores (https://pnp-ccv.github.io/guiapnp/) em 2026-08-18

## Problema

Gestores da Rede Federal de Educação Profissional, Científica e Tecnológica (RFEPCT) consultam a PNP por Power BI e pelo Extrator CSV. Isso não serve para agentes em Grok, Claude e similares: não há API REST oficial, o painel não é consultável por ferramenta, e o Extrator só mostra 100 linhas na tela.

O MCP PNP expõe os **indicadores oficiais de gestão** da PNP como ferramentas MCP, em português, para diagnóstico institucional em toda a Rede (sem instituição padrão).

## Público e sucesso

- **Público:** gestores de IF/CEFET/escolas vinculadas, SETEC e áreas de planejamento/controle.
- **Perguntas-alvo:** “qual a RAP (ALRMP) do IFMG em 2025?”, “e a RAP presencial (ALRAPE)?”, “a ALMTEC está nos 50%?”, “como evoluiu a ENME?”, “qual o GACM?”.
- **Sucesso:** o agente responde com o número oficial da PNP, a edição/ano, a definição do indicador e, quando pedido, comparação, ranking ou série histórica — sem inventar dado ausente e sem recalcular indicador oficial.

## Recorte do MVP (aprovado 2026-08-18)

Primeira implementação entrega só o que o Extrator PNP já publica:

- Ensino (EN*), situação, RAP/ALRMP/ALRAPE, legais (AL*), gastos (GA*), pessoal (PE*), perfil discente, Tesouro Gerencial (6 oficiais + desagregações já no Extrator), descoberta, análise derivada, glossário e sync.

Ficam no spec, **fora deste plano de implementação**:

- Pesquisa (PI*), extensão (EX*), polos (PO*), sustentabilidade (S*), INEP (IGC/CPC/Enade/IDD).

Essas tools não são registradas no MVP. `pnp_listar_indicadores` do MVP lista só o que está carregável. Quando houver CSV oficial, um plano seguinte registra as tools restantes.

## Fora de escopo (esta versão)

- Recalcular indicadores a partir de microdados (risco de divergir do número oficial).
- Portal `pnp.mec.gov.br` (oferta “quero estudar”, Rede Integra).
- Scraping do Power BI como fonte de dados (o PBIX documenta indicadores; a carga vem do Extrator ou, se o Extrator não tiver o conjunto, de CSV oficial equivalente).
- Instagram, redes sociais e demais visuais de comunicação do PBIX (`fInstagram`, URLs, curtidas).
- Medidas de chrome do relatório (sliders, botões, títulos, cores, `% de X` só para visual).
- Instituição padrão configurável.
- Transporte HTTP/SSE (fica preparado na estrutura; não é entrega do MVP).
- Autenticação, multi-tenant e hospedagem compartilhada.
- UI web.

## Decisões

1. **Fonte da verdade:** CSVs do Extrator PNP (`https://moduloextratorpnp.mec.gov.br/`), já calculados pelo modelo semântico oficial. Não se recalcula evasão, RAP, eficiência, percentuais legais nem gasto por Mateq.
2. **Loja local:** SQLite. Consultas leem só a base local. Sem fallback online na consulta.
3. **Stack:** Python 3.12+, FastMCP (stdio no MVP; o mesmo objeto de servidor deve poder subir HTTP/SSE depois sem reescrever tools).
4. **Granularidade:** uma tool por indicador/recorte nomeável. Filtros não viram tool. Nomes oficiais do Power BI (ALMTEC, ENME, RAP, etc.) entram como **aliases** obrigatórios nas descrições e no glossário.
5. **Análise derivada:** `pnp_comparar`, `pnp_evolucao`, `pnp_ranking` e `pnp_estatisticas` existem, mas toda resposta derivada leva `fonte: derivada`.
6. **Rede inteira:** sem `PNP_INSTITUICAO` padrão. Comparações entre IFs entram no MVP.
7. **Idioma:** tools, schemas, descrições e erros em pt-BR. Código e identificadores internos em inglês (`snake_case`).
8. **Sync:** tool `pnp_sincronizar` + CLI `mcp-pnp sync`. Consulta com base vazia falha com instrução para sincronizar.
9. **Catálogo canônico:** a lista oficial de indicadores é a do [Guia PNP Indicadores](https://pnp-ccv.github.io/guiapnp/documentacao/indicadores/lista_dos_indicadores.html) (SETEc/DSBR, atualizado em 2026). Cada item da lista tem tool (ou alias) no spec. O Power BI e o Extrator são superfícies de publicação/carga, não a definição do conjunto.
10. **Sigla oficial:** o código do indicador no envelope e em `pnp_listar_indicadores` é a sigla do Guia (`ENME`, `ALMTEC`, `ALRMP`, `GACM`, `PETCD`, …). Nomes populares (Mateq, RAP, ITCD) ficam como alias.

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
| 17 | Professores por instituição | `docentes_jornada` | docentes por titulação e jornada (20h/40h/DE) |
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

`ano` (int, opcional — se omitido, usa o último ano carregado e declara isso em `filtros_aplicados`), `instituicao` (sigla, case-insensitive), `unidade` (estrutura com matrícula), `uf`, `regiao`, `municipio`, `organizacao_academica`, `limite` (default 200, max 500), `offset`.

Filtros extras só quando a tabela/página do Power BI tiver o recorte: `tipo_curso`, `tipo_oferta`, `modalidade`, `turno`, `eixo`, `subeixo`, `nome_curso`, `fonte_financiamento`, `programa`, `faixa_carga_horaria` (FIC).

### Catálogo

**Descoberta**

| tool | faz |
|---|---|
| `pnp_listar_edicoes` | anos na base, edição PNP, data do sync |
| `pnp_listar_instituicoes` | sigla, nome, tipo; filtros região/UF/organização |
| `pnp_listar_unidades` | campi de uma instituição (instituição obrigatória) |
| `pnp_listar_indicadores` | código, nome, família, se é oficial |

**Oferta e volume**

| tool | métrica oficial no Power BI / Extrator |
|---|---|
| `pnp_consultar_estruturas` | **ENEMA** — Número de estruturas com matrícula |
| `pnp_consultar_unidades_academicas` | **ENUND** — Número de unidades acadêmicas (distinto de ENEMA) |
| `pnp_consultar_ciclos` | Número de ciclos (volume do Extrator; não é item da lista oficial) |
| `pnp_consultar_cursos` | **ENC** — Número de cursos |
| `pnp_consultar_matriculas` | **ENM** — Número de matrículas (matrícula atendida, ver Guia) |
| `pnp_consultar_mateq` | **ENME** — Número de matrículas equivalentes |
| `pnp_consultar_vagas` | **ENV** — Número de vagas |
| `pnp_consultar_inscritos` | **ENIC** — Número de inscritos |
| `pnp_consultar_ingressantes` | **ENING** — Número de ingressantes |
| `pnp_consultar_concluintes` | **ENCT** — Número de concluintes |

**Situação**

| tool | métrica |
|---|---|
| `pnp_consultar_em_curso` | situação “em curso” (componente de ENM) |
| `pnp_consultar_evadidos` | **ENEV** — Número de evadidos; filtro `motivo` |
| `pnp_consultar_retidos` | retidos / fluxo (componente de ENREC) |
| `pnp_consultar_formas_ingresso` | Formas de Ingresso (**FIng**), página de ensino do Guia |

**Indicadores acadêmicos oficiais**

| tool | métrica |
|---|---|
| `pnp_consultar_evasao` | **ENEVA** — Percentual de evasão anual |
| `pnp_consultar_evasao_ciclo` | **ENEC** — Percentual de evasão por ciclo |
| `pnp_consultar_conclusao_ciclo` | **ENCC** — Percentual de conclusão por ciclo |
| `pnp_consultar_retencao_ciclo` | **ENREC** — Percentual de retenção por ciclo |
| `pnp_consultar_eficiencia_academica` | **ENIEA** — Índice de eficiência acadêmica |
| `pnp_consultar_rap` | **ALRMP** — Relação matrícula-equivalente / professor-equivalente (nome consagrado: RAP) |
| `pnp_consultar_rap_presencial` | **ALRAPE** — RAP Presencial (só matrículas presenciais; meta 20) |
| `pnp_consultar_verticalizacao` | **ENIV** — Índice de verticalização |
| `pnp_consultar_ocupacao` | **ENOC** — Taxa de ocupação |

**Percentuais legais (Lei 11.892 / Decreto 5.840 e recortes PNP)**

Toda resposta dessas tools inclui o valor, a **meta oficial** e o desvio (como o cartão do Power BI: `48,8% Meta: 50,00% (−1,2%)`). Aplicam-se só a Institutos Federais quando o painel restringe “apenas IFs”.

| tool | nome oficial PBI | métrica | meta |
|---|---|---|---|
| `pnp_consultar_percentual_tecnicos` | **ALMTEC** | % Mateq em EPTNM | 50% (Lei 11.892) |
| `pnp_consultar_percentual_formacao_professores` | **ALMPROF** | % Mateq em formação de professores | 20% (Lei 11.892) |
| `pnp_consultar_percentual_proeja` | **ALMEJA** | % Mateq em EJA/EPT | 10% (Dec. 5.840) |
| `pnp_consultar_percentual_vagas_tecnicos` | **ALVTEC** | % oferta de vagas em EPTNM | — |
| `pnp_consultar_percentual_vagas_formacao_professores` | **ALVPROF** | % oferta de vagas em formação de professores | — |
| `pnp_consultar_percentual_vagas_proeja` | **ALVEJA** | % oferta de vagas em EJA/EPT | — |
| `pnp_consultar_percentual_cursos_graduacao_noturna` | **ALGN** | % cursos de graduação noturna presencial | PNE 2014 (série histórica mantida) |
| `pnp_consultar_percentual_mateq_graduacao_noturna` | **ALMGN** | % Mateq de graduação noturna presencial | PNE 2014 |
| `pnp_consultar_percentual_vagas_graduacao_noturna` | **ALVGN** | % vagas de graduação noturna presencial | PNE 2014 |
| `pnp_consultar_vagas_noturnas` | **ALVCN** | % vagas em cursos noturnos presenciais | PNE 2014 |
| `pnp_consultar_reserva_vagas` | **ALVAC / ALVRES / ALVTG** e **ALMAC / ALMRES / ALMTG** | vagas e matrículas ampla vs reserva (Lei 14.723/2023) | Lei de cotas |
| `pnp_consultar_inscritos_vagas` | **ENRIV** | Relação inscritos/vaga | — |

**Orçamento** (nomes do grupo `_fOrçamento` / `_fIndAcompOrc` do Power BI)

Não usar a sigla `RAP` nestas tools — no orçamento RAP = restos a pagar; no ensino RAP = relação aluno/professor.

| tool | métrica no Power BI |
|---|---|
| `pnp_consultar_projeto_lei` | Projeto de Lei |
| `pnp_consultar_dotacao_inicial` | Dotação inicial |
| `pnp_consultar_dotacao` | Dotação atualizada |
| `pnp_consultar_credito_adicional` | Crédito adicional / Dotação adicional |
| `pnp_consultar_empenho` | Despesa empenhada |
| `pnp_consultar_liquidacao` | Despesa liquidada |
| `pnp_consultar_despesa_paga` | Despesa paga |
| `pnp_consultar_empenhado_a_liquidar` | Empenhado a liquidar |
| `pnp_consultar_credito_disponivel` | Crédito disponível |
| `pnp_consultar_destaque_recebido` | Destaque recebido |
| `pnp_consultar_pagamento_total` | Pagamento total |
| `pnp_consultar_liquidacao_total` | Liquidação total / Despesa liq&RP |
| `pnp_consultar_restos_inscritos` | RAP inscrito e reinscrito |
| `pnp_consultar_restos_a_pagar` | RAP a pagar |
| `pnp_consultar_restos_pagos` | RAP pago |
| `pnp_consultar_restos_bloqueados` | RAP bloqueado |
| `pnp_consultar_restos_cancelados` | RAP cancelado |
| `pnp_consultar_percentual_execucao` | % execução e razões do `_fIndAcompOrc` (empenhada vs dotação, liquidada vs empenhada, etc.). Parâmetro `razao`. |

Todas aceitam filtro `resultado_primario` (obrigatorio, discricionario, emenda_bancada, emenda_individual, financeiro) e `relacao_orgao` quando a coluna existir.

**Gastos**

| tool | métrica |
|---|---|
| `pnp_consultar_gasto_por_mateq` | **GACM** — Gastos correntes por matrícula equivalente |
| `pnp_consultar_gastos_totais` | **GAT** — Gastos totais |
| `pnp_consultar_gastos_correntes` | **GAC** — Gastos correntes |
| `pnp_consultar_gastos_pessoal` | **GAPE** — Gastos de pessoal |
| `pnp_consultar_gastos_custeio` | **GAOC** — Outros custeios |
| `pnp_consultar_gastos_investimento` | **GAIV** — Investimentos e inversões |
| `pnp_consultar_gastos_inativos` | **GAIP** — Inativos e pensionistas |
| `pnp_consultar_gastos_precatorios` | **GAPRE** — Precatórios |
| `pnp_consultar_gastos_pis_pasep` | Pis-Pasep (decomposição do Extrator; **não** é item da lista oficial) |

**Pessoas**

| tool | métrica |
|---|---|
| `pnp_consultar_docentes` | **PEDO** — Número de pessoas docentes |
| `pnp_consultar_docentes_efetivos` | **PEDE** — Número de pessoas docentes efetivas |
| `pnp_consultar_tae` | **PETAE** — Número de pessoas TAE |
| `pnp_consultar_cargos` | carreira (volume do Extrator; não é item da lista oficial) |
| `pnp_consultar_servidores` | **PES** — Número de pessoas servidoras |
| `pnp_consultar_profeq` | professor-equivalente (DEq nas fichas de ALRMP/ALRAPE) |
| `pnp_consultar_itcd` | **PETCD** — Índice de titulação do corpo docente efetivo |
| `pnp_consultar_jornada` | jornada 20h/40h/DE (volume do Extrator) |
| `pnp_consultar_funcoes` | funções/comissão (volume do PBIX; não é item da lista oficial) |

**Perfil**

| tool | dimensão |
|---|---|
| `pnp_consultar_cor_raca` | cor/raça |
| `pnp_consultar_renda` | renda familiar |
| `pnp_consultar_sexo` | sexo |
| `pnp_consultar_faixa_etaria` | faixa etária |

**Qualidade INEP (páginas do mesmo PBIX oficial; não estão no Extrator)**

| tool | métrica no Power BI |
|---|---|
| `pnp_consultar_igc` | IGC – INEP |
| `pnp_consultar_cpc` | CPC – INEP |
| `pnp_consultar_enade` | Conceito Enade – INEP |
| `pnp_consultar_idd` | IDD – INEP |

Se o sync não encontrar CSV oficial, a tool devolve `fonte_indisponivel` — não scrapa o Power BI.

**Pesquisa e inovação (lista oficial; carga quando houver CSV)**

| tool | sigla |
|---|---|
| `pnp_consultar_acordos_pesquisa` | **PIPDI** |
| `pnp_consultar_ativos_propriedade` | **PIPROT** |
| `pnp_consultar_ativos_transferidos` | **PIPROTR** |
| `pnp_consultar_producao_intelectual` | **PIPRO** |
| `pnp_consultar_estudantes_pesquisa` | **PIES** |
| `pnp_consultar_cotistas_pesquisa` | **PICOT** |
| `pnp_consultar_investimento_pesquisa` | **PINV** |
| `pnp_consultar_servidores_pesquisa` | **PISERV** |
| `pnp_consultar_pesquisa_aplicada` | **PIPA** |

**Extensão**

| tool | sigla |
|---|---|
| `pnp_consultar_pessoas_atendidas_extensao` | **EXPAE** |
| `pnp_consultar_extensao_com_parceria` | **EXPAR** |
| `pnp_consultar_extensao_vulneravel` | **EXVUL** |
| `pnp_consultar_estudantes_extensao` | **EXEAE** |
| `pnp_consultar_cotistas_extensao` | **EXCOT** |
| `pnp_consultar_servidores_extensao` | **EXSERV** |
| `pnp_consultar_recursos_extensao` | **EXREC** |

**Polos de inovação**

| tool | sigla |
|---|---|
| `pnp_consultar_polos_contratos` | **POP** |
| `pnp_consultar_polos_empresas` | **POEMP** |
| `pnp_consultar_polos_eventos` | **POET** |
| `pnp_consultar_polos_colaboradores` | **POCO** |
| `pnp_consultar_polos_estudantes_bolsistas` | **POEB** |
| `pnp_consultar_polos_servidores_bolsistas` | **POSERV** |
| `pnp_consultar_polos_propriedade` | **POPID** |
| `pnp_consultar_polos_unidades_pesquisa` | **POUP** |
| `pnp_consultar_polos_recurso` | **POREC** |

**Sustentabilidade**

| tool | sigla |
|---|---|
| `pnp_consultar_consumo_agua` | **SCAG** |
| `pnp_consultar_consumo_energia` | **SCEE** |
| `pnp_consultar_geracao_renovavel` | **SGER** |
| `pnp_consultar_governanca_sustentabilidade` | **SIGS** |
| `pnp_consultar_gestao_residuos` | **SIGRS** |
| `pnp_consultar_divulgacao_sustentabilidade` | **SIDS** |
| `pnp_consultar_compras_sustentaveis_inst` | **SICS** |
| `pnp_consultar_percentual_compras_sustentaveis` | **SPCS** |
| `pnp_consultar_projetos_sustentabilidade` | **SPRO** |
| `pnp_consultar_projetos_gestao_sustentabilidade` | **SPGIS** |

**Tesouro Gerencial (lista oficial — 6 itens)**

As tools de orçamento já cobrem os 6 oficiais: dotação atualizada, despesa empenhada, despesa liquidada, despesa paga, empenho a liquidar, crédito disponível. As demais (`projeto_lei`, restos a pagar detalhados, destaque, % execução) são **desagregações do Extrator/PBIX**, não itens da lista oficial.

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
| `fonte_indisponivel` | indicador no spec (ex.: IGC) sem CSV oficial carregado | dizer o indicador e que a fonte ainda não está na base |
| `limite_invalido` | limite > 500 ou < 1 | lembrar o teto |

Nunca completar número faltante com estimativa. Célula vazia no CSV oficial vira `null`, não zero.

## Testes

Pirâmide sem rede no CI:

1. **Envelope e filtros** — `tests/test_envelope.py`, `tests/test_filtros.py`.
2. **Queries com fixture** — SQLite temporário carregado de CSVs mínimos em `tests/fixtures/` (recorte de 2 instituições, 2 anos, 2 campi). Uma suíte por família de tools.
3. **Análise** — comparar IF vs Rede, YoY, ranking e percentil sobre a fixture; assert `fonte == derivada`.
4. **Glossário** — termos obrigatórios do Guia: `enme`, `enm`, `enema`, `enund`, `eniea`, `eneva`, `enec`, `encc`, `enrec`, `enoc`, `eniv`, `almtec`, `almprof`, `almeja`, `alrmp`, `alrape`, `gacm`, `petcd`, `matricula_atendida`, `fech`, `fec`, `fcg`.
5. **Ingest unitário** — `client` e `loader` com HTTP mockado (resposta CSV fixa). Nenhum teste de CI bate no MEC.
6. **Contrato MCP** — lista todas as tools do catálogo, verifica nome em pt-BR, aliases oficiais do Power BI e envelope.

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

## Catálogo oficial do Guia (check 2026-08-18)

Fonte canônica: [Lista dos indicadores](https://pnp-ccv.github.io/guiapnp/documentacao/indicadores/lista_dos_indicadores.html) do Guia PNP Indicadores. PDF: [Guia_PNP.pdf](https://pnp-ccv.github.io/guiapnp/assets/files/Guia_PNP.pdf). Fichas: [fichas técnicas](https://pnp-ccv.github.io/guiapnp/documentacao/usuarios-especializados/fichas_tecnica_dos_indicadores.html).

### Ensino

| sigla | indicador | tool | status |
|---|---|---|---|
| ENCT | Nº de concluintes | `pnp_consultar_concluintes` | coberto |
| ENC | Nº de cursos | `pnp_consultar_cursos` | coberto |
| ENEV | Nº de evadidos | `pnp_consultar_evadidos` | coberto |
| ENEMA | Nº de estruturas com matrícula | `pnp_consultar_estruturas` | coberto |
| ENING | Nº de ingressantes | `pnp_consultar_ingressantes` | coberto |
| ENIC | Nº de inscritos | `pnp_consultar_inscritos` | coberto |
| ENM | Nº de matrículas | `pnp_consultar_matriculas` | coberto |
| ENME | Nº de matrículas equivalentes | `pnp_consultar_mateq` | coberto |
| ENUND | Nº de unidades acadêmicas | `pnp_consultar_unidades_academicas` | coberto (distinto de ENEMA) |
| ENV | Nº de vagas | `pnp_consultar_vagas` | coberto |
| ENIEA | Índice de eficiência acadêmica | `pnp_consultar_eficiencia_academica` | coberto |
| ENIV | Índice de verticalização | `pnp_consultar_verticalizacao` | coberto |
| ENCC | % conclusão por ciclo | `pnp_consultar_conclusao_ciclo` | coberto |
| ENEVA | % evasão anual | `pnp_consultar_evasao` | coberto |
| ENEC | % evasão por ciclo | `pnp_consultar_evasao_ciclo` | coberto |
| ENREC | % retenção por ciclo | `pnp_consultar_retencao_ciclo` | coberto |
| ENRIV | Relação inscritos/vagas | `pnp_consultar_inscritos_vagas` | coberto |
| ENOC | Taxa de ocupação | `pnp_consultar_ocupacao` | coberto |

### Acompanhamento legal

| sigla | indicador | tool | status |
|---|---|---|---|
| ALMEJA | % Mateq EJA/EPT | `pnp_consultar_percentual_proeja` | coberto (meta 10%) |
| ALMTEC | % Mateq EPTNM | `pnp_consultar_percentual_tecnicos` | coberto (meta 50%) |
| ALMPROF | % Mateq formação de professores | `pnp_consultar_percentual_formacao_professores` | coberto (meta 20%) |
| ALVEJA | % vagas EJA/EPT | `pnp_consultar_percentual_vagas_proeja` | coberto |
| ALVTEC | % vagas EPTNM | `pnp_consultar_percentual_vagas_tecnicos` | coberto |
| ALVPROF | % vagas formação de professores | `pnp_consultar_percentual_vagas_formacao_professores` | coberto |
| ALGN | % cursos graduação noturna presencial | `pnp_consultar_percentual_cursos_graduacao_noturna` | coberto |
| ALMGN | % Mateq graduação noturna presencial | `pnp_consultar_percentual_mateq_graduacao_noturna` | coberto |
| ALVGN | % vagas graduação noturna presencial | `pnp_consultar_percentual_vagas_graduacao_noturna` | coberto |
| ALVCN | % vagas noturnas presenciais | `pnp_consultar_vagas_noturnas` | coberto |
| ALRMP | Mateq / professor-eq. (RAP) | `pnp_consultar_rap` | coberto |
| ALRAPE | Mateq presencial / professor-eq. | `pnp_consultar_rap_presencial` | coberto (meta 20) |
| ALMAC, ALMTG, ALMRES, ALVAC, ALVTG, ALVRES | cotas Lei 14.723 | `pnp_consultar_reserva_vagas` | cobertos na mesma tool (recorte) |

### Pessoal

| sigla | tool | status |
|---|---|---|
| PETCD | `pnp_consultar_itcd` | coberto |
| PEDO | `pnp_consultar_docentes` | coberto |
| PEDE | `pnp_consultar_docentes_efetivos` | coberto |
| PES | `pnp_consultar_servidores` | coberto |
| PETAE | `pnp_consultar_tae` | coberto |

### Gastos

| sigla | tool | status |
|---|---|---|
| GAIP | `pnp_consultar_gastos_inativos` | coberto |
| GAPRE | `pnp_consultar_gastos_precatorios` | coberto |
| GAC | `pnp_consultar_gastos_correntes` | coberto |
| GACM | `pnp_consultar_gasto_por_mateq` | coberto |
| GAPE | `pnp_consultar_gastos_pessoal` | coberto |
| GAT | `pnp_consultar_gastos_totais` | coberto |
| GAIV | `pnp_consultar_gastos_investimento` | coberto |
| GAOC | `pnp_consultar_gastos_custeio` | coberto |

### Pesquisa, extensão, polos, sustentabilidade

As quatro dimensões constam do Guia e têm tools no spec. A carga depende de CSV oficial (CCV/Extrator). Sem arquivo: `fonte_indisponivel`. Não recalcular.

| dimensão | siglas | qtd |
|---|---|---|
| Pesquisa e inovação | PIPDI, PIPROT, PIPROTR, PIPRO, PIES, PICOT, PINV, PISERV, PIPA | 9 |
| Extensão | EXPAE, EXPAR, EXVUL, EXEAE, EXCOT, EXSERV, EXREC | 7 |
| Polos de inovação | POP, POEMP, POET, POCO, POEB, POSERV, POPID, POUP, POREC | 9 |
| Sustentabilidade | SCAG, SCEE, SGER, SIGS, SIGRS, SIDS, SICS, SPCS, SPRO, SPGIS | 10 |

### INEP e Tesouro (o Guia os lista à parte)

| origem | indicadores oficiais | spec |
|---|---|---|
| INEP | CPC, IGC, Enade, IDD | 4 tools |
| Tesouro Gerencial | dotação atualizada, empenhada, liquidada, paga, empenho a liquidar, crédito disponível | 6 tools de orçamento |

### O que o Guia **não** trata como indicador (e o spec marca como volume/desagregação)

Ciclos, jornada, funções, cargos, Pis-Pasep, projeto de lei, restos a pagar detalhados, Instagram, sliders do Power BI. Permanecem só quando o Extrator/PBIX publica o recorte e a descrição da tool diz que **não** é item da lista oficial.

### Conceito obrigatório do Guia

**Matrícula atendida** (base de ENM e da maioria dos indicadores de ensino): matrícula ativa em pelo menos um dia do ano-base, após regras do CCV. Documentar em `pnp_glossario` (`matricula_atendida`) e na descrição de `pnp_consultar_matriculas`.

## Review do spec

- Sem TBD/TODO.
- Um servidor, um domínio (indicadores oficiais de gestão). Não precisa decompor em vários projetos.
- “Indicador oficial” = item da lista do Guia PNP (sigla EN*/AL*/GA*/PE*/PI*/EX*/PO*/S*) carregado de CSV oficial. “Derivada” = cálculo do MCP. Volume Extrator sem sigla no Guia não se apresenta como indicador oficial.
- HTTP/SSE fica só como extensão futura da mesma instância FastMCP, sem design de auth nesta versão.
