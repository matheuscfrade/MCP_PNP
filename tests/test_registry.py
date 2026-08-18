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
