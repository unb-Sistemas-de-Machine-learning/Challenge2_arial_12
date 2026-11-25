# Data Card do Corpus Oficial (`corpus-v1.0.0`)

Este *data card* descreve o corpus documental usado pelo motor RAG do **EvidencIA Saúde**: o que contém, de onde veio, como a vigência foi conferida, como é processado e quais são suas limitações. Ele atende à issue **`#11`** e segue a estrutura de *Data Cards* (Pushkarna et al., 2022) e *Datasheets for Datasets* (Gebru et al., 2021), adaptada a um corpus pequeno e curado.

| Item | Valor |
| :--- | :--- |
| Versão | `corpus-v1.0.0` |
| Data de coleta e de verificação de vigência | 25/11/2026 |
| Documentos | 11 PDFs oficiais (6 do Ministério da Saúde, 5 da Anvisa) |
| Local no repositório | PDFs em `data/raw/`; catálogo com metadados, vigência e sha256 em `data/catalogo_fontes.toml` |
| Esquema de metadados | [Contrato JSON e Metadados do RAG, Seção 2](/arquitetura/contrato-json-e-metadados-rag.md?id=metadados-rag) |
| Responsáveis | Curadoria e pipeline: `R4` (Engenharia de Dados) e `R3` (Ciência de Dados). Ver [Papéis e Responsabilidades](/arquitetura/papeis-e-responsabilidades.md). |

---

## 1. Finalidade

O corpus é a **única fonte de evidência** dos agentes especialistas do EvidencIA Saúde:

* **Agente de Triagem Vacinal** (issue `#15`, Jornada da Mariana): vacinas do adulto e da gestante, com foco em dTpa, febre amarela e dengue.
* **Agente de Medicamentos e Condutas** (issue `#16`, Jornada do Pedro): contraindicações de ibuprofeno, ácido acetilsalicílico, dipirona e paracetamol, manejo clínico e sinais de alarme de dengue e malária.

Toda resposta clínica precisa citar um trecho literal deste corpus (regra *Zero Evidence, Zero Recommendation* do contrato).

**Usos fora do escopo:** pediatria (as seções infantis do calendário não são indexadas), doenças fora do recorte do MVP, prescrição e posologia individualizada, e qualquer uso comercial (ver Seção 7).

---

## 2. Composição

| `doc_id` | Documento | Órgão | `categoria` | Jornada | Edição / data | Páginas indexadas |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| `DOC-MS-CALENDARIO-2026` | Instrução Normativa do Calendário Nacional de Vacinação 2026 | MS | `calendario_vacinal` | Mariana | Atualizada em 08/10/2026 | 2–8, 25–35, 37–39, 50–60 |
| `DOC-MS-NT-DTPA` | Nota Técnica nº 119/2025-CGICI/DPNI/SVSA/MS (vacinação de gestantes: VSR, dTpa e covid-19) | MS | `nota_tecnica` | Mariana | 22/10/2025 | todas (5) |
| `DOC-MS-NT-FEBRE-AMARELA` | Nota Técnica Conjunta nº 27/2025-DEDT/DPNI/SVSA (febre amarela: alerta aos viajantes) | MS | `nota_tecnica` | Mariana | 02/02/2025 | todas (6) |
| `DOC-MS-NT-VACINA-DENGUE` | Nota Técnica Conjunta nº 11/2024-CGICI/DPNI/SVSA/MS (vacina dengue e amamentação) | MS | `nota_tecnica` | Mariana | 28/02/2024 | todas (5) |
| `DOC-ANVISA-BULA-VACINA-DENGUE` | Bula do paciente — Qdenga (vacina dengue 1, 2, 3 e 4 atenuada), Takeda | Anvisa | `bula_vacina` | Mariana | Aprovada em 25/08/2026 | 1–6 |
| `DOC-ANVISA-BULA-IBUPROFENO` | Bula do paciente — Ibuprofeno 600 mg, Laboratório Globo (genérico) | Anvisa | `bula_medicamento` | Pedro | Última alteração em 25/11/2024 | 1–10 |
| `DOC-ANVISA-BULA-AAS` | Bula do paciente — Ácido acetilsalicílico 100 mg, Eurofarma (genérico) | Anvisa | `bula_medicamento` | Pedro | Bula Padrão de 24/08/2026 | 1–9 |
| `DOC-ANVISA-BULA-DIPIRONA` | Bula do paciente — Dipirona monoidratada 50 mg/mL, Sanofi Medley | Anvisa | `bula_medicamento` | Pedro | Bula Padrão de 16/01/2026 | 1–9 |
| `DOC-ANVISA-BULA-PARACETAMOL` | Bula do paciente — Tylenol (paracetamol) 500 mg e 750 mg, Johnson & Johnson (referência) | Anvisa | `bula_medicamento` | Pedro | Última alteração em 11/04/2024 | 1–6 |
| `DOC-MS-PROTOCOLO-DENGUE` | Dengue: diagnóstico e manejo clínico — adulto e criança (6ª edição) | MS | `protocolo_clinico` | Pedro | 2024 | 12–64, 78 |
| `DOC-MS-GUIA-MALARIA` | Guia de tratamento da malária no Brasil (3ª edição) | MS | `protocolo_clinico` | Pedro | 2026 | 21–74 |

