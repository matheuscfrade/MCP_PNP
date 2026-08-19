# Lacunas do Extrator (completar depois)

O painel Power BI da PNP calcula alguns indicadores no modelo semântico (microdados: `dimCurso.turnoCurso`, eixo, financiamento). O Extrator 2.3.0 (`/pnpquery/1`–`18`) **não exporta** esses recortes. Não é falha de importação: as páginas ao vivo do Extrator têm as mesmas colunas dos CSVs locais.

Conferido em 2026-08-18 contra o painel (IFMG, ano-base 2025) e contra `https://moduloextratorpnp.mec.gov.br/pnpquery/{id}`.

## O que falta no Extrator (ensino / legal)

| Sigla | O que é | Por que não dá para calcular agora |
|---|---|---|
| **ALRAPE** | RAP só presencial (Mateq presencial / professor-eq.; meta 20) | Query 12 só tem RAP geral. Mateq RAP ≠ ENME presencial da oferta |
| **ALVCN** | % vagas noturnas presenciais (todos os níveis) | Query 8 só traz noturnas de **graduação** (isso é ALVGN) |
| **ALGN** | % cursos de graduação presencial noturna | Query 8 não traz nº de cursos; Dados Gerais (query 3) não tem `turno` |
| **ALMGN** | % Mateq de graduação presencial noturna | Sem Mateq noturna no CSV |
| **ALVTEC** | % vagas em EPTNM | Query 6 só tem Mateq (ALMTEC), não vagas |
| **ALVPROF** | % vagas em formação de professores | Idem (irmão de vagas do ALMPROF) |
| **ALVEJA** | % vagas em EJA/PROEJA | Idem (irmão de vagas do ALMEJA) |

Já cobertos da mesma família: ALMTEC, ALMPROF, ALMEJA, **ALVGN**, **ALRMP**.

## Outros buracos oficiais (fora desses sete)

- **Cotas em matrícula** (ALMAC, ALMRES, ALMTG): o CSV de reserva só tem **vagas** (ALVAC, ALVRES, ALVTG).
- **Pesquisa, extensão, polos, sustentabilidade** (PI*, EX*, PO*, S*): o Guia lista; o Extrator 2.3.0 não tem conjunto.
- **INEP** (IGC, CPC, Enade, IDD): no painel, não no Extrator.
- **Microdados** do cubo 2025: não são públicos. Dados Abertos do MEC tem microdados até **PNP 2024 (ano-base 2023)**. CCV é só para quem valida na instituição.

## Como completar no futuro

1. Novo CSV no Extrator com turno / eixo / programa, ou conjunto específico (RAP presencial, vagas legais).
2. Ou microdado oficial do **mesmo ano-base** do painel — e só então validar de novo no Power BI antes de marcar como `fonte=oficial`.
3. Recalcular a partir da oferta atual (filtrar presencial, chutar técnico/total) **não** reproduz o cartão oficial.

Enquanto isso, as tools desses códigos devolvem `valor_oficial = null` com a expressão da lacuna, em vez de inventar média ou recorte errado.
