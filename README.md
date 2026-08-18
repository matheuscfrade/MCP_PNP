# MCP PNP

Servidor MCP da Plataforma Nilo Peçanha (indicadores oficiais de gestão).

O MCP PNP expõe os indicadores oficiais da PNP como ferramentas para agentes (Grok, Claude e similares). Consultas leem uma base SQLite local, preenchida pelos CSVs oficiais do Extrator PNP.

## Recorte do MVP

Coberto (conjuntos já publicados no Extrator): ensino (EN*), percentuais legais (AL*), pessoas (PE*), gastos (GA*), Tesouro Gerencial, perfil discente, descoberta, análise derivada, glossário e sync.

Ainda não registrados: pesquisa (PI*), extensão (EX*), polos (PO*), sustentabilidade (S*) e INEP (IGC/CPC/Enade/IDD).

## Instalação

No repositório principal:

```powershell
cd D:\OneDrive\Documentos\devProjects\projects\MCP_PNP
pip install -e ".[dev]"
mcp-pnp sync
```

Se estiver neste worktree (`feat/mcp-pnp-mvp`):

```powershell
cd D:\OneDrive\Documentos\devProjects\projects\MCP_PNP\.worktrees\feat-mcp-pnp-mvp
pip install -e ".[dev]"
mcp-pnp sync
```

`mcp-pnp sync` baixa os CSVs oficiais do Extrator e popula `data/pnp.sqlite`. Sem sync, as consultas falham pedindo sincronização.

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
