"""Pipeline batch de ingestão do corpus oficial (issue #11).

Uso, na raiz do repositório::

    uv run python -m src.rag.ingestao                # corpus inteiro
    uv run python -m src.rag.ingestao --doc DOC-MS-PROTOCOLO-DENGUE
    uv run python -m src.rag.ingestao --sem-embeddings   # só valida e gera os chunks

Etapas: integridade dos PDFs (sha256) → extração → limpeza → seções → chunking →
quality gate → embeddings → ChromaDB em ``data/vectorstore/`` → manifesto.
Qualquer chunk inválido interrompe a carga antes de gravar a base vetorial.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.rag import config
from src.rag.catalogo import (
    Catalogo,
    ErroIntegridade,
    carregar_catalogo,
    verificar_integridade,
)
from src.rag.chunking import ALVO_CARACTERES, MAXIMO_CARACTERES, montar_chunks
from src.rag.indexacao import (
    MODELO_PADRAO,
    MODELOS,
    Embedder,
    EmbedderFastEmbed,
    gerar_embeddings,
    gravar_indice,
)
from src.rag.manifesto import gravar_manifesto, montar_manifesto
from src.rag.metadados import (
    MIN_CARACTERES_UTEIS,
    Chunk,
    ErroQualidade,
    validar_lote,
)
from src.rag.secoes import EstrategiaIndisponivel, processar_fonte

PARAMETROS_CHUNKING = {
    "alvo_caracteres": ALVO_CARACTERES,
    "maximo_caracteres": MAXIMO_CARACTERES,
    "min_caracteres_uteis": MIN_CARACTERES_UTEIS,
    "fronteira": "secao_e_titulo",
    "texto_embedding": "titulo_documento + secao + titulo_secao + trecho",
}


@dataclass
class Caminhos:
    raw: Path = config.DIR_RAW
    processed: Path = config.DIR_PROCESSED
    vectorstore: Path = config.DIR_VECTORSTORE
    manifests: Path = config.DIR_MANIFESTS


@dataclass
class Resultado:
    chunks: list[Chunk]
    auditoria: dict[str, Any]
    manifesto: dict[str, Any] | None = None
    arquivos: list[Path] = field(default_factory=list)


def executar(
    catalogo: Catalogo,
    caminhos: Caminhos,
    embedder: Embedder | None,
    doc_ids: list[str] | None = None,
    comando: str = "python -m src.rag.ingestao",
) -> Resultado:
    """Roda o pipeline. Sem ``embedder``, para depois do quality gate."""
    fontes = [catalogo.fonte(d) for d in doc_ids] if doc_ids else list(catalogo.fontes)
    verificar_integridade(
        Catalogo(versao_corpus=catalogo.versao_corpus, fontes=fontes), caminhos.raw
    )

    chunks: list[Chunk] = []
    auditoria: dict[str, Any] = {}
    for fonte in fontes:
        blocos, registro = processar_fonte(fonte, caminhos.raw)
        chunks_fonte = montar_chunks(fonte, blocos, catalogo.versao_corpus, registro)
        chunks.extend(chunks_fonte)
        auditoria[fonte.doc_id] = {"chunks": len(chunks_fonte), **asdict(registro)}

    chunks = validar_lote(chunks)

    caminhos.processed.mkdir(parents=True, exist_ok=True)
    jsonl = caminhos.processed / "chunks.jsonl"
    jsonl.write_text(
        "".join(
            json.dumps(c.model_dump(exclude_none=True), ensure_ascii=False) + "\n"
            for c in chunks
        ),
        encoding="utf-8",
    )
    relatorio = caminhos.processed / "auditoria.json"
    relatorio.write_text(
        json.dumps(auditoria, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    resultado = Resultado(
        chunks=chunks, auditoria=auditoria, arquivos=[jsonl, relatorio]
    )
    if embedder is None:
        return resultado

    embeddings = gerar_embeddings(chunks, embedder)
    parcial = doc_ids is not None and len(fontes) < len(catalogo.fontes)
    manifesto = montar_manifesto(
        versao_corpus=catalogo.versao_corpus,
        fontes=fontes,
        chunks=chunks,
        parametros_chunking=PARAMETROS_CHUNKING,
        modelo_embedding={
            "nome": embedder.nome,
            "dimensao": len(embeddings[0]) if embeddings else None,
            "prefixo_passagem": embedder.config.prefixo_passagem,
            "prefixo_consulta": embedder.config.prefixo_consulta,
        },
        base_vetorial={
            "motor": "chromadb",
            "colecao": config.NOME_COLECAO,
            "distancia": config.DISTANCIA,
            "caminho": "data/vectorstore",
        },
        parcial=parcial,
        comando=comando,
    )
    gravar_indice(
        chunks,
        embeddings,
        caminhos.vectorstore,
        metadados_colecao={
            "versao_corpus": catalogo.versao_corpus,
            "hash_indice": manifesto["hash_indice"],
            "modelo_embedding": embedder.nome,
            "prefixo_consulta": embedder.config.prefixo_consulta,
            "parcial": parcial,
        },
    )
    resultado.manifesto = manifesto
    # Só uma carga completa atualiza a cópia versionada em data/manifests/.
    resultado.arquivos += gravar_manifesto(
        manifesto, caminhos.vectorstore, None if parcial else caminhos.manifests
    )
    return resultado


def _resumo(resultado: Resultado) -> str:
    linhas = [f"{len(resultado.chunks)} chunks válidos"]
    for doc_id, dados in resultado.auditoria.items():
        linhas.append(
            f"  {doc_id}: {dados['chunks']} chunks, "
            f"{len(dados['reclassificados'])} reclassificados, "
            f"{len(dados['descartados'])} parágrafos descartados"
        )
    if resultado.manifesto:
        linhas.append(f"hash_indice: {resultado.manifesto['hash_indice']}")
    linhas += [f"gravado: {p.relative_to(config.RAIZ)}" for p in resultado.arquivos]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.rag.ingestao",
        description="Gera a base vetorial local a partir dos PDFs de data/raw/.",
    )
    parser.add_argument(
        "--doc",
        action="append",
        metavar="DOC_ID",
        help="Processa só este documento do catálogo (pode repetir).",
    )
    parser.add_argument(
        "--sem-embeddings",
        action="store_true",
        help="Para depois do quality gate, sem gerar embeddings nem a base vetorial.",
    )
    parser.add_argument("--modelo", default=MODELO_PADRAO, choices=sorted(MODELOS))
    parser.add_argument("--catalogo", type=Path, default=config.CAMINHO_CATALOGO)
    args = parser.parse_args(argv)

    comando = "python -m src.rag.ingestao " + " ".join(argv or sys.argv[1:])
    try:
        catalogo = carregar_catalogo(args.catalogo)
        embedder = None if args.sem_embeddings else EmbedderFastEmbed(args.modelo)
        resultado = executar(
            catalogo, Caminhos(), embedder, args.doc, comando=comando.strip()
        )
    except (ErroIntegridade, ErroQualidade, EstrategiaIndisponivel, KeyError) as erro:
        print(f"Falha na ingestão: {erro}", file=sys.stderr)
        return 1
    print(_resumo(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
