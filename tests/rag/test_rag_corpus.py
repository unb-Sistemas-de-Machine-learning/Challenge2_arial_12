"""Testes do corpus real: catálogo, PDFs de data/raw e ligação com o golden dataset."""

import pymupdf
import pytest

from src.eval.golden_dataset import carregar_golden_dataset
from src.rag.catalogo import Catalogo, carregar_catalogo, verificar_integridade
from src.rag.chunking import montar_chunks
from src.rag.config import DIR_RAW
from src.rag.metadados import Chunk, validar_lote
from src.rag.secoes import CATEGORIAS_SUPORTADAS, processar_fonte


@pytest.fixture(scope="module")
def catalogo() -> Catalogo:
    return carregar_catalogo()


@pytest.fixture(scope="module")
def chunks(catalogo: Catalogo) -> list[Chunk]:
    """Chunks reais dos documentos cujas categorias já têm estratégia de seções."""
    gerados: list[Chunk] = []
    for fonte in catalogo.fontes:
        if fonte.categoria in CATEGORIAS_SUPORTADAS:
            blocos, auditoria = processar_fonte(fonte, DIR_RAW)
            gerados += montar_chunks(fonte, blocos, catalogo.versao_corpus, auditoria)
    return gerados


def test_chunks_reais_passam_no_quality_gate(chunks: list[Chunk]) -> None:
    assert chunks
    validar_lote(chunks)


def test_todo_documento_processado_gera_chunks(
    catalogo: Catalogo, chunks: list[Chunk]
) -> None:
    com_chunks = {c.metadados.doc_id for c in chunks}
    for fonte in catalogo.fontes:
        if fonte.categoria in CATEGORIAS_SUPORTADAS:
            assert fonte.doc_id in com_chunks


def test_toda_bula_tem_chunk_de_contraindicacoes(
    catalogo: Catalogo, chunks: list[Chunk]
) -> None:
    pares = {(c.metadados.doc_id, c.metadados.secao) for c in chunks}
    for fonte in catalogo.fontes:
        if fonte.categoria.startswith("bula_"):
            assert (fonte.doc_id, "contraindicacoes") in pares, fonte.doc_id


def test_chunks_cobrem_as_fontes_esperadas_do_golden_dataset(
    catalogo: Catalogo, chunks: list[Chunk]
) -> None:
    """Cada (doc_id, secao) citado pelo gabarito precisa existir no índice."""
    categoria = {f.doc_id: f.categoria for f in catalogo.fontes}
    pares = {(c.metadados.doc_id, c.metadados.secao) for c in chunks}
    golden = carregar_golden_dataset()
    faltando = {
        (f.doc_id, f.secao)
        for caso in golden.casos
        for f in caso.gabarito.fontes_esperadas
        if categoria[f.doc_id] in CATEGORIAS_SUPORTADAS
    } - pares
    assert not faltando


def test_chunks_reais_nao_tem_cabecalho_nem_numero_de_pagina(
    chunks: list[Chunk],
) -> None:
    ruido = ("Bula_Paciente", "| adulto e criança", "VENDA PROIBIDA", "ࡿ")
    for chunk in chunks:
        assert not any(r in chunk.texto for r in ruido), chunk.chunk_id
        assert not any(linha.strip().isdigit() for linha in chunk.texto.splitlines())


def test_corpus_tem_de_10_a_12_documentos(catalogo: Catalogo) -> None:
    assert 10 <= len(catalogo.fontes) <= 12


def test_cobre_anvisa_e_ministerio_da_saude(catalogo: Catalogo) -> None:
    orgaos = {f.orgao_emissor for f in catalogo.fontes}
    assert orgaos == {"ANVISA", "MINISTERIO_DA_SAUDE"}


def test_pdfs_batem_com_o_sha256_do_catalogo(catalogo: Catalogo) -> None:
    verificar_integridade(catalogo, DIR_RAW)


def test_data_raw_nao_tem_pdf_fora_do_catalogo(catalogo: Catalogo) -> None:
    no_disco = {p.name for p in DIR_RAW.glob("*.pdf")}
    assert no_disco == {f.arquivo for f in catalogo.fontes}


def test_paginas_processadas_existem_e_tem_texto(catalogo: Catalogo) -> None:
    for fonte in catalogo.fontes:
        with pymupdf.open(DIR_RAW / fonte.arquivo) as documento:
            paginas = fonte.paginas_processadas(documento.page_count)
            com_texto = [p for p in paginas if documento[p - 1].get_text().strip()]
        assert len(com_texto) >= 0.9 * len(paginas), fonte.doc_id


def test_bulas_tem_registro_e_detentor(catalogo: Catalogo) -> None:
    for fonte in catalogo.fontes:
        if fonte.categoria.startswith("bula_"):
            assert fonte.registro_anvisa and fonte.detentor_registro, fonte.doc_id


def test_catalogo_cobre_documentos_do_golden_dataset(catalogo: Catalogo) -> None:
    golden = carregar_golden_dataset()
    por_id = {f.doc_id: f for f in catalogo.fontes}
    for referencia in golden.documentos_referencia:
        fonte = por_id.get(referencia.doc_id)
        assert fonte is not None, f"{referencia.doc_id} ausente do catálogo"
        assert fonte.orgao_emissor == referencia.orgao_emissor
        assert fonte.categoria == referencia.categoria
        assert fonte.titulo_documento == referencia.titulo_documento
