import pytest
from pydantic import ValidationError

from src.rag.metadados import (
    Chunk,
    ErroQualidade,
    MetadadosChunk,
    de_chroma,
    para_chroma,
    validar_lote,
)

TEXTO = (
    "Os anti-inflamatórios não esteroidais são contraindicados em pacientes "
    "com suspeita de dengue."
)


def metadados(**alteracoes) -> dict:
    base = {
        "orgao_emissor": "MINISTERIO_DA_SAUDE",
        "titulo_documento": "Dengue: diagnóstico e manejo clínico (6ª edição)",
        "categoria": "protocolo_clinico",
        "secao": "contraindicacoes",
        "publico_alvo": ["geral", "pacientes_com_dengue"],
        "doc_id": "DOC-MS-PROTOCOLO-DENGUE",
        "entidade_principal": "dengue",
        "versao_ingestao": "corpus-v1.0.0",
        "data_publicacao": "2024",
        "pagina_origem": 31,
    }
    base.update(alteracoes)
    return base


def chunk(chunk_id: str = "ms-dengue-6ed-contraindicacoes-p31-c01", **alt) -> dict:
    return {"chunk_id": chunk_id, "texto": TEXTO, "metadados": metadados(**alt)}


def test_chunk_valido() -> None:
    validado = Chunk.model_validate(chunk())
    assert validado.metadados.publico_alvo == ["geral", "pacientes_com_dengue"]


@pytest.mark.parametrize(
    "campo",
    ["orgao_emissor", "titulo_documento", "categoria", "secao", "publico_alvo"],
)
def test_rejeita_campo_obrigatorio_ausente(campo: str) -> None:
    bruto = chunk()
    del bruto["metadados"][campo]
    with pytest.raises(ValidationError):
        Chunk.model_validate(bruto)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("titulo_documento", "   "),
        ("publico_alvo", []),
        ("orgao_emissor", "OMS"),
        ("categoria", "artigo"),
        ("secao", "posologia"),
        ("publico_alvo", ["gestante", "criancas"]),
        ("publico_alvo", ["gestante", "gestante"]),
        ("versao_ingestao", "v1"),
        ("data_publicacao", "2024-13"),
    ],
)
def test_rejeita_valor_fora_do_contrato(campo: str, valor) -> None:
    with pytest.raises(ValidationError):
        Chunk.model_validate(chunk(**{campo: valor}))


def test_rejeita_texto_com_menos_de_30_caracteres_uteis() -> None:
    bruto = chunk()
    bruto["texto"] = "Não usar.   " + " " * 100 + "Procurar UBS."
    with pytest.raises(ValidationError):
        Chunk.model_validate(bruto)


def test_conversao_chroma_ida_e_volta_omite_nulos() -> None:
    original = MetadadosChunk.model_validate(metadados(data_publicacao=None))
    gravado = para_chroma(original)
    assert "data_publicacao" not in gravado
    assert "url_referencia" not in gravado
    assert gravado["publico_alvo"] == ["geral", "pacientes_com_dengue"]
    assert de_chroma(gravado) == original


def test_validar_lote_junta_todos_os_problemas() -> None:
    lote = [
        chunk("c-01"),
        chunk("c-02", secao="posologia"),
        chunk("c-01"),
        {"chunk_id": "c-03", "texto": "curto", "metadados": metadados()},
    ]
    with pytest.raises(ErroQualidade) as erro:
        validar_lote(lote)
    problemas = erro.value.problemas
    assert len(problemas) == 3
    assert any(p.startswith("c-02: metadados.secao") for p in problemas)
    assert any("chunk_id repetido" in p for p in problemas)
    assert any(p.startswith("c-03: texto") for p in problemas)


def test_validar_lote_devolve_chunks_validos() -> None:
    validos = validar_lote([chunk("c-01"), chunk("c-02")])
    assert [c.chunk_id for c in validos] == ["c-01", "c-02"]
