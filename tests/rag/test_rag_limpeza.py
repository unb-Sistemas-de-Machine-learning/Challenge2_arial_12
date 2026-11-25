from src.rag.extracao import Linha
from src.rag.limpeza import (
    descartar_boilerplate,
    juntar_paragrafos,
    normalizar_texto,
    remover_ruido,
)


def linha(
    texto: str,
    pagina: int = 1,
    tamanho: float = 10.0,
    negrito: bool = False,
    y: float = 0.5,
    horizontal: bool = True,
):
    return Linha(texto, pagina, tamanho, negrito, y_relativo=y, horizontal=horizontal)


def test_normalizar_texto() -> None:
    assert normalizar_texto("  ime­diata­mente  ") == "imediatamente"
    assert normalizar_texto("ﬁbra\tde   ﬂor") == "fibra de flor"
    assert normalizar_texto("\x17 Oferecer O2") == "• Oferecer O2"
    assert normalizar_texto("• \x17 Falta de ar") == "• Falta de ar"


def test_remove_cabecalho_repetido_numero_de_pagina_e_texto_miudo() -> None:
    linhas = []
    for pagina in range(1, 5):
        linhas += [
            linha("Dengue: diagnóstico e manejo clínico | adulto", pagina, 7, y=0.04),
            linha(f"Conteúdo clínico da página {pagina}.", pagina),
            linha("Dose: 0,5 mL.", pagina),  # repete no corpo: é conteúdo
            linha("12", pagina),  # número no corpo (célula de tabela): fica
            linha("seta do fluxograma", pagina, 3.2),
            linha(str(pagina + 10), pagina, 7, y=0.96),
        ]
    linhas.append(linha("Ibuprofeno_Bula_Paciente Página 3 de 11", 4))
    limpas = remover_ruido(linhas)
    assert [x.texto for x in limpas] == [
        texto
        for p in range(1, 5)
        for texto in (f"Conteúdo clínico da página {p}.", "Dose: 0,5 mL.", "12")
    ]


def test_remove_cabecalho_girado_na_lateral() -> None:
    linhas = []
    for pagina in range(1, 5):
        linhas += [
            linha(
                "Dengue: manejo clínico | adulto", pagina, 7, y=0.76, horizontal=False
            ),
            linha(f"Conduta descrita na página {pagina}.", pagina),
        ]
    assert [x.texto for x in remover_ruido(linhas)] == [
        f"Conduta descrita na página {p}." for p in range(1, 5)
    ]


def test_remove_carimbos_do_sei() -> None:
    linhas = [
        linha("04/03/2024, 11:09 SEI/MS - 0039050923 - Nota Técnica Conjunta"),
        linha("Nota Técnica 119 (0051250997) SEI 25000.126136/2024-55 / pg. 4"),
        linha("2.1. A dengue é uma doença infecciosa febril aguda."),
    ]
    assert [x.texto for x in remover_ruido(linhas)] == [linhas[2].texto]


def test_junta_linhas_e_separa_itens_de_lista() -> None:
    paragrafos = juntar_paragrafos(
        [
            linha("b. Prescrever paracetamol e/ou dipirona, conforme orientações"),
            linha("do Apêndice H."),
            linha("c. Não utilizar salicilatos ou anti-inflamatórios não esteroides"),
            linha("e corticosteroides."),
            linha("Orientar o paciente a não se automedicar e a procurar ime­"),
            linha("diatamente o serviço de urgência; e usar anti-"),
            linha("inflamatório só com prescrição."),
        ]
    )
    assert [p.texto for p in paragrafos] == [
        "b. Prescrever paracetamol e/ou dipirona, conforme orientações do Apêndice H.",
        (
            "c. Não utilizar salicilatos ou anti-inflamatórios não esteroides "
            "e corticosteroides."
        ),
        (
            "Orientar o paciente a não se automedicar e a procurar imediatamente o "
            "serviço de urgência; e usar anti-inflamatório só com prescrição."
        ),
    ]


def test_paragrafo_continua_na_pagina_seguinte() -> None:
    paragrafos = juntar_paragrafos(
        [linha("Os AINEs podem causar sangramento", 1), linha("gastrintestinal.", 2)]
    )
    assert len(paragrafos) == 1
    assert paragrafos[0].pagina == 1


def test_subtitulo_em_negrito_vira_paragrafo_proprio() -> None:
    paragrafos = juntar_paragrafos(
        [
            linha("Efeitos cardíacos", negrito=True),
            linha("Os AINEs podem aumentar o risco de eventos trombóticos."),
        ]
    )
    assert [(p.texto, p.candidato_titulo) for p in paragrafos] == [
        ("Efeitos cardíacos", True),
        ("Os AINEs podem aumentar o risco de eventos trombóticos.", False),
    ]


def test_titulo_marcado_em_duas_linhas_e_mudanca_de_tamanho() -> None:
    linhas = [
        linha("6.5 CONSIDERAÇÕES IMPORTANTES PARA", tamanho=14, negrito=True),
        linha("OS GRUPOS C E D", tamanho=14, negrito=True),
        linha("a. Oferecer oxigênio em todas as situações de choque."),
    ]
    paragrafos = juntar_paragrafos(linhas, [True, True, False])
    assert [p.texto for p in paragrafos] == [
        "6.5 CONSIDERAÇÕES IMPORTANTES PARA OS GRUPOS C E D",
        "a. Oferecer oxigênio em todas as situações de choque.",
    ]


def test_descarta_assinatura_eletronica() -> None:
    paragrafos = juntar_paragrafos(
        [
            linha("3.1. Suspender a amamentação por 15 dias após a vacinação."),
            linha("Documento assinado eletronicamente por Fulano de Tal, Diretor."),
        ]
    )
    restantes = descartar_boilerplate(paragrafos)
    assert [p.texto for p in restantes] == [paragrafos[0].texto]