O catálogo registra, para cada documento, a URL oficial, o sha256 do PDF, o público-alvo padrão, a entidade principal e, nas bulas, o detentor e o número de registro na Anvisa.

**Por que estas páginas.** Ficam de fora capas, fichas técnicas, sumários, apresentações, referências bibliográficas, equipes técnicas, as seções infantis do calendário, as cópias repetidas da bula da Qdenga (o PDF traz uma cópia por apresentação) e as tabelas de histórico de alteração das bulas. Nos dois guias do MS, a página impressa *N* corresponde à página *N+1* do PDF.

**Relação com o golden dataset.** Os `doc_id` são os mesmos do catálogo `documentos_referencia` de `tests/eval/golden_dataset.json`. O teste `tests/rag/test_rag_corpus.py` garante que todo documento citado pelo gabarito existe no catálogo, com o mesmo título, órgão e categoria.

---

## 3. Coleta e verificação de vigência

* **Origem:** portal `gov.br/saude` (Ministério da Saúde) e Bulário Eletrônico da Anvisa (`consultas.anvisa.gov.br/#/bulario/`). Nenhum documento veio de terceiros, agregadores ou sites de fabricantes.
* **Coleta manual:** os dois portais bloqueiam download automatizado (o `gov.br` responde `403` a scripts e o Bulário exige verificação do Cloudflare). Os PDFs foram baixados manualmente em 25/11/2026 e versionados em `data/raw/`, exatamente como publicados.
* **Critério de vigência:**
  * **Protocolos e calendário:** edição mais recente publicada no portal do MS na data da coleta.
  * **Notas técnicas:** nota mais recente sobre o tema, sem nota posterior conhecida que a revogue.
  * **Bulas:** versão com a data de publicação mais recente no Bulário. A data registrada no catálogo vem do próprio texto da bula ("Bula Padrão aprovada pela Anvisa em…") ou, na falta dela, da última linha do histórico de alterações.
* **Integridade:** o pipeline confere o sha256 de cada PDF com o catálogo antes de processar e falha se algum arquivo tiver sido trocado ou corrompido.

---

## 4. Pré-processamento e indexação

O comando único `uv run python -m src.rag.ingestao` (issue `#11`) executa, nesta ordem:

1. **Integridade:** confere o sha256 de cada PDF.
2. **Extração:** lê apenas as páginas listadas no catálogo, com PyMuPDF.
3. **Limpeza:** remove cabeçalhos e rodapés repetidos, números de página, carimbos do SEI, blocos de assinatura eletrônica das notas técnicas e hifenização de fim de linha.
4. **Seções:** atribui a `secao` de cada trecho.
   * **Bulas:** as 9 perguntas padronizadas da RDC nº 47/2009 dão o mapeamento (ex.: "3. Quando não devo usar este medicamento?" → `contraindicacoes`). As perguntas sem equivalente no vocabulário, como posologia e armazenamento, são descartadas, porque o sistema não prescreve.
   * **Calendário:** os subtítulos de cada vacina dão a seção (Indicação, Esquema de vacinação, Precauções, Contraindicações).
   * **Protocolos e notas técnicas:** regras por documento, definidas no catálogo.
5. **Chunking semântico:** nenhum chunk atravessa a fronteira de uma seção e itens de lista não são cortados. O embedding é calculado sobre o trecho precedido do título do documento e da seção; o texto guardado é o trecho literal.
6. **Quality gate:** aplica a Seção 2.4 do contrato a todos os chunks (5 metadados obrigatórios, vocabulário controlado, pelo menos 30 caracteres úteis, `chunk_id` único). Basta um chunk inválido para a carga falhar sem gravar nada.
7. **Indexação:** grava os chunks no ChromaDB local em `data/vectorstore/` (coleção `evidencia_corpus`, distância cosseno).
8. **Manifesto:** grava `data/vectorstore/manifest.json`, com uma cópia versionada em `data/manifests/`. O manifesto traz hashes do corpus, dos chunks e do índice, parâmetros de chunking, modelo de embedding e contagens por documento e seção.

