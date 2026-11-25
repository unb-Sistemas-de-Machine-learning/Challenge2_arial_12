import pytest

from src.rag.catalogo import Fonte
from src.rag.limpeza import Paragrafo
from src.rag.secoes import (
    Auditoria,
    menciona_contraindicacao,
    publico_alvo,
    segmentar_bula,
    segmentar_por_titulos,
)


def fonte(**alteracoes) -> Fonte:
    base = {
        "doc_id": "DOC-TESTE",
        "slug": "teste",
        "arquivo": "teste.pdf",
        "sha256": "0" * 64,
        "orgao_emissor": "MINISTERIO_DA_SAUDE",
        "titulo_documento": "Protocolo de teste",
        "categoria": "protocolo_clinico",
        "jornada": "pedro",
        "entidade_principal": "dengue",
        "publico_alvo": ["geral", "pacientes_com_dengue"],
        "data_publicacao": "2024",
        "url_referencia": "https://www.gov.br/saude/",
        "data_coleta": "2026-11-25",
        "data_verificacao_vigencia": "2026-11-25",
        "situacao_vigencia": "vigente",
        "evidencia_vigencia": "teste",
        "secao_padrao": "manejo_clinico",
        "regras_secao": [
            {"padrao": "sinais de alarme", "secao": "sinais_de_alarme"},
            {"padrao": "diagn[óo]stico diferencial", "secao": "descartar"},
        ],
    }
    base.update(alteracoes)
    return Fonte.model_validate(base)


def p(texto: str, tamanho: float = 10, titulo: bool = False, pagina: int = 1):
    return Paragrafo(texto, pagina, tamanho, negrito=titulo, candidato_titulo=titulo)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("c. Não utilizar salicilatos ou anti-inflamatórios.", True),
        ("Este medicamento é contraindicado em caso de suspeita de dengue.", True),
        ("A vacina não deve ser administrada em gestantes.", True),
        ("Radiografias não são contraindicadas na gestação.", False),
        ("Não utilizar doses maiores que a recomendada.", False),
        ("Prescrever paracetamol e/ou dipirona.", False),
    ],
)
def test_menciona_contraindicacao(texto: str, esperado: bool) -> None:
    assert menciona_contraindicacao(texto) is esperado


def test_publico_alvo_acrescenta_o_que_o_texto_menciona() -> None:
    f = fonte()
    assert publico_alvo(f, "Manejo geral.") == ["geral", "pacientes_com_dengue"]
    assert publico_alvo(f, "9 Gestação e dengue", "Idosos e lactantes") == [
        "geral",
        "gestante",
        "lactante",
        "idoso",
        "pacientes_com_dengue",
    ]


def test_segmentar_por_titulos_hierarquia_regras_e_reclassificacao() -> None:
    paragrafos = [
        p("1 Manejo da doença", 18, True),
        p("1.1 Conduta", 14, True),
        p("a. Orientar hidratação oral e repouso."),
        p("b. Não utilizar anti-inflamatórios não esteroides."),
        p("1.2 Sinais de alarme", 14, True),
        p("Dor abdominal intensa exige atendimento imediato."),
        p("2 Diagnóstico diferencial", 18, True),
        p("Texto descartado pela regra do catálogo."),
        p("APÊNDICE H USO DE MEDICAMENTOS", 15, True),
        p("Paracetamol pode ser usado para febre."),
    ]
    auditoria = Auditoria()
    blocos = segmentar_por_titulos(fonte(), paragrafos, auditoria)
    assert [(b.secao, b.titulo_secao) for b in blocos] == [
        ("manejo_clinico", "1 Manejo da doença > 1.1 Conduta"),
        ("contraindicacoes", "1 Manejo da doença > 1.1 Conduta"),
        ("sinais_de_alarme", "1 Manejo da doença > 1.2 Sinais de alarme"),
        ("manejo_clinico", "APÊNDICE H USO DE MEDICAMENTOS"),
    ]
    assert auditoria.reclassificados[0]["de"] == "manejo_clinico"
    assert (
        auditoria.descartados[0]["trecho"] == "Texto descartado pela regra do catálogo."
    )


def test_sem_secao_padrao_descarta_titulos_sem_regra() -> None:
    auditoria = Auditoria()
    blocos = segmentar_por_titulos(
        fonte(secao_padrao=None),
        [p("1 Introdução", 18, True), p("Texto sem regra.")],
        auditoria,
    )
    assert blocos == []
    assert len(auditoria.descartados) == 1


