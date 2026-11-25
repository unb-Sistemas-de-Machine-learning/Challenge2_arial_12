import json

from src.agents.llm import ErroLLM
from src.eval.golden_dataset import carregar_golden_dataset
from src.eval.roteamento import avaliar_caso, resumir


class LLMDoGabarito:
    """Responde a rota esperada pelo gabarito de cada caso."""

    modelo = "llm-gabarito"

    def __init__(self, caso):
        self.caso = caso

    def gerar_json(self, mensagens, schema, nome_schema):
        gabarito = self.caso.gabarito
        rota = gabarito.rotas_aceitas[0]
        fora = rota in ("fora_de_escopo", "evidencia_insuficiente")
        return json.dumps(
            {
                "rota_definida": "fora_de_escopo" if fora else rota,
                "agentes_alvo": list(gabarito.agentes_esperados),
                "entidades_normalizadas": {},
                "filtros_rag_recomendados": {},
                "dentro_do_escopo_mvp": not fora,
                "entrada_suficiente": True,
            }
        )


class LLMForaDoAr:
    modelo = "fora"

    def gerar_json(self, mensagens, schema, nome_schema):
        raise ErroLLM("HTTP 503")


def test_llm_que_segue_o_gabarito_acerta_todos_os_casos() -> None:
    casos = carregar_golden_dataset().casos
    resultados = [avaliar_caso(caso, LLMDoGabarito(caso)) for caso in casos]
    resumo = resumir(resultados)
    assert resumo["acerto_rota_e_agentes"] == 1
    assert resumo["acerto_casos_criticos"] == 1
    assert resumo["fallbacks"] == 0


def test_erro_do_llm_conta_como_erro() -> None:
    caso = carregar_golden_dataset().casos[0]
    resultado = avaliar_caso(caso, LLMForaDoAr())
    assert not resultado.acerto
    assert resultado.erro == "HTTP 503"
    assert resumir([resultado])["erros_llm"] == 1
