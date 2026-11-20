# ADR-001: Arquitetura MLOps e Stack do MVP sob Custo Zero

* **Status:** Aceito
* **Data:** Outubro/Novembro de 2026 *(Semana 1 — Concepção e Arquitetura)*
* **Decisores:** André Maia (`R1`/`R2`), Bruno Ricardo de Menezes (`R6`/`R7`), Carlos Eduardo Mota (`R4`), Pedro Henrique Faria (`R3`), Breno Soares Fernandes (`R5`)
* **Contexto do Projeto:** EvidencIA Saúde — Challenge 2 (UnB) | Entrega Final: 07/12 | Orçamento: **R$ 0,00**

---

## 1. Contexto e Restrições Arquiteturais

O **EvidencIA Saúde** é um sistema multiagentes com **RAG (*Retrieval-Augmented Generation*)** destinado a apoiar cidadãos na tomada de decisão sobre vacinação pendente, manejo inicial de sintomas e contraindicações de medicamentos, utilizando exclusivamente evidências oficiais da **Anvisa** e do **Ministério da Saúde**.

A definição da arquitetura de MLOps do MVP precisa equilibrar maturidade de engenharia com quatro restrições inegociáveis:

1. **Orçamento zero (R$ 0,00):** toda a stack deve ser 100% *open source* e/ou operável gratuitamente em ambiente local/Docker e GitHub Free, sem dependência de clusters gerenciados pagos em nuvem.
2. **Prazo curto (6 semanas — entrega em 07/12):** com dois feriados no período (02/11 e 20/11) e equipe de 5 pessoas, a arquitetura deve evitar *over-engineering* de infraestrutura que atrasaria a validação científica do RAG e dos agentes.
3. **Domínio crítico de saúde:** erros silenciosos, alucinações ou atualizações automatizadas não auditadas na base clínica podem induzir decisões perigosas ao cidadão.
4. **Conformidade com a LGPD (dados sensíveis de saúde):** o MVP deve operar de forma *stateless*, sem cadastro de usuários e sem persistência de dados pessoais identificáveis (PII).

---

## 2. Avaliação dos 9 Componentes de MLOps (Kreuzberger et al., 2023)

Tomando como referência os **9 componentes técnicos de MLOps (`C1` a `C9`)** da literatura de Kreuzberger, Kühl e Hirschl (2023), a tabela abaixo registra explicitamente quais componentes são **adotados**, **simplificados** ou **omitidos/substituídos** no MVP:

