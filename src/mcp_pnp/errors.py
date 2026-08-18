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
