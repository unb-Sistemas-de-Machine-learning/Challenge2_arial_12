from src.rag.catalogo import Fonte
from src.rag.chunking import (
    ALVO_CARACTERES,
    MAXIMO_CARACTERES,
    montar_chunks,
    texto_para_embedding,
)
from src.rag.metadados import validar_lote
from src.rag.secoes import Auditoria, Bloco

FONTE = Fonte.model_validate(
    {
        "doc_id": "DOC-MS-PROTOCOLO-DENGUE",
        "slug": "ms-dengue-6ed",
        "arquivo": "teste.pdf",
        "sha256": "0" * 64,
        "orgao_emissor": "MINISTERIO_DA_SAUDE",
        "titulo_documento": "Dengue: diagnóstico e manejo clínico",
        "categoria": "protocolo_clinico",
        "jornada": "pedro",
        "entidade_principal": "dengue",
        "publico_alvo": ["geral"],
        "data_publicacao": "2024",
        "url_referencia": "https://www.gov.br/saude/",
        "data_coleta": "2026-11-25",
        "data_verificacao_vigencia": "2026-11-25",
        "situacao_vigencia": "vigente",
        "evidencia_vigencia": "teste",
    }
)


def bloco(
    texto, secao="manejo_clinico", titulo="6.1.2 Conduta", pagina=29, publico=None
):
    return Bloco(texto, pagina, secao, titulo, publico or ["geral"])


def frase(n: int) -> str:
    return f"Frase número {n} sobre hidratação oral e repouso do paciente. "


def montar(blocos):
    return montar_chunks(FONTE, blocos, "corpus-v1.0.0", Auditoria())


def test_chunk_nunca_atravessa_secao_ou_titulo() -> None:
    chunks = montar(
        [
            bloco("a. Orientar hidratação oral abundante e repouso em casa."),
            bloco(
                "c. Não utilizar salicilatos ou anti-inflamatórios não esteroides.",
                secao="contraindicacoes",
            ),
            bloco("d. Orientar repouso e prescrever dieta conforme o quadro."),
            bloco("Dor abdominal intensa e vômitos persistentes.", titulo="Alarme"),
        ]
    )
    assert [c.metadados.secao for c in chunks] == [
        "manejo_clinico",
        "contraindicacoes",
        "manejo_clinico",
        "manejo_clinico",
    ]
    assert chunks[1].texto.startswith("c. Não utilizar salicilatos")
    assert [c.metadados.ordem for c in chunks] == [0, 1, 2, 3]


def test_empacota_paragrafos_ate_o_alvo_sem_cortar() -> None:
    paragrafos = [frase(i) * 3 for i in range(10)]  # cerca de 180 caracteres cada
    chunks = montar([bloco(t) for t in paragrafos])
    assert all(len(c.texto) <= ALVO_CARACTERES for c in chunks)
    reconstruido = [t for c in chunks for t in c.texto.split("\n")]
    assert reconstruido == [t.strip() for t in paragrafos]


def test_paragrafo_longo_e_dividido_por_frases() -> None:
    longo = "".join(frase(i) for i in range(60)).strip()
    chunks = montar([bloco(longo)])
    assert len(chunks) > 1
    assert all(len(c.texto) <= MAXIMO_CARACTERES for c in chunks)
    assert all(c.texto.rstrip().endswith(".") for c in chunks)


def test_pedaco_pequeno_e_absorvido_pelo_vizinho() -> None:
    chunks = montar([bloco("Ver Quadro 3."), bloco(frase(1) + frase(2))])
    assert len(chunks) == 1
    assert chunks[0].texto.startswith("Ver Quadro 3.")


def test_secao_inteira_pequena_e_descartada_com_registro() -> None:
    auditoria = Auditoria()
    chunks = montar_chunks(FONTE, [bloco("Ver Quadro 3.")], "corpus-v1.0.0", auditoria)
    assert chunks == []
    assert "menos de 30" in auditoria.descartados[0]["motivo"]


def test_ids_deterministicos_unicos_e_validos() -> None:
    blocos = [bloco(frase(i) * 6, pagina=29 + i // 3) for i in range(9)]
    primeira, segunda = montar(blocos), montar(blocos)
    assert [c.chunk_id for c in primeira] == [c.chunk_id for c in segunda]
    assert primeira[0].chunk_id == "ms-dengue-6ed-manejo-clinico-p29-c01"
    validar_lote(primeira)


def test_publico_alvo_e_a_uniao_dos_blocos() -> None:
    chunks = montar(
        [
            bloco("Conduta para a gestante com dengue.", publico=["geral", "gestante"]),
            bloco("Conduta para o idoso com dengue.", publico=["geral", "idoso"]),
        ]
    )
    assert chunks[0].metadados.publico_alvo == ["geral", "gestante", "idoso"]


def test_texto_para_embedding_leva_documento_secao_e_titulo() -> None:
    trecho = "c. Não utilizar salicilatos ou anti-inflamatórios."
    chunk = montar([bloco(trecho, secao="contraindicacoes")])[0]
    texto = texto_para_embedding(chunk)
    assert texto.splitlines()[:2] == [
        "Dengue: diagnóstico e manejo clínico",
        "Contraindicações — 6.1.2 Conduta",
    ]
    assert texto.endswith(trecho)
    assert chunk.texto == trecho


def test_entidade_do_bloco_vai_para_o_chunk_e_separa_grupos() -> None:
    chunks = montar(
        [
            Bloco(
                "Gestante: 1 dose de dTpa a cada gravidez.",
                2,
                "esquema_vacinal",
                "V",
                ["geral"],
                "dtpa",
            ),
            Bloco(
                "Gestante: 1 dose de influenza por temporada.",
                2,
                "esquema_vacinal",
                "V",
                ["geral"],
                "influenza",
            ),
            Bloco(
                "Informações gerais sobre o calendário nacional.",
                3,
                "condutas_gerais",
                "G",
                ["geral"],
            ),
        ]
    )
    assert [c.metadados.entidade_principal for c in chunks] == [
        "dtpa",
        "influenza",
        "dengue",
    ]
