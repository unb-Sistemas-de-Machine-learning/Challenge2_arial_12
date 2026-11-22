# EvidencIA Saúde

O EvidencIA Saúde é um assistente de apoio à decisão em saúde baseado em
evidências oficiais. Consulte a [documentação do projeto](docs/README.md) para
conhecer o escopo e a arquitetura.

## Estrutura do repositório

| Diretório | Finalidade |
| --- | --- |
| `data/` | Dados usados pela ingestão e artefatos locais do RAG |
| `src/rag/` | Ingestão, indexação e recuperação de documentos |
| `src/agents/` | Agentes especialistas e orquestração |
| `src/api/` | API REST |
| `src/ui/` | Interface com o usuário |
| `tests/` | Testes automatizados |

## Configuração local

Instale o [uv](https://docs.astral.sh/uv/getting-started/installation/) e execute
na raiz do repositório. O uv usa o Python 3.12 indicado em `.python-version`
e instala as dependências de desenvolvimento a partir do `uv.lock`.

```sh
uv python install
uv sync --locked
```

Crie o arquivo `.env` na raiz do repositório e coloque nele o conteúdo de
`.env.example`.

## Verificações locais

O GitHub Actions roda as mesmas verificações em cada pull request.

```sh
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
```

Ao alterar dependências, inclua no mesmo pull request as mudanças em
`pyproject.toml` e no `uv.lock`.

## Contribuidores

<center>
  
  <table style="width: 100%;">
  <tr>
    <td align="center"><a href="https://github.com/andre-maia51"><img style="border-radius: 50%;" src="https://github.com/andre-maia51.png" width="100px;" alt="Imagem de André Maia"/><br /><sub><b>André Maia</b></sub></a></td>
    <td align="center"><a href="https://github.com/Brenofrds"><img style="border-radius: 50%;" src="https://github.com/Brenofrds.png" width="100px;" alt="Imagem de Bruno Ricardo de Menezes"/><br /><sub><b>Breno Soares Fernandes</b></sub></a></td>
    <td align="center"><a href="https://github.com/EhOBruno"><img style="border-radius: 50%;" src="https://github.com/EhOBruno.png" width="100px;" alt="Imagem de Bruno Ricardo de Menezes"/><br /><sub><b>Bruno Ricardo de Menezes</b></sub></a></td>
    <td align="center"><a href="https://github.com/CADU110"><img style="border-radius: 50%;" src="https://github.com/CADU110.png" width="100px;" alt="Imagem de Carlos Eduardo Mota"/><br /><sub><b>Carlos Eduardo Mota</b></sub></a></td>
    <td align="center"><a href="https://github.com/PhFariaa"><img style="border-radius: 50%;" src="https://github.com/PhFariaa.png" width="100px;" alt="Imagem de Pedro Henrique Faria"/><br /><sub><b>Pedro Henrique Faria</b></sub></a></td>
  </tr>
  </table> 

</center>