def test_segmentar_bula_pelas_perguntas_da_rdc_47() -> None:
    paragrafos = [
        p("APRESENTAÇÕES", titulo=True),
        p("Cápsula de 600 mg."),
        p("1. PARA QUE ESTE MEDICAMENTO É INDICADO?", titulo=True),
        p("Indicado para dor e febre em adultos."),
        p("2. COMO ESTE MEDICAMENTO FUNCIONA?", titulo=True),
        p("Inibe a síntese de prostaglandinas."),
        p("3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?", titulo=True),
        p("Contraindicado em caso de suspeita de dengue."),
        p("4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?", titulo=True),
        p("Use com cautela em pacientes com problemas renais."),
        p("Uso durante a Gravidez", titulo=True),
        p("Não use durante a gravidez sem orientação médica."),
        p("Interações medicamentosas", titulo=True),
        p("Evite o uso com outros anti-inflamatórios."),
        p("COMO DEVO USAR ESTE MEDICAMENTO?", titulo=True),
        p("Tome uma cápsula a cada oito horas."),
        p("DIZERES LEGAIS", titulo=True),
        p("Registro 1.0000.0000."),
    ]
    auditoria = Auditoria()
    blocos = segmentar_bula(
        fonte(categoria="bula_medicamento", publico_alvo=["geral"]),
        paragrafos,
        auditoria,
    )
    assert [(b.secao, b.texto) for b in blocos] == [
        ("indicacoes", "Indicado para dor e febre em adultos."),
        ("contraindicacoes", "Contraindicado em caso de suspeita de dengue."),
        (
            "advertencias_e_precaucoes",
            "Use com cautela em pacientes com problemas renais.",
        ),
        ("gravidez_e_lactacao", "Não use durante a gravidez sem orientação médica."),
        ("interacoes_medicamentosas", "Evite o uso com outros anti-inflamatórios."),
    ]
    assert blocos[3].titulo_secao.endswith("> Uso durante a Gravidez")
    assert blocos[3].publico_alvo == ["geral", "gestante"]
    assert len(auditoria.descartados) == 4


def test_rotulo_no_inicio_do_paragrafo_encerra_subtitulo_de_gravidez() -> None:
    paragrafos = [
        p("4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?", titulo=True),
        p("Não tome mais do que a dose recomendada."),
        p("Gravidez e Amamentação", titulo=True),
        p("Se você estiver grávida, consulte o seu médico."),
        p("Uso em idosos: não são conhecidas restrições específicas."),
        p("Não use outro produto que contenha paracetamol."),
        p("Lactação: consulte o médico antes de amamentar."),
        p("Interações medicamentosas", titulo=True),
        p("Evite o uso com varfarina."),
        p("Medicamento-alimentos: não há dados disponíveis."),
    ]
    blocos = segmentar_bula(
        fonte(categoria="bula_medicamento", publico_alvo=["geral"]),
        paragrafos,
        Auditoria(),
    )
    assert [b.secao for b in blocos] == [
        "advertencias_e_precaucoes",
        "gravidez_e_lactacao",
        "advertencias_e_precaucoes",
        "advertencias_e_precaucoes",
        "gravidez_e_lactacao",
        "interacoes_medicamentosas",
        "interacoes_medicamentosas",
    ]
    assert (
        blocos[3].titulo_secao == "4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?"
    )
    assert blocos[3].publico_alvo == ["geral"]


def test_texto_antes_do_primeiro_titulo_e_descartado() -> None:
    auditoria = Auditoria()
    blocos = segmentar_por_titulos(
        fonte(),
        [
            p("fim da seção anterior, fora do intervalo."),
            p("1 Manejo", 18, True),
            p("Repouso."),
        ],
        auditoria,
    )
    assert [b.texto for b in blocos] == ["Repouso."]
    assert "antes do primeiro título" in auditoria.descartados[0]["motivo"]


def test_mencao_a_ausencia_de_contraindicacao_nao_reclassifica() -> None:
    assert not menciona_contraindicacao(
        "Todas as pessoas, desde que não tenham contraindicação, precisam usar."
    )


def test_anexo_aninha_os_titulos_seguintes_do_mesmo_tamanho() -> None:
    f = fonte(
        categoria="nota_tecnica",
        secao_padrao="gravidez_e_lactacao",
        regras_secao=[{"padrao": "^ANEXO", "secao": "descartar"}],
    )
    auditoria = Auditoria()
    blocos = segmentar_por_titulos(
        f,
        [
            p("ORIENTAÇÕES", 12, True),
            p("Suspender a amamentação por 15 dias após a vacinação."),
            p("ANEXO Como manter a produção de leite?", 12, True),
            p("Esvaziar as mamas regularmente durante a suspensão."),
            p("Como preparar o frasco?", 12, True),
            p("Escolher um frasco de vidro com tampa plástica."),
        ],
        auditoria,
    )
    assert [b.texto for b in blocos] == [
        "Suspender a amamentação por 15 dias após a vacinação."
    ]
    assert len(auditoria.descartados) == 2


