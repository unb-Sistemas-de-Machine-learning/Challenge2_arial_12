"""Teste de ponta a ponta do pipeline com PDFs gerados e embedder determinístico."""

import json
from pathlib import Path

import chromadb
import pymupdf
import pytest
from chromadb.config import Settings

from src.rag.catalogo import Catalogo, ErroIntegridade, sha256_arquivo
from src.rag.config import NOME_COLECAO
from src.rag.indexacao import EmbedderDeterministico
from src.rag.ingestao import Caminhos, executar
from src.rag.metadados import de_chroma

BULA = [
    ("ibuprofeno", 20, True),
    ("APRESENTAÇÕES", 10, True),
    ("Cápsula gelatinosa mole de 600 mg.", 10, False),
    ("1. PARA QUE ESTE MEDICAMENTO É INDICADO?", 10, True),
    ("Este medicamento é indicado para o alívio da dor e da febre.", 10, False),
    ("3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?", 10, True),
    ("Este medicamento é contraindicado em caso de suspeita de dengue,", 10, False),
    ("pois pode aumentar o risco de sangramentos.", 10, False),
    ("4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?", 10, True),
    ("Uso durante a Gravidez", 10, True),
    ("Não se recomenda a administração de ibuprofeno durante a gravidez.", 10, False),
    ("6. COMO DEVO USAR ESTE MEDICAMENTO?", 10, True),
    ("Tome uma cápsula a cada oito horas, com água.", 10, False),
]

PROTOCOLO = [
    ("1 Manejo clínico da dengue", 18, True),
    ("1.1 Conduta", 14, True),
    ("a. Orientar hidratação oral abundante e repouso domiciliar.", 10, False),
    ("b. Não utilizar salicilatos ou anti-inflamatórios não esteroides.", 10, False),
    ("1.2 Sinais de alarme", 14, True),
    ("Dor abdominal intensa e vômitos persistentes exigem atendimento.", 10, False),
    ("2 Diagnóstico diferencial", 18, True),
    ("Este texto deve ser descartado pela regra do catálogo de teste.", 10, False),
]


def criar_pdf(caminho: Path, linhas: list[tuple[str, float, bool]]) -> None:
    documento = pymupdf.open()
    pagina = documento.new_page()
    y = 60.0
    for texto, tamanho, negrito in linhas:
        pagina.insert_text(
            (60, y), texto, fontsize=tamanho, fontname="hebo" if negrito else "helv"
        )
        y += tamanho * 1.9
    documento.save(caminho)


def fonte(doc_id, slug, arquivo, categoria, sha, **extra) -> dict:
    return {
        "doc_id": doc_id,
        "slug": slug,
        "arquivo": arquivo,
        "sha256": sha,
        "orgao_emissor": "ANVISA"
        if categoria.startswith("bula")
        else "MINISTERIO_DA_SAUDE",
        "titulo_documento": f"Documento de teste {slug}",
        "categoria": categoria,
        "jornada": "pedro",
        "entidade_principal": "teste",
        "publico_alvo": ["geral"],
        "data_publicacao": "2025",
        "url_referencia": "https://www.gov.br/saude/",
        "data_coleta": "2026-11-25",
        "data_verificacao_vigencia": "2026-11-25",
        "situacao_vigencia": "vigente",
        "evidencia_vigencia": "teste",
        **extra,
    }


@pytest.fixture
def ambiente(tmp_path: Path) -> tuple[Catalogo, Caminhos]:
    raw = tmp_path / "raw"
    raw.mkdir()
    criar_pdf(raw / "bula.pdf", BULA)
    criar_pdf(raw / "protocolo.pdf", PROTOCOLO)
    catalogo = Catalogo.model_validate(
        {
            "versao_corpus": "corpus-v0.0.1",
            "fontes": [
                fonte(
                    "DOC-ANVISA-BULA-TESTE",
                    "anvisa-bula-teste",
                    "bula.pdf",
                    "bula_medicamento",
                    sha256_arquivo(raw / "bula.pdf"),
                ),
                fonte(
                    "DOC-MS-PROTOCOLO-TESTE",
                    "ms-protocolo-teste",
                    "protocolo.pdf",
                    "protocolo_clinico",
                    sha256_arquivo(raw / "protocolo.pdf"),
                    publico_alvo=["geral", "pacientes_com_dengue"],
                    secao_padrao="manejo_clinico",
                    regras_secao=[
                        {"padrao": "sinais de alarme", "secao": "sinais_de_alarme"},
                        {"padrao": "diagn[óo]stico diferencial", "secao": "descartar"},
                    ],
                ),
            ],
        }
    )
    caminhos = Caminhos(
        raw=raw,
        processed=tmp_path / "processed",
        vectorstore=tmp_path / "vectorstore",
        manifests=tmp_path / "manifests",
    )
    return catalogo, caminhos


