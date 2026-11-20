# As 5 Perguntas Fundamentais de MLOps

Antes de escrever pipelines ou escolher bibliotecas, a engenharia de sistemas de Machine Learning (MLOps) exige responder de forma explícita a **cinco perguntas fundamentais** que conectam valor de negócio, organização do time, fronteiras arquiteturais, reprodutibilidade e governança em produção.

Este documento consolida as respostas do projeto **EvidencIA Saúde** e serve como índice executivo para os artefatos detalhados de concepção, papéis, decisões arquiteturais (ADR), contratos e gestão de riscos.

---

## Visão Consolidada das 5 Perguntas Fundamentais

| # | Pergunta Fundamental de MLOps | Resposta Síntese no EvidencIA Saúde | Documento Detalhado |
| :-: | :--- | :--- | :--- |
| **1** | **Qual é o problema de negócio, o valor esperado e como validá-lo objetivamente?** | Apoiar cidadãos na triagem vacinal, manejo inicial de sintomas e prevenção de automedicação contraindicada usando exclusivamente fontes oficiais (Anvisa/MS), validado via benchmark LLM puro × RAG + Multiagentes (meta de **100% em contraindicações críticas**) e taxa de feedback *"Útil"*. | [Challenge 2 e Essential Question](/concepcao/challenge-e-essential-question.md) e [Lean Inception](/concepcao/lean-inception.md) |
| **2** | **Quem é responsável por cada etapa do ciclo de vida (Papéis R1 a R7)?** | Os 7 papéis interdisciplinares da arquitetura de MLOps (Kreuzberger et al., 2023) são distribuídos integralmente entre os 5 integrantes do grupo com titularidade clara, co-responsabilidade e Matriz RACI, consolidando `R1+R2` e `R6+R7` sem sobrepor dados (`R4`), modelagem (`R3`) e software (`R5`). | [Papéis e Responsabilidades (R1 a R7)](/arquitetura/papeis-e-responsabilidades.md) |
| **3** | **Quais componentes MLOps (C1 a C9) adotar sob custo zero e onde a automação começa e para?** | Adoção de GitHub Actions, Base Vetorial local, MLflow (Tracking + Registry), API REST em Docker, Streamlit e Prometheus/Grafana sob **R$ 0,00**. Omissão justificada de Feature Store tradicional, Kubernetes e reindexação autônoma — a automação cobre CI, validação, serving e alertas, **parando antes de alterar o conhecimento clínico sem revisão humana (*human-in-the-loop*)**. | [ADR-001: Arquitetura MLOps sob Custo Zero](/arquitetura/adr-001-arquitetura-mlops-mvp.md) |
| **4** | **Como versionar dados/experimentos, comparar versões e entregar o serviço de forma desacoplada?** | Corpus Anvisa/MS estruturado com 5 metadados obrigatórios (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`), troca de dados via **Contrato JSON padronizado**, comparação objetiva de prompts/modelos/índices no **MLflow Tracking**, promoção controlada no **MLflow Model Registry** e exposição desacoplada via **API REST em Docker** consumida pelo **Streamlit**. | [Contrato JSON e Metadados do RAG](/arquitetura/contrato-json-e-metadados-rag.md) e [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md) |
| **5** | **Como evitar regressões, monitorar degradação em produção e garantir segurança ética e LGPD?** | Portões de qualidade no CI + benchmark no MLflow bloqueiam regressões antes do deploy; **Prometheus + Grafana** monitoram latência, erros HTTP, tempo do RAG, alertas graves e feedback *"Útil"/"Inútil"*; riscos clínicos e vieses são mitigados via citação obrigatória, política *fail-safe* e arquitetura *stateless* sem coleta de PII conforme a **LGPD**. | [Riscos Clínicos, Viés, Ética e LGPD](/governanca/riscos-vies-etica-lgpd.md) |

---

## Detalhamento das Respostas no Contexto do EvidencIA Saúde

### Pergunta 1 — Alinhamento de Problema, Valor de Negócio e Métricas Objetivas

* **Problema real:** Cidadãos enfrentam barreiras para cruzar cartões vacinais antigos com o calendário do Ministério da Saúde (caso da persona **Mariana**, gestante de 20 semanas) e correm risco grave de automedicação diante de doenças agudas como dengue ou malária (caso da persona **Pedro**, prestes a ingerir Ibuprofeno).
* **Por que IA com RAG + Multiagentes (e não busca comum ou LLM puro)?** Buscas comuns retornam informações contraditórias; bulas oficiais têm linguagem técnica densa; e LLMs genéricos alucinam contraindicações ou misturam diretrizes estrangeiras (FDA/CDC) com protocolos brasileiros. O RAG ancorado exclusivamente em documentos da Anvisa e do Ministério da Saúde, aliado a agentes especialistas (Estruturador, Orquestrador, Imunização e Medicamentos/Condutas), resolve a interpretação sem abdicar da rastreabilidade documental.
* **Critérios objetivos de sucesso:**
  1. **Segurança clínica (MLflow):** **100% de acerto** no conjunto de avaliação de contraindicações críticas (ex.: Ibuprofeno na dengue; vacinas de vírus vivo atenuado como febre amarela na gestação) e comprovação quantitativa da superioridade sobre um LLM puro.
  2. **Fidelidade documental (*groundedness*):** **0% de recomendações sem citação literal** da fonte oficial recuperada pelo motor RAG.
  3. **Valor percebido:** Taxa de avaliações *"Útil"* registradas na etapa 6 das jornadas da Mariana e do Pedro.
  4. **Estabilidade operacional:** Latência controlada na API REST em Docker e 100% das versões auditáveis no *Model Registry*.

---

### Pergunta 2 — Organização Interdisciplinar e Mapeamento de Papéis (R1 a R7)

Um sistema de MLOps falha quando a responsabilidade entre concepção, dados, modelagem, software e operação permanece difusa. Com base na taxonomia de **Kreuzberger, Kühl e Hirschl (2023)**, o EvidencIA Saúde mapeia todos os **7 papéis (`R1` a `R7`)** entre os **5 integrantes**:

* **André Maia** (*Arquiteto de Soluções e Dados*) assume **`R1` (Business Stakeholder / PO)** e **`R2` (Solution Architect)**, atuando como guardião da visão do MVP, da arquitetura, dos contratos JSON e da conformidade ética/LGPD.
* **Pedro Henrique Faria** (*Cientista de Dados*) assume **`R3` (Data Scientist)**, liderando o motor RAG, a engenharia de prompts dos agentes, a definição de métricas e o benchmark LLM puro × RAG no MLflow.
* **Carlos Eduardo Mota** (*Engenheiro de Dados*) assume **`R4` (Data Engineer)**, responsável pela curadoria, limpeza, chunking, anotação dos 5 metadados obrigatórios e ingestão *batch* da base vetorial oficial (Anvisa/MS).
* **Breno Soares Fernandes** (*Engenheiro de Software / Fullstack*) assume **`R5` (Software Engineer)**, construindo a API REST tipada (FastAPI/Flask), o painel web em Streamlit, a integração ponta a ponta e os testes automatizados de software e contrato.
* **Bruno Ricardo de Menezes** (*Engenheiro de MLOps / LLMOps*) assume **`R6` (DevOps Engineer)** e **`R7` (ML / MLOps Engineer)**, operando CI/CD no GitHub Actions, containerização Docker, MLflow Tracking/Registry e observabilidade em Prometheus/Grafana.

A Matriz completa e a divisão RACI por entrega estão documentadas em [Papéis e Responsabilidades (R1 a R7)](/arquitetura/papeis-e-responsabilidades.md).

---

### Pergunta 3 — Arquitetura sob Custo Zero e Fronteiras da Automação

A arquitetura do MVP avalia cada um dos **9 componentes técnicos de MLOps (`C1` a `C9`)** sob quatro restrições concretas: orçamento de **R$ 0,00**, prazo de **6 semanas (entrega em 07/12)**, equipe de **5 pessoas** e **domínio crítico de saúde**.

* **Onde a automação acontece:**
  * **Integração contínua (`C1`/`C2`):** GitHub Actions valida estilo de código, testes unitários, conformidade com o contrato JSON e integridade dos metadados a cada Pull Request.
  * **Rastreamento e registro (`C6`/`C7`):** MLflow registra automaticamente parâmetros de chunking, `top_k`, prompts, latência e acurácia em casos críticos, versionando artefatos promovíveis no *Model Registry*.
  * **Empacotamento e inferência (`C8`):** Docker + Docker Compose sobem de forma reproduzível a API REST, a Base Vetorial local, o MLflow, o Streamlit, o Prometheus e o Grafana.
  * **Coleta de telemetria (`C9`):** Prometheus raspa continuamente métricas da API e alimenta dashboards e alertas no Grafana.
* **Onde a automação deliberadamente para (*Human-in-the-Loop*):**
  * **Ingestão documental e reindexação:** Não há *web scraping* em tempo real nem reindexação autônoma. Alterar documentos clínicos sem revisão humana criaria risco de corromper trechos de contraindicação. A atualização é *batch*, curada pelo `R4` e validada pelo `R3`.
  * **Promoção para produção:** Nenhuma nova versão de prompt, modelo ou índice vetorial passa de *Staging* para *Production* no MLflow Registry sem validação no conjunto de testes críticos (100% de acerto em contraindicações) e aprovação explícita em Pull Request.

As justificativas técnicas de cada adoção e omissão (incluindo Feature Store tradicional, Kubernetes e reindexação autônoma) estão registradas no [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md).

---

### Pergunta 4 — Dados, Contratos, Comparação de Versões e Entrega Desacoplada

Para evitar o clássico débito técnico de protótipos acoplados em *notebooks*, o EvidencIA Saúde estabelece três pilares de engenharia:

1. **Rastreabilidade documental desde a ingestão (`#11`):** Todo trecho (*chunk*) da base vetorial carrega obrigatoriamente cinco metadados (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`), permitindo filtragem precisa (por exemplo, filtrar `secao="contraindicacoes"` e `publico_alvo="gestante"`) e citação verificável.
2. **Comparação rigorosa de versões e prevenção de regressões (`#12`):** Diferentes configurações — *LLM puro* (baseline), estratégias de *chunking*, valores de `top_k`, versões de *prompts* dos agentes e modelos de *embedding* — são executadas contra o mesmo conjunto de cenários de validação e comparadas lado a lado no **MLflow Tracking**. Somente a configuração que atinge os critérios mínimos é promovida no **MLflow Model Registry**.
3. **Desacoplamento por Contrato JSON e API REST em Docker (`#24`):** O frontend **Streamlit** nunca importa diretamente módulos internos do RAG ou dos agentes; toda comunicação ocorre via endpoints REST tipados (`POST /api/v1/consultar` e `POST /api/v1/feedback`) governados pelo [Contrato JSON](/arquitetura/contrato-json-e-metadados-rag.md). Isso permite evoluir agentes, prompts ou interface de forma independente.

---

### Pergunta 5 — Monitoramento Contínuo, Qualidade Clínica, Ética e LGPD

Em saúde, monitoramento não significa apenas observar CPU e memória, mas garantir que a confiabilidade informacional não degrade e que a privacidade do cidadão seja inviolável:

* **Observabilidade técnica e de produto (Prometheus + Grafana):** Rastreamento de latência (p50/p95) da API e da etapa de recuperação RAG, taxa de erros HTTP (`4xx`/`5xx`), taxa de acionamento de *fallback* (`EVIDENCIA_INSUFICIENTE`), volume por rota de agente, frequência de *Alertas de Risco Grave* e razão de feedback *"Útil"* vs. *"Inútil"*.
* **Ciclo de feedback seguro:** Quedas na taxa de respostas úteis ou picos de `EVIDENCIA_INSUFICIENTE` disparam alertas operacionais para que a equipe (`R3`, `R4` e `R7`) investigue lacunas na base documental ou falhas de recuperação e execute um novo ciclo controlado de experimentação e reindexação.
* **Mitigação de riscos, vieses e conformidade LGPD:** Por tratar de dados sensíveis de saúde (Art. 5º, II da Lei nº 13.709/2018), o MVP adota *Privacy by Design*: arquitetura *stateless* (sem cadastro, sem login, sem persistência de identidade ou prontuário), proibição de armazenar dados pessoais identificáveis (PII) em logs/MLflow/Prometheus, *disclaimer* médico fixo e política *fail-safe* documentados em [Riscos Clínicos, Viés, Ética e LGPD](/governanca/riscos-vies-etica-lgpd.md).
