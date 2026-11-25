"""Avalia o Agente Estruturador/Roteador (issue #13) no golden dataset.

Para cada caso, roda o agente com o LLM real e compara com o gabarito:

* **rota**: ``rota_definida`` está em ``rotas_aceitas``;
* **agentes**: ``agentes_alvo`` é igual a ``agentes_esperados``;
* **abstenção**: casos com ``deve_abster`` não acionam nenhum especialista.

Uso (com a chave do LLM no ``.env``)::

    uv run --env-file .env python -m src.eval.roteamento
    uv run --env-file .env python -m src.eval.roteamento --casos GD-06,GD-19
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from src.agents.estruturador_roteador import estruturar_e_rotear
from src.agents.llm import ClienteLLM, ClienteOpenAICompativel, ErroLLM
from src.eval.golden_dataset import CasoGolden, carregar_golden_dataset


@dataclass
class ResultadoCaso:
    id: str
    critico: bool
    rotas_aceitas: list[str]
    agentes_esperados: list[str]
    rota_obtida: str | None
    agentes_obtidos: list[str]
    entrada_suficiente: bool | None
    fallback: bool
    latencia_ms: int
    erro: str | None = None

    @property
    def rota_ok(self) -> bool:
        return self.rota_obtida in self.rotas_aceitas

    @property
    def agentes_ok(self) -> bool:
        return self.erro is None and set(self.agentes_obtidos) == set(
            self.agentes_esperados
        )

    @property
    def acerto(self) -> bool:
        return self.rota_ok and self.agentes_ok


def avaliar_caso(caso: CasoGolden, cliente: ClienteLLM) -> ResultadoCaso:
    base = {
        "id": caso.id,
        "critico": caso.critico,
        "rotas_aceitas": list(caso.gabarito.rotas_aceitas),
        "agentes_esperados": list(caso.gabarito.agentes_esperados),
    }
    inicio = time.perf_counter()
    try:
        contrato = estruturar_e_rotear(caso.entrada, cliente)
    except ErroLLM as erro:
        return ResultadoCaso(
            **base,
            rota_obtida=None,
            agentes_obtidos=[],
            entrada_suficiente=None,
            fallback=False,
            latencia_ms=round((time.perf_counter() - inicio) * 1000),
            erro=str(erro),
        )
    roteamento = contrato.roteamento
    return ResultadoCaso(
        **base,
        rota_obtida=roteamento.rota_definida,
        agentes_obtidos=list(roteamento.agentes_alvo),
        entrada_suficiente=roteamento.entrada_suficiente,
        fallback=contrato.execucao.fallback_seguranca,
        latencia_ms=contrato.execucao.latencia_ms,
    )


def resumir(resultados: list[ResultadoCaso]) -> dict:
    def taxa(itens: list[ResultadoCaso]) -> float | None:
        return round(sum(r.acerto for r in itens) / len(itens), 4) if itens else None

    return {
        "casos": len(resultados),
        "acerto_rota_e_agentes": taxa(resultados),
        "acerto_casos_criticos": taxa([r for r in resultados if r.critico]),
        "acerto_rota": round(
            sum(r.rota_ok for r in resultados) / max(len(resultados), 1), 4
        ),
        "fallbacks": sum(r.fallback for r in resultados),
        "erros_llm": sum(r.erro is not None for r in resultados),
        "latencia_media_ms": round(
            sum(r.latencia_ms for r in resultados) / max(len(resultados), 1)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--casos", help="IDs separados por vírgula (ex.: GD-01,GD-19)")
    parser.add_argument(
        "--pausa", type=float, default=0.0, help="Segundos entre chamadas ao LLM."
    )
    parser.add_argument("--saida", type=Path, help="Salva o relatório em JSON.")
    args = parser.parse_args(argv)

    dataset = carregar_golden_dataset()
    casos = dataset.casos
    if args.casos:
        ids = {i.strip() for i in args.casos.split(",")}
        casos = [c for c in casos if c.id in ids]

    cliente = ClienteOpenAICompativel.do_ambiente()
    print(f"Modelo: {cliente.modelo} | golden {dataset.versao_dataset}\n")

    resultados = []
    for indice, caso in enumerate(casos):
        if indice and args.pausa:
            time.sleep(args.pausa)
        resultado = avaliar_caso(caso, cliente)
        resultados.append(resultado)
        marca = "OK  " if resultado.acerto else "ERRO"
        obtido = resultado.erro or (
            f"{resultado.rota_obtida} {resultado.agentes_obtidos}"
            + (" [fallback]" if resultado.fallback else "")
        )
        print(
            f"{marca} {caso.id}{'*' if caso.critico else ' '} "
            f"esperado={resultado.rotas_aceitas} {resultado.agentes_esperados} | "
            f"obtido={obtido} | {resultado.latencia_ms} ms"
        )

    resumo = resumir(resultados)
    print("\n* caso crítico\n" + json.dumps(resumo, ensure_ascii=False, indent=2))
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        relatorio = {
            "modelo_llm": cliente.modelo,
            "versao_dataset": dataset.versao_dataset,
            "resumo": resumo,
            "resultados": [asdict(r) for r in resultados],
        }
        args.saida.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0 if resumo["acerto_rota_e_agentes"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