def test_pipeline_gera_indice_manifesto_e_chunks(ambiente) -> None:
    catalogo, caminhos = ambiente
    resultado = executar(catalogo, caminhos, EmbedderDeterministico())

    secoes = {(c.metadados.doc_id, c.metadados.secao) for c in resultado.chunks}
    assert secoes == {
        ("DOC-ANVISA-BULA-TESTE", "indicacoes"),
        ("DOC-ANVISA-BULA-TESTE", "contraindicacoes"),
        ("DOC-ANVISA-BULA-TESTE", "gravidez_e_lactacao"),
        ("DOC-MS-PROTOCOLO-TESTE", "manejo_clinico"),
        ("DOC-MS-PROTOCOLO-TESTE", "contraindicacoes"),
        ("DOC-MS-PROTOCOLO-TESTE", "sinais_de_alarme"),
    }
    textos = " ".join(c.texto for c in resultado.chunks)
    assert "Tome uma cápsula" not in textos  # posologia fica fora
    assert "descartado pela regra" not in textos

    colecao = chromadb.PersistentClient(
        path=str(caminhos.vectorstore), settings=Settings(anonymized_telemetry=False)
    ).get_collection(NOME_COLECAO)
    assert colecao.count() == len(resultado.chunks)
    assert colecao.metadata["hash_indice"] == resultado.manifesto["hash_indice"]
    contra = colecao.get(where={"secao": "contraindicacoes"})
    assert len(contra["ids"]) == 2
    for bruto in contra["metadatas"]:
        assert de_chroma(bruto).orgao_emissor in ("ANVISA", "MINISTERIO_DA_SAUDE")
    gestante = colecao.get(where={"publico_alvo": {"$contains": "gestante"}})
    assert len(gestante["ids"]) == 1

    manifesto = json.loads((caminhos.vectorstore / "manifest.json").read_text())
    assert manifesto["parcial"] is False
    assert manifesto["contagens"]["chunks"] == len(resultado.chunks)
    assert (caminhos.manifests / "corpus-v0.0.1.json").is_file()
    linhas = (caminhos.processed / "chunks.jsonl").read_text().splitlines()
    assert len(linhas) == len(resultado.chunks)


def test_hash_do_indice_e_reprodutivel(ambiente) -> None:
    catalogo, caminhos = ambiente
    primeiro = executar(catalogo, caminhos, EmbedderDeterministico())
    segundo = executar(catalogo, caminhos, EmbedderDeterministico())
    assert primeiro.manifesto["hash_indice"] == segundo.manifesto["hash_indice"]
    assert primeiro.manifesto["hash_chunks"] == segundo.manifesto["hash_chunks"]


def test_carga_parcial_nao_atualiza_manifesto_versionado(ambiente) -> None:
    catalogo, caminhos = ambiente
    resultado = executar(
        catalogo, caminhos, EmbedderDeterministico(), ["DOC-ANVISA-BULA-TESTE"]
    )
    assert resultado.manifesto["parcial"] is True
    assert not caminhos.manifests.exists()


def test_sem_embeddings_para_no_quality_gate(ambiente) -> None:
    catalogo, caminhos = ambiente
    resultado = executar(catalogo, caminhos, None)
    assert resultado.chunks and resultado.manifesto is None
    assert not caminhos.vectorstore.exists()


def test_pdf_alterado_interrompe_antes_de_gravar(ambiente) -> None:
    catalogo, caminhos = ambiente
    (caminhos.raw / "bula.pdf").write_bytes(b"%PDF-1.7 alterado")
    with pytest.raises(ErroIntegridade):
        executar(catalogo, caminhos, EmbedderDeterministico())
    assert not caminhos.vectorstore.exists()