| ID | Componente MLOps (Kreuzberger et al.) | Decisão no MVP | Tecnologia Adotada no EvidencIA Saúde | Resumo da Justificativa |
| :-: | :--- | :---: | :--- | :--- |
| **C1** | **CI/CD Component** | **Adotado** | **GitHub Actions** | Automação gratuita de lint, testes unitários, validação de contratos JSON, testes de integridade do RAG e build Docker a cada PR. |
| **C2** | **Source Code Repository** | **Adotado** | **Git + GitHub** | Versionamento unificado de código, prompts, schemas JSON, Dockerfiles, scripts de ingestão e documentação Docsify com revisão por pares. |
| **C3** | **Workflow Orchestration Component** | **Simplificado** | **Scripts Python modulares (*batch* sob demanda) + CLI / GitHub Actions** | Escopo documental fechado no MVP (calendário adulto/gestante + dengue, malária e gripe) dispensa orquestradores pesados (Apache Airflow/Kubeflow) e **omite reindexação autônoma** por segurança clínica. |
| **C4** | **Feature Store System** | **Omitido / Substituído funcionalmente** | **Base Vetorial Local** *(ex.: ChromaDB / Qdrant local ou FAISS com metadados)* — **sem Feature Store tradicional** | O sistema não consome *features* tabulares históricas em janelas temporais; o ativo central de recuperação são *embeddings* de trechos regulatórios da Anvisa/MS com filtros de metadados obrigatórios. |
| **C5** | **Model Training Infrastructure** | **Simplificado** | **Execução local / APIs gratuitas ou modelos open-source leves — sem Kubernetes e sem cluster GPU** | O paradigma é LLMOps/RAG (engenharia de prompts, embeddings e orquestração multiagentes), sem pré-treinamento ou *fine-tuning* distribuído de pesos que justificasse cluster GPU/K8s. |
| **C6** | **Model Registry** | **Adotado** | **MLflow Model Registry** | Versionamento centralizado e promoção controlada (*Staging* → *Production* → *Archived*) de pipelines RAG, versões de prompts, configurações dos agentes e snapshots de índice vetorial. |
| **C7** | **ML Metadata Stores** | **Adotado** | **MLflow Tracking** | Rastreamento completo de experimentos (benchmark **LLM puro × RAG + Multiagentes**), hiperparâmetros de chunking/`top_k`/temperatura, latência e métricas de fidelidade e acerto em contraindicações críticas. |
| **C8** | **Model Serving Component** | **Adotado** | **API REST em Docker (FastAPI/Flask) + Streamlit** | Desacoplamento rigoroso entre inteligência (API REST containerizada validando o Contrato JSON) e experiência do cidadão (interface web leve de página única em Streamlit). |
| **C9** | **Monitoring Component** | **Adotado (sem ação autônoma)** | **Prometheus + Grafana** | Coleta contínua de métricas operacionais da API (latência, erros HTTP, tempo de RAG) e de produto (feedback *"Útil"*/*Inútil* e alertas graves), gerando alertas para revisão humana (*human-in-the-loop*) sem retreinamento/reindexação automática. |

---

## 3. Justificativa Detalhada das Adoções

### 3.1. GitHub Actions (`C1` — CI/CD)

* **Decisão:** Adotar **GitHub Actions** como esteira de integração contínua.
* **Justificativa:**
  * Integrado nativamente ao repositório GitHub da organização da disciplina, com cota gratuita (R$ 0,00) para execução de workflows.
  * Garante qualidade contínua antes do *merge* na branch `main`: verificação de estilo (*lint*), testes unitários dos agentes e da API, validação automática de conformidade com o Contrato JSON e checagem de preenchimento dos 5 metadados obrigatórios na ingestão documental.
  * Evita regressões silenciosas no código e nos contratos entre as frentes paralelas (`#11`, `#12` e `#24`).

### 3.2. Base Vetorial Local (`C4` adaptado para RAG)

* **Decisão:** Adotar uma **Base Vetorial local open-source** (persistida em volume Docker local — recomendando-se **ChromaDB** ou **Qdrant local**, ou **FAISS** acoplado a índice de metadados, a ser consolidado na issue `#11`) com suporte nativo à filtragem por metadados obrigatórios.
* **Justificativa:**
  * Elimina custos recorrentes de bancos vetoriais gerenciados em nuvem (Pinecone, Zilliz Cloud, OpenSearch gerenciado), mantendo o custo rigorosamente em **R$ 0,00**.
  * Para o volume documental do MVP (dezenas de bulas selecionadas da Anvisa, Calendário Nacional de Vacinação e protocolos clínicos de dengue, malária e gripe — ordem de milhares de *chunks*), uma base vetorial local oferece busca semântica com latência de poucos milissegundos e pegada de memória reduzida.
  * Permite filtragem híbrida combinando similaridade vetorial e metadados obrigatórios (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`), essencial para restringir buscas a trechos de contraindicação para gestantes ou interações medicamentosas específicas.
  * Facilita a reprodutibilidade: o snapshot do índice vetorial gerado pelo pipeline *batch* é versionado e referenciado no MLflow, garantindo que o mesmo índice usado na avaliação seja servido em produção.

### 3.3. MLflow (Tracking + Model Registry) (`C6` e `C7`)

* **Decisão:** Adotar **MLflow** em modo *self-hosted* (container Docker local com backend SQLite/artefatos locais) cobrindo simultaneamente **Tracking** e **Model Registry**.
* **Justificativa:**
  * Atende diretamente a duas restrições centrais do Challenge 2: **validar com métricas objetivas** e **justificar decisões técnicas**.
  * **MLflow Tracking (`C7`):** permite executar e comparar de forma auditável o benchmark **LLM puro × RAG + Multiagentes**, registrando por execução: versão do corpus/índice vetorial, estratégia de *chunking* (`chunk_size`, `overlap`), modelo de *embedding*, `top_k`, *prompt* de cada agente, latência média, fidelidade à fonte (*groundedness*) e taxa de acerto nos casos críticos de contraindicação (meta: 100%).
  * **MLflow Model Registry (`C6`):** unifica a governança de versões do pipeline RAG/multiagentes (empacotado como modelo `pyfunc` ou artefato de configuração versionado), aplicando ciclo de vida formal (`Staging` → `Production` → `Archived`) e assegurando que 100% das versões servidas pela API REST sejam rastreáveis.
  * Ferramenta 100% *open source*, leve para subir via Docker Compose e padrão consolidado na disciplina de Sistemas de Machine Learning.

### 3.4. API REST em Docker (`C8` — Serving Desacoplado)

* **Decisão:** Empacotar o motor multiagentes + RAG como uma **API REST** (preferencialmente **FastAPI** pela tipagem nativa com Pydantic e documentação OpenAPI automática, ou Flask com validação de schema equivalente) executada em **container Docker** (orquestrada localmente via `docker-compose.yml`).
* **Justificativa:**
  * **Desacoplamento arquitetural:** separa integralmente a camada de inferência/orquestração de agentes da camada de apresentação (Streamlit), permitindo evoluir qualquer interface futura (web SPA, aplicativo móvel ou integração externa) consumindo o mesmo contrato JSON.
  * **Garantia de contrato:** validação estrita na fronteira da API assegura que entradas inválidas sejam rejeitadas com clareza e que nenhuma saída clínica chegue ao usuário sem `evidencias_oficiais` válidas e `disclaimer_medico`.
  * **Reprodutibilidade ("funciona na minha máquina"):** o container Docker congela versão de Python, dependências, variáveis de ambiente e conexão com a Base Vetorial local, MLflow e Prometheus, garantindo execução idêntica nas máquinas dos 5 integrantes e na apresentação final em 07/12.
  * **Instrumentação nativa:** facilita a exposição do endpoint `/metrics` para raspagem direta pelo Prometheus.

### 3.5. Streamlit (`C8` — Camada de Apresentação / Painel de Apoio à Decisão)

* **Decisão:** Adotar **Streamlit** como interface web de página única para o MVP, comunicando-se exclusivamente via HTTP com a API REST.
* **Justificativa:**
  * Entrega extrema produtividade em Python para uma equipe de 5 pessoas em horizonte de 6 semanas, eliminando o esforço de estruturar um frontend SPA completo (React/Next.js/Tailwind + build separado) que não agrega diferenciação científica ao Challenge 2.
  * Atende com clareza todos os requisitos funcionais do **Cluster 4 (Painel de Apoio à Decisão)** da *Lean Inception*: formulário estruturado de perfil e checklist manual de vacinas, campo de texto livre para sintomas/medicamento, cards de resposta com selo visual de risco (*Indicada*, *Contraindicada*, *Alerta de Risco Grave*), bloco expansível com citação literal da fonte oficial (Anvisa/MS), *disclaimer* médico fixo e botões simples de avaliação (*Útil* / *Inútil*).
  * Roda em container próprio no `docker-compose.yml` com custo R$ 0,00.

### 3.6. Prometheus + Grafana (`C9` — Monitoramento e Observabilidade)

* **Decisão:** Adotar **Prometheus** (coleta de séries temporais via *pull* no endpoint `/metrics` da API REST) e **Grafana** (visualização de dashboards e alertas operacionais), ambos containerizados via Docker Compose.
* **Justificativa:**
  * Custo R$ 0,00 (*open source*) e padrão de indústria para observabilidade em MLOps.
  * Fecha o ciclo de vida operacional do sistema (Etapa 6 das Jornadas da Mariana e do Pedro), monitorando duas camadas complementares sem armazenar dados pessoais identificáveis (LGPD):
    * **Métricas técnicas/infraestrutura:** latência de inferência (p50, p95, p99), tempo gasto na busca vetorial (RAG) vs. geração dos agentes, taxa de requisições por segundo, contagem de erros HTTP (`4xx`/`5xx`) e disponibilidade (*uptime*) do container.
    * **Métricas de negócio/qualidade em produção:** distribuição de consultas por rota (`triagem_vacinal`, `interacao_medicamentosa`, `condutas_doenca`), taxa de respostas com `EVIDENCIA_INSUFICIENTE`, frequência de `ALERTA_RISCO_GRAVE` e proporção de avaliações *"Útil"* vs. *"Inútil"*.

---

## 4. Justificativa Detalhada das Omissões e Simplificações

Decisões arquiteturais maduras definem tanto o que entra quanto o que é deliberadamente deixado de fora. Abaixo registram-se as três grandes omissões justificadas do MVP:

### 4.1. Omissão de Feature Store Tradicional *(ex.: Feast, Tecton, AWS Feature Store)*

* **Decisão:** **Não adotar** uma *Feature Store* tradicional no MVP.
* **Justificativa Técnica:**
  * *Feature Stores* tradicionais resolvem o problema de *training-serving skew* para **dados tabulares históricos** que exigem agregações temporais consistentes entre treino *offline* e inferência *online* de baixa latência (ex.: média de transações dos últimos 30 dias em modelos de fraude ou risco de crédito).
  * O **EvidencIA Saúde** não treina modelos supervisionados sobre tabelas históricas de usuários. Seu conhecimento reside em **documentos textuais regulatórios semiestruturados** (bulas da Anvisa e protocolos do Ministério da Saúde), cujas representações numéricas (*embeddings*) são gerenciadas de forma muito mais adequada pela **Base Vetorial Local** indexada com os 5 metadados obrigatórios.
  * Os atributos estruturados do cidadão (faixa etária, condição de gestante, comorbidades, checklist vacinal) são informados em tempo real na sessão e descartados ao término da requisição (*stateless*) por exigência da **LGPD** — portanto, não existe histórico persistente de *features* de usuários para armazenar ou servir.
  * Introduzir uma *Feature Store* como Feast adicionaria bancos extras (Redis/PostgreSQL/Parquet), complexidade operacional e zero ganho funcional ao caso de uso.

### 4.2. Omissão de Kubernetes *(K8s / EKS / GKE / AKS)*

* **Decisão:** **Não adotar** Kubernetes no MVP; utilizar **Docker + Docker Compose** como camada de containerização e orquestração local.
* **Justificativa Técnica:**
  * **Restrição financeira (R$ 0,00):** clusters gerenciados de Kubernetes em nuvem incorrem em custos diretos de plano de controle e nós de computação, violando a restrição de custo zero.
  * **Custo de complexidade vs. escala do MVP:** o escopo do Challenge 2 exige validação científica, demonstração funcional reprodutível e maturidade de MLOps, sem demanda de alta disponibilidade multirregional ou auto-escalonamento horizontal elástico para milhares de usuários simultâneos.
  * **Foco da equipe (5 pessoas, 6 semanas):** manter manifestos Helm/K8s, *Ingress*, *RBAC*, *PersistentVolumeClaims* e *Service Mesh* desviaria esforço crítico de `R6`/`R7` e `R5` que deve estar concentrado na qualidade do RAG, na segurança dos agentes e na observabilidade.
  * **Caminho de evolução preservado:** como todos os componentes (API REST, Streamlit, Base Vetorial, MLflow, Prometheus e Grafana) já nascem **containerizados em Docker** e desacoplados via rede interna/REST, uma eventual migração pós-MVP para Kubernetes torna-se incremental e livre de refatoração estrutural.

### 4.3. Omissão de Reindexação Autônoma e Retreinamento Automático *(Closed-Loop Automation)*

* **Decisão:** **Não adotar** *web scraping* automatizado, reindexação autônoma da base vetorial nem retreinamento/atualização automática de prompts em produção a partir de feedback; adotar **ingestão *batch* curada** e **alertas *human-in-the-loop***.
* **Justificativa Técnica e Clínica:**
  * **Segurança clínica inegociável:** no domínio de saúde, a alteração autônoma da base de conhecimento (por exemplo, um *crawler* que captura um PDF mal formatado da Anvisa, uma nota técnica revogada ou quebra a tabela de contraindicações durante o *chunking*) pode introduzir falsos negativos graves em produção sem que a equipe perceba.
  * **Risco de envenenamento por feedback (*Feedback Poisoning*):** acionar ajustes automáticos diretamente a partir do botão *"Inútil"* de usuários finais (sem curadoria clínica/técnica) é vulnerável a ruído ou interpretações leigas incorretas (por exemplo, um usuário marcar *"Inútil"* justamente porque o sistema contraindicou o medicamento que ele queria tomar).
  * **Alinhamento ao paradigma LLMOps:** o MVP utiliza LLMs pré-treinados + RAG (sem ajuste contínuo de pesos). Logo, a evolução segura ocorre por meio de um ciclo controlado: **Prometheus/Grafana detecta anomalia ou queda de satisfação → alerta à equipe → curadoria manual de documentos/prompts (`R4`/`R3`) → reexecução do benchmark no MLflow exigindo 100% nos casos críticos → promoção manual no MLflow Model Registry → novo deploy containerizado**.
  * **Horizonte de evolução:** a automação de coleta periódica via **Apache Airflow** (gerando candidatos de atualização para aprovação humana antes da promoção) está formalmente mapeada no [Horizonte de Evolução Pós-MVP](/concepcao/lean-inception.md?id=horizonte-pos-mvp).

---

## 5. Consequências e Trade-offs Aceitos

| Dimensão | Benefícios Conquistados | Trade-offs Aceitos e Mitigação |
| :--- | :--- | :--- |
| **Custo e Viabilidade** | Stack 100% *open source* sob **R$ 0,00**, executável em qualquer máquina com Docker instalado. | Limitação de paralelismo pesado de LLMs locais; mitigada pelo recorte fechado de doenças/vacinas do MVP e uso controlado de modelos eficientes/APIs de camada gratuita. |
| **Velocidade de Entrega** | Foco máximo na qualidade do RAG, segurança dos agentes e testes objetivos até **07/12**, evitando meses de setup em K8s/Airflow/Feast. | Atualizações de novas notas técnicas da Anvisa/MS dependem de execução *batch* manual pela equipe; mitigado por scripts reprodutíveis e versionamento de índice no MLflow. |
| **Segurança Clínica** | Controle humano obrigatório (*human-in-the-loop*) impede degradação silenciosa da base de evidências oficiais. | Tempo de resposta a novas atualizações regulatórias não é instantâneo; mitigado pela exibição explícita da data/versão da fonte oficial citada ao cidadão. |
| **Evolução Futura** | Fronteiras limpas (API REST + Contrato JSON + Containers Docker) permitem evoluir para Kubernetes, Airflow, OCR/ASR e SPA sem reescrever o núcleo de IA. | Streamlit impõe limitações de customização visual avançada frente a uma SPA dedicada; aceito integralmente para o escopo do MVP. |
