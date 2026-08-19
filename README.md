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