---

## 5. Limitações e vieses conhecidos

* **Dose máxima diária fora do índice.** Nas bulas, a posologia (pergunta 6 da RDC nº 47/2009) não é indexada, porque o sistema não prescreve. O limite de 4.000 mg/dia de paracetamol chega aos agentes pelo protocolo de dengue do MS; a bula contribui com a advertência de não exceder a dose recomendada nem associar outro produto com paracetamol.
* **Bula do paracetamol de 2024.** No Bulário, a busca por paracetamol retorna sobretudo associações (codeína, pseudoefedrina, carisoprodol). Foi usada a bula do medicamento de referência (Tylenol), cuja última alteração de texto é de abril de 2024.
* **Bulas de um único fabricante.** Cada medicamento está representado pela bula de um produto e de uma apresentação. Contraindicações e advertências costumam coincidir entre produtos com o mesmo princípio ativo, mas posologia e excipientes variam.
* **Notas técnicas com outro foco principal.** A NT 119/2025 trata do painel de vacinação de gestantes e traz a recomendação de dTpa como um dos itens. A NT 27/2025 é um alerta a viajantes que lista as contraindicações da vacina de febre amarela. A NT 11/2024 trata apenas de lactantes e não menciona gestantes.
* **Linguagem técnica.** Protocolos e notas técnicas são escritos para profissionais de saúde. A tradução para linguagem acessível fica a cargo dos agentes, sempre ancorada no trecho literal.
* **Tabelas.** Tabelas (calendário, esquemas de tratamento da malária) são extraídas como texto linear e podem perder a relação entre linhas e colunas. Os chunks dessas seções passam por revisão manual.
* **Corpus fechado e datado.** O corpus não acompanha novas notas ou bulas automaticamente (decisão do [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md), Seção 4.3). Cada resposta mostra o documento e a edição citados.
* **Recorte populacional.** Adultos, gestantes e lactantes. Crianças e adolescentes ficam fora do escopo do MVP.

---

## 6. Privacidade e LGPD

O corpus é formado apenas por documentos públicos e não contém dados de pacientes ou de usuários. As notas técnicas trazem nomes e cargos dos servidores que as assinaram eletronicamente, que são dados públicos de agentes no exercício da função. Mesmo assim, o pipeline remove os blocos de assinatura, porque eles não têm valor clínico.

---

## 7. Licença e atribuição

* **Ministério da Saúde:** os guias de dengue e malária são distribuídos sob a licença Creative Commons Atribuição–NãoComercial–CompartilhaIgual 4.0. As notas técnicas e o calendário são documentos públicos oficiais. Uso acadêmico, sem fins comerciais e com citação da fonte.
* **Anvisa:** as bulas são documentos públicos do Bulário Eletrônico. O texto pertence aos detentores dos registros, citados no catálogo. Uso acadêmico e informativo, com citação da fonte.

---

## 8. Manutenção e pendências

**Atualização (sempre com revisão humana):**

1. Baixar a nova edição ou bula do portal oficial.
2. Atualizar o PDF em `data/raw/` e a entrada no catálogo (sha256, datas, páginas).
3. Incrementar `versao_corpus` e rodar o pipeline.
4. Comparar o novo manifesto com o anterior.
5. Reexecutar o benchmark do golden dataset (issue `#18`), exigindo 100% nos casos críticos.
6. Promover a versão no MLflow.

**Pendências de `corpus-v1.0.0`:** nenhuma.

**Resolvidas:**

* Bula do paracetamol: a bula em pó de 2014 (EMS) foi trocada pela bula do Tylenol 500 mg e 750 mg em comprimidos (medicamento de referência). Uma bula de paracetamol + fosfato de codeína foi recusada, porque as contraindicações do opioide se misturariam às do paracetamol. No caso `GD-09`, a afirmação-chave atribuída à bula passou a ser a advertência sobre a dose recomendada; o limite de 4 g/dia continua exigido pela fonte do protocolo de dengue.

* Caso `GD-03` do golden dataset (`golden-v2.0.0`): a fonte esperada NT 11/2024, que trata só de lactantes, foi trocada pela seção de contraindicações da vacina dengue no Calendário 2026, que lista mulheres grávidas e lactantes.
