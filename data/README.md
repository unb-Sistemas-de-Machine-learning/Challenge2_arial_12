# Dados do EvidencIA Saúde

Use somente fontes oficiais da Anvisa e do Ministério da Saúde no corpus do
projeto.

| Caminho | Conteúdo | Versionado no Git |
| --- | --- | :-: |
| `catalogo_fontes.toml` | Catálogo das fontes: metadados, URL, vigência e sha256 de cada documento | Sim |
| `raw/` | PDFs oficiais do corpus, exatamente como foram baixados | Sim |
| `manifests/` | Cópia do manifesto de cada versão do índice vetorial | Sim |
| `processed/` | Resultados intermediários da ingestão (chunks em JSONL e relatórios) | Não |
| `vectorstore/` | Base vetorial local (ChromaDB) e o manifesto da versão atual | Não |

Os PDFs ficam versionados porque o Bulário Eletrônico da Anvisa não permite
download automatizado confiável. Sem os arquivos originais, o índice vetorial
não pode ser reproduzido. O pipeline confere o sha256 de cada PDF com o valor
registrado no catálogo antes de processá-lo.
