"""Manifesto de versão do índice vetorial, para rastreabilidade no MLOps (issue #11).

O ``hash_indice`` depende só do conteúdo (PDFs, chunks, modelo e parâmetros),
não da data nem dos arquivos binários do ChromaDB, cujo índice HNSW não sai
idêntico a cada execução. Duas cargas com as mesmas entradas geram o mesmo hash.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from src.rag.catalogo import Fonte
from src.rag.config import RAIZ
from src.rag.metadados import Chunk

NOME_ARQUIVO = "manifest.json"


def _sha256_json(valor: Any) -> str:
    texto = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def hash_chunks(chunks: Sequence[Chunk]) -> str:
    """sha256 do JSONL canônico dos chunks, ordenados por ``chunk_id``."""
    resumo = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda c: c.chunk_id):
        linha = json.dumps(
            chunk.model_dump(exclude_none=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        resumo.update(linha.encode("utf-8") + b"\n")
    return resumo.hexdigest()


def hash_corpus(fontes: Sequence[Fonte]) -> str:
    return _sha256_json(sorted(f"{f.doc_id}:{f.sha256}" for f in fontes))


def _commit_git() -> dict[str, Any] | None:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        sujo = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit, "alteracoes_nao_commitadas": bool(sujo)}


def _versao(pacote: str) -> str | None:
    try:
        return version(pacote)
    except PackageNotFoundError:
        return None


def montar_manifesto(
    *,
    versao_corpus: str,
    fontes: Sequence[Fonte],
    chunks: Sequence[Chunk],
    parametros_chunking: dict[str, Any],
    modelo_embedding: dict[str, Any],
    base_vetorial: dict[str, Any],
    parcial: bool,
    comando: str,
) -> dict[str, Any]:
    por_doc: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        por_doc.setdefault(chunk.metadados.doc_id, []).append(chunk)
    hashes = {
        "hash_corpus": hash_corpus(fontes),
        "hash_chunks": hash_chunks(chunks),
    }
    hashes["hash_indice"] = _sha256_json(
        {
            **hashes,
            "modelo_embedding": modelo_embedding,
            "parametros_chunking": parametros_chunking,
        }
    )
    return {
        "versao_corpus": versao_corpus,
        "parcial": parcial,
        **hashes,
        "gerado_em": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git": _commit_git(),
        "comando": comando,
        "parametros_chunking": parametros_chunking,
        "modelo_embedding": modelo_embedding,
        "base_vetorial": base_vetorial,
        "bibliotecas": {
            p: _versao(p) for p in ("chromadb", "pymupdf", "fastembed", "pydantic")
        },
        "contagens": {
            "chunks": len(chunks),
            "por_categoria": dict(
                sorted(Counter(c.metadados.categoria for c in chunks).items())
            ),
            "por_secao": dict(
                sorted(Counter(c.metadados.secao for c in chunks).items())
            ),
        },
        "fontes": [
            {
                "doc_id": f.doc_id,
                "arquivo": f.arquivo,
                "sha256": f.sha256,
                "paginas": f.paginas,
                "chunks": len(por_doc.get(f.doc_id, [])),
                "por_secao": dict(
                    sorted(
                        Counter(
                            c.metadados.secao for c in por_doc.get(f.doc_id, [])
                        ).items()
                    )
                ),
            }
            for f in fontes
        ],
    }


def gravar_manifesto(
    manifesto: dict[str, Any], dir_vectorstore: Path, dir_manifests: Path | None
) -> list[Path]:
    """Grava o manifesto no vectorstore e, se pedido, a cópia versionada."""
    texto = json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n"
    destinos = [dir_vectorstore / NOME_ARQUIVO]
    if dir_manifests is not None:
        destinos.append(dir_manifests / f"{manifesto['versao_corpus']}.json")
    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return destinos
