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

# Nomes dos CSVs baixados pelo botão "Baixar CSV" do Extrator.
ARQUIVOS_LOCAIS: dict[str, str] = {
    "panoramaorcamentario": "orcamento",
    "dadosgerais": "oferta",
    "situacaomatricula": "situacao_matricula",
    "cassificacaoracialrendasexo": "perfil_discente",
    "classificacaoracialrendasexo": "perfil_discente",
    "percentuaislegais": "percentuais_legais",
    "reservavagas": "reserva_vagas",
    "ofertavagasnoturnas": "vagas_noturnas",
    "relacaoinscritosvagas": "inscritos_vagas",
    "taxaevasao": "evasao",
    "eficienciaacademica": "eficiencia",
    "relacaoalunoprofessorrap": "rap",
    "indiceverticalizacao": "verticalizacao",
    "taxaocupacao": "ocupacao",
    "titulacaodocente": "docentes",
    "tecnicosadmnivel": "tae",
    "indicadoresgastos": "gastos",
    "cargoscarreira": "cargos",
    "professoresporinstituicao": "docentes_jornada",
}


def tabela_do_arquivo(nome: str) -> str | None:
    stem = nome.rsplit(".", 1)[0].lower()
    compacto = "".join(ch for ch in stem if ch.isalnum())
    return ARQUIVOS_LOCAIS.get(compacto)