def test_entidade_por_titulo_e_por_inicio_de_paragrafo() -> None:
    f = fonte(
        categoria="nota_tecnica",
        secao_padrao="esquema_vacinal",
        entidade_principal="calendario_vacinal",
        regras_entidade=[
            {"padrao": "^Vacina difteria", "entidade": "dtpa"},
            {"padrao": "^Vacina Covid", "entidade": "covid_19"},
            {"padrao": "influenza", "entidade": "influenza"},
        ],
    )
    blocos = segmentar_por_titulos(
        f,
        [
            p("ANÁLISE", 12, True),
            p("Vacina difteria, tétano e pertussis (dTpa) incorporada em 2014."),
            p("Recomenda-se uma dose em todas as gestações."),
            p("Vacina Covid-19 Recomenda-se uma dose anual para gestantes."),
            p("Vacina influenza", 12, True),
            p("Uma dose por temporada para gestantes."),
        ],
        Auditoria(),
    )
    assert [b.entidade for b in blocos] == ["dtpa", "dtpa", "covid_19", "influenza"]


def test_salto_de_pagina_reinicia_os_titulos() -> None:
    auditoria = Auditoria()
    blocos = segmentar_por_titulos(
        fonte(),
        [
            p("1 Manejo", 18, True, pagina=8),
            p("Hidratação oral.", pagina=8),
            p("Final de uma seção que ficou fora do intervalo.", pagina=25),
        ],
        auditoria,
    )
    assert [b.texto for b in blocos] == ["Hidratação oral."]
    assert "antes do primeiro título" in auditoria.descartados[0]["motivo"]


def _fonte_calendario() -> Fonte:
    return fonte(
        categoria="calendario_vacinal",
        publico_alvo=["adulto"],
        entidade_principal="calendario_vacinal",
        secao_padrao="esquema_vacinal",
        regras_secao=[],
        regras_entidade=[
            {"padrao": "\\bdTpa\\b", "entidade": "dtpa"},
            {"padrao": "febre amarela", "entidade": "febre_amarela"},
        ],
    )


def test_segmentar_calendario_por_vacina_e_subtitulo() -> None:
    from src.rag.secoes import segmentar_calendario

    auditoria = Auditoria()
    blocos = segmentar_calendario(
        _fonte_calendario(),
        [
            p("fim da vacina anterior, fora do intervalo.", pagina=1),
            p("1. Vacina adsorvida difteria, tétano e pertussis - dTpa", 12, True, 2),
            p("Indicação", 12, True, 2),
            p("Prevenção de difteria, tétano e coqueluche.", pagina=2),
            p("Esquema de vacinação", 12, True, 2),
            p("Gestante: 1 dose a partir da 20ª semana, a cada gravidez.", pagina=2),
            p("Contraindicações", 12, True, 3),
            p("Reação anafilática a dose anterior da vacina.", pagina=3),
            p("Recomendações sobre administração simultânea", 12, True, 3),
            p("Pode ser administrada com as demais vacinas.", pagina=3),
            p("Texto de outra vacina, depois de um salto de páginas.", pagina=25),
            p("13. Vacina febre amarela (atenuada) - VFA", 12, True, 29),
            p("Contraindicações:", 12, True, 29),
            p("Pessoa com neoplasia maligna.", pagina=29),
            p("Informações Gerais", 12, True, 55),
            p("Vacinar antes da imunossupressão.", pagina=55),
        ],
        auditoria,
    )
    assert [(b.secao, b.entidade) for b in blocos] == [
        ("indicacoes", "dtpa"),
        ("esquema_vacinal", "dtpa"),
        ("contraindicacoes", "dtpa"),
        ("esquema_vacinal", "dtpa"),
        ("contraindicacoes", "febre_amarela"),
        ("condutas_gerais", None),
    ]
    assert blocos[1].publico_alvo == ["adulto", "gestante"]
    assert blocos[4].titulo_secao.endswith("> Contraindicações")
    assert len(auditoria.descartados) == 2


def test_quebra_de_paragrafo_entre_nome_da_vacina_e_subtitulo() -> None:
    from src.rag.extracao import Linha
    from src.rag.limpeza import juntar_paragrafos
    from src.rag.secoes import _marcar_titulos_calendario, _quebras_calendario

    linhas = [
        Linha("13. Vacina febre amarela (atenuada) - VFA", 1, 12, True),
        Linha("Indicação", 1, 12, False),
        Linha("Prevenção da febre amarela.", 1, 12, False),
        Linha("Dose: 0,5 mL.", 1, 12, False),
    ]
    paragrafos = juntar_paragrafos(
        linhas, _marcar_titulos_calendario(linhas), False, _quebras_calendario(linhas)
    )
    assert [(x.texto, x.candidato_titulo) for x in paragrafos] == [
        ("13. Vacina febre amarela (atenuada) - VFA", True),
        ("Indicação", True),
        ("Prevenção da febre amarela.", False),
        ("Dose: 0,5 mL.", False),
    ]
