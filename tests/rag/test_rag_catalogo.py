from pathlib import Path

import pytest
from pydantic import ValidationError

from src.rag.catalogo import (
    Catalogo,
    ErroIntegridade,
    carregar_catalogo,
    sha256_arquivo,
    verificar_integridade,
)

CONTEUDO_PDF = b"%PDF-1.7 conteudo de teste"


def fonte(**alteracoes) -> dict:
    base = {
        "doc_id": "DOC-MS-PROTOCOLO-DENGUE",
        "slug": "ms-dengue-6ed",
        "arquivo": "ms-protocolo-dengue-6ed.pdf",
        "sha256": "0" * 64,
        "orgao_emissor": "MINISTERIO_DA_SAUDE",
        "titulo_documento": "Dengue: diagnóstico e manejo clínico (6ª edição)",
        "categoria": "protocolo_clinico",
        "jornada": "pedro",
        "entidade_principal": "dengue",
        "publico_alvo": ["geral", "pacientes_com_dengue"],
        "data_publicacao": "2024",
        "url_referencia": "https://www.gov.br/saude/",
        "data_coleta": "2026-11-25",
        "data_verificacao_vigencia": "2026-11-25",
        "situacao_vigencia": "vigente",
        "evidencia_vigencia": "Edição mais recente listada no portal do MS.",
        "paginas": [[5, 7], [10, 12]],
        "regras_secao": [
            {"padrao": r"(?i)^sinais de alarme", "secao": "sinais_de_alarme"}
        ],
    }
    base.update(alteracoes)
    return base


def test_catalogo_valido() -> None:
    catalogo = Catalogo.model_validate(
        {"versao_corpus": "corpus-v1.0.0", "fontes": [fonte()]}
    )
    dengue = catalogo.fonte("DOC-MS-PROTOCOLO-DENGUE")
    assert dengue.paginas == [(5, 7), (10, 12)]
    assert dengue.paginas_processadas(20) == [5, 6, 7, 10, 11, 12]
    with pytest.raises(ValueError, match="além do total"):
        dengue.paginas_processadas(11)
    with pytest.raises(KeyError):
        catalogo.fonte("DOC-INEXISTENTE")


def test_sem_paginas_processa_documento_inteiro() -> None:
    catalogo = Catalogo.model_validate(
        {"versao_corpus": "corpus-v1.0.0", "fontes": [fonte(paginas=None)]}
    )
    assert catalogo.fontes[0].paginas_processadas(3) == [1, 2, 3]


@pytest.mark.parametrize("campo", ["doc_id", "slug", "arquivo"])
def test_rejeita_identificadores_repetidos(campo: str) -> None:
    outra = fonte(
        doc_id="DOC-MS-GUIA-MALARIA",
        slug="ms-malaria-3ed",
        arquivo="ms-guia-malaria.pdf",
    )
    outra[campo] = fonte()[campo]
    with pytest.raises(ValidationError, match="repetido"):
        Catalogo.model_validate(
            {"versao_corpus": "corpus-v1.0.0", "fontes": [fonte(), outra]}
        )


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("arquivo", "../segredo.pdf"),
        ("arquivo", "bula.docx"),
        ("sha256", "abc"),
        ("situacao_vigencia", "revogado"),
        ("paginas", [[10, 2]]),
        ("paginas", [[1, 5], [4, 8]]),
        ("paginas", []),
        ("registro_anvisa", "105350230"),
        ("regras_secao", [{"padrao": "(", "secao": "manejo_clinico"}]),
        ("regras_secao", [{"padrao": "x", "secao": "posologia"}]),
        ("regras_entidade", [{"padrao": "(", "entidade": "dtpa"}]),
        ("regras_entidade", [{"padrao": "dTpa", "entidade": "dTpa adulto"}]),
    ],
)
def test_rejeita_fonte_invalida(campo: str, valor) -> None:
    with pytest.raises(ValidationError):
        Catalogo.model_validate(
            {"versao_corpus": "corpus-v1.0.0", "fontes": [fonte(**{campo: valor})]}
        )


def test_carrega_catalogo_toml(tmp_path: Path) -> None:
    caminho = tmp_path / "catalogo.toml"
    caminho.write_text(
        """
versao_corpus = "corpus-v1.0.0"

[[fontes]]
doc_id = "DOC-ANVISA-BULA-IBUPROFENO"
slug = "anvisa-bula-ibuprofeno"
arquivo = "anvisa-bula-ibuprofeno.pdf"
sha256 = "%s"
orgao_emissor = "ANVISA"
titulo_documento = "Bula do paciente - Ibuprofeno"
categoria = "bula_medicamento"
jornada = "pedro"
entidade_principal = "ibuprofeno"
publico_alvo = ["geral"]
data_publicacao = "2025-03"
url_referencia = "https://consultas.anvisa.gov.br/#/bulario/"
data_coleta = 2026-11-25
data_verificacao_vigencia = 2026-11-25
situacao_vigencia = "vigente"
evidencia_vigencia = "Versão mais recente no Bulário Eletrônico."
"""
        % ("a" * 64),
        encoding="utf-8",
    )
    catalogo = carregar_catalogo(caminho)
    assert catalogo.fontes[0].regras_secao == []
    assert catalogo.fontes[0].paginas is None


def test_verificar_integridade(tmp_path: Path) -> None:
    pdf = tmp_path / "ms-protocolo-dengue-6ed.pdf"
    pdf.write_bytes(CONTEUDO_PDF)
    correto = Catalogo.model_validate(
        {
            "versao_corpus": "corpus-v1.0.0",
            "fontes": [fonte(sha256=sha256_arquivo(pdf))],
        }
    )
    verificar_integridade(correto, tmp_path)

    alterado = Catalogo.model_validate(
        {"versao_corpus": "corpus-v1.0.0", "fontes": [fonte(sha256="f" * 64)]}
    )
    with pytest.raises(ErroIntegridade, match="sha256 diferente"):
        verificar_integridade(alterado, tmp_path)

    pdf.unlink()
    with pytest.raises(ErroIntegridade, match="arquivo ausente"):
        verificar_integridade(correto, tmp_path)
