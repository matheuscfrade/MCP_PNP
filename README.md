# MCP PNP

Servidor MCP da Plataforma Nilo Peçanha (indicadores oficiais de gestão).

O MCP PNP expõe os indicadores oficiais da PNP como ferramentas para agentes (Grok, Claude e similares). Consultas leem uma base SQLite local, preenchida pelos CSVs oficiais do Extrator PNP.

## Recorte do MVP

Coberto (conjuntos já publicados no Extrator): ensino (EN*), percentuais legais (AL*), pessoas (PE*), gastos (GA*), Tesouro Gerencial, perfil discente, descoberta, análise derivada, glossário e sync.

Ainda não registrados: pesquisa (PI*), extensão (EX*), polos (PO*), sustentabilidade (S*) e INEP (IGC/CPC/Enade/IDD).

## Instalação

```powershell
pip install -e ".[dev]"
mcp-pnp sync --from-dir <pasta-com-os-CSVs-do-Extrator>
```

A pasta `data/` e os CSVs do Extrator **não** vão no Git (são ~90 MB e mudam a cada edição). Estão na [Release `extrator-2025`](https://github.com/matheuscfrade/MCP_PNP/releases/tag/extrator-2025): zip dos 18 CSVs e o `pnp.sqlite` já importado.

```powershell
# CSVs
gh release download extrator-2025 -p extrator-pnp-csvs.zip -R matheuscfrade/MCP_PNP
# ou use o pnp.sqlite direto e defina PNP_DB_PATH
```

Indicadores que o Extrator ainda não exporta (ALRAPE, ALVCN, ALGN, ALMGN, ALVTEC, ALVPROF, ALVEJA e outros) estão em `docs/lacunas-extrator.md`.

Na primeira execução (stdio ou HTTP), se `data/pnp.sqlite` não existir o servidor baixa o arquivo da release. Para pular: `PNP_SKIP_DB_DOWNLOAD=1`. URL alternativa: `PNP_DB_URL`.

## Servidor remoto (Prefect Horizon)

Hospedagem gratuita do FastMCP. O entrypoint é `server.py:mcp`.

1. Faça push destas alterações para o GitHub.
2. Entre em [horizon.prefect.io](https://horizon.prefect.io) com a conta GitHub.
3. Selecione o repositório `MCP_PNP`.
4. Entrypoint: `server.py:mcp`. Nome sugerido: `pnp`.
5. Autenticação: desligada (dados públicos do Extrator). Ligue OAuth no painel se quiser restringir.
6. Deploy. A URL fica `https://<nome>.fastmcp.app/mcp`.

O processo sobe sem baixar o banco (o pre-flight do Horizon tem ~15 s). A primeira consulta baixa o `pnp.sqlite` (~90 MB) da release `extrator-2025` para `/tmp`. Se o repositório/release for privado, deixe a release pública **ou** defina `GITHUB_TOKEN` nas variáveis do Horizon.

O health check responde em `https://<nome>.fastmcp.app/health`.

Claude / Cursor (HTTP):

```json
{
  "mcpServers": {
    "pnp": { "url": "https://pnp.fastmcp.app/mcp" }
  }
}
```

Para testar HTTP local (sem Horizon):

```powershell
mcp-pnp serve
# http://127.0.0.1:8000/mcp  e  /health
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

## Cursor

No MCP do Cursor, o mesmo comando stdio:

```json
{
  "mcpServers": {
    "pnp": { "command": "mcp-pnp" }
  }
}
```

## Primeiro uso

Depois de instalar, sincronizar e configurar o cliente, chame `pnp_status_base` para conferir o caminho do banco, as edições carregadas e o último sync.

Exemplos:

- “Qual a ENME do IFMG em 2025?”
- “A ALMTEC está nos 50%?”
- “Compare a ALRMP do IFMG com a Rede.”
- “Qual a ENEVA presencial do Campus Formiga?”

Recortes extras (modalidade, tipo de curso…) só existem quando a **página do painel/Extrator** daquele indicador publica o slicer. ENEVA e ENME aceitam modalidade; ENEC e RAP não. Depois de atualizar o schema, recarregue os CSVs (`mcp-pnp sync --from-dir <pasta>`) para a evasão ganhar `ModalidadeEnsino`.
