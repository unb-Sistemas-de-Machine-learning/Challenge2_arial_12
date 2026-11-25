"""Caminhos e parâmetros do pipeline de ingestão do RAG (issue #11)."""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_DADOS = RAIZ / "data"
DIR_RAW = DIR_DADOS / "raw"
DIR_PROCESSED = DIR_DADOS / "processed"
DIR_VECTORSTORE = DIR_DADOS / "vectorstore"
DIR_MANIFESTS = DIR_DADOS / "manifests"
CAMINHO_CATALOGO = DIR_DADOS / "catalogo_fontes.toml"

# Nome da coleção no ChromaDB. A issue #14 consulta esta coleção.
NOME_COLECAO = "evidencia_corpus"
DISTANCIA = "cosine"
