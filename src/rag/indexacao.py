"""Embeddings e gravação da base vetorial local no ChromaDB (issue #11).

Os embeddings rodam em CPU com o fastembed (ONNX), sem custo e sem torch. O
modelo, os prefixos e a dimensão vão para os metadados da coleção e para o
manifesto, para que a consulta (issue #14) use exatamente a mesma configuração.
"""

from __future__ import annotations

import hashlib
import math
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.rag.chunking import texto_para_embedding
from src.rag.config import DIR_DADOS, DISTANCIA, NOME_COLECAO
from src.rag.metadados import Chunk, para_chroma

MODELO_PADRAO = "intfloat/multilingual-e5-large"
DIR_MODELOS = Path(os.environ.get("EVIDENCIA_DIR_MODELOS", DIR_DADOS / "modelos"))
TAMANHO_LOTE = 32


@dataclass(frozen=True)
class ConfigModelo:
    prefixo_passagem: str
    prefixo_consulta: str


# Modelos multilíngues avaliados para o corpus (todos aceitam 512 tokens).
MODELOS: dict[str, ConfigModelo] = {
    "intfloat/multilingual-e5-large": ConfigModelo("passage: ", "query: "),
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": ConfigModelo("", ""),
}


class Embedder(Protocol):
    nome: str
    config: ConfigModelo

    def passagens(self, textos: Sequence[str]) -> list[list[float]]: ...

    def consulta(self, texto: str) -> list[float]: ...


class EmbedderFastEmbed:
    """Modelo real, baixado uma vez para ``data/modelos/`` (fora do Git)."""

    def __init__(self, nome: str = MODELO_PADRAO, dir_modelos: Path = DIR_MODELOS):
        from fastembed import TextEmbedding

        if nome not in MODELOS:
            raise ValueError(f"Modelo sem configuração de prefixos: {nome}")
        self.nome = nome
        self.config = MODELOS[nome]
        self._modelo = TextEmbedding(nome, cache_dir=str(dir_modelos))

    def passagens(self, textos: Sequence[str]) -> list[list[float]]:
        entradas = [self.config.prefixo_passagem + t for t in textos]
        return [v.tolist() for v in self._modelo.embed(entradas, batch_size=16)]

    def consulta(self, texto: str) -> list[float]:
        entrada = self.config.prefixo_consulta + texto
        return next(iter(self._modelo.embed([entrada]))).tolist()


class EmbedderDeterministico:
    """Embedder de teste: vetores derivados do sha256 do texto, sem download."""

    nome = "teste/deterministico-32"
    config = ConfigModelo("", "")

    def __init__(self, dimensao: int = 32):
        self.dimensao = dimensao

    def _vetor(self, texto: str) -> list[float]:
        bruto = hashlib.sha256(texto.encode("utf-8")).digest()
        valores = [(bruto[i % len(bruto)] - 127.5) for i in range(self.dimensao)]
        norma = math.sqrt(sum(v * v for v in valores)) or 1.0
        return [v / norma for v in valores]

    def passagens(self, textos: Sequence[str]) -> list[list[float]]:
        return [self._vetor(t) for t in textos]

    def consulta(self, texto: str) -> list[float]:
        return self._vetor(texto)


def gerar_embeddings(chunks: Sequence[Chunk], embedder: Embedder) -> list[list[float]]:
    return embedder.passagens([texto_para_embedding(c) for c in chunks])


def gravar_indice(
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
    dir_vectorstore: Path,
    metadados_colecao: dict[str, str | int | float | bool],
    nome_colecao: str = NOME_COLECAO,
) -> None:
    """Recria a coleção do zero com os chunks e embeddings informados."""
    import chromadb
    from chromadb.config import Settings

    if len(chunks) != len(embeddings):
        raise ValueError("Quantidade de chunks e de embeddings diferente.")
    dir_vectorstore.mkdir(parents=True, exist_ok=True)
    cliente = chromadb.PersistentClient(
        path=str(dir_vectorstore), settings=Settings(anonymized_telemetry=False)
    )
    if nome_colecao in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(nome_colecao)
    colecao = cliente.create_collection(
        nome_colecao,
        metadata={"hnsw:space": DISTANCIA, **metadados_colecao},
        embedding_function=None,
    )
    for inicio in range(0, len(chunks), TAMANHO_LOTE):
        lote = chunks[inicio : inicio + TAMANHO_LOTE]
        colecao.add(
            ids=[c.chunk_id for c in lote],
            documents=[c.texto for c in lote],
            embeddings=[list(e) for e in embeddings[inicio : inicio + TAMANHO_LOTE]],
            metadatas=[para_chroma(c.metadados) for c in lote],
        )
