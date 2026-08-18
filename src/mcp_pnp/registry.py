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
