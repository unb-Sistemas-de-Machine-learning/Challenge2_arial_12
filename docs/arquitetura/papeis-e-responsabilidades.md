# Matriz de Papéis e Responsabilidades (R1 a R7)

A disciplina de MLOps define a operacionalização de sistemas de Inteligência Artificial como um esforço estritamente interdisciplinar. Este documento mapeia os **7 papéis fundamentais de MLOps (`R1` a `R7`)**, definidos no framework de referência de **Kreuzberger, Kühl e Hirschl (2023)** (*"Machine Learning Operations (MLOps): Overview, Definition, and Architecture"*, IEEE Access), entre os **5 integrantes** da equipe do **EvidencIA Saúde**.

---

## 1. Integrantes e Papéis Declarados no Projeto

<table class="team-table">
  <tr>
    <td align="center">
      <a href="https://github.com/andre-maia51">
        <img src="https://github.com/andre-maia51.png" width="100px;" alt="Imagem de André Maia"/><br />
        <sub><b>André Maia</b><br />Arquiteto de Soluções e Dados</sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Brenofrds">
        <img src="https://github.com/Brenofrds.png" width="100px;" alt="Imagem de Breno Soares Fernandes"/><br />
        <sub><b>Breno Soares Fernandes</b><br />Engenheiro de Software / Fullstack</sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/EhOBruno">
        <img src="https://github.com/EhOBruno.png" width="100px;" alt="Imagem de Bruno Ricardo de Menezes"/><br />
        <sub><b>Bruno Ricardo de Menezes</b><br />Engenheiro de MLOps / LLMOps</sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/CADU110">
        <img src="https://github.com/CADU110.png" width="100px;" alt="Imagem de Carlos Eduardo Mota"/><br />
        <sub><b>Carlos Eduardo Mota</b><br />Engenheiro de Dados</sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/PhFariaa">
        <img src="https://github.com/PhFariaa.png" width="100px;" alt="Imagem de Pedro Henrique Faria"/><br />
        <sub><b>Pedro Henrique Faria</b><br />Cientista de Dados</sub>
      </a>
    </td>
  </tr>
</table>

---

## 2. Mapeamento dos Papéis R1 a R7 (Kreuzberger et al., 2023)

| Código | Papel no MLOps | Definição na Literatura | Titular (Responsável Principal) | Co-responsável / Apoio | Entregáveis e Responsabilidades no EvidencIA Saúde |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **R1** | **Business Stakeholder** *(Product Owner / Gestão de Produto)* | Define metas de negócio, prioriza escopo, valida critérios de sucesso, valor entregue e conformidade com restrições do projeto. | **André Maia** (`@andre-maia51`) | Toda a equipe (especialmente **Pedro Henrique Faria** em métricas de validação e **Breno Soares Fernandes** em UX/jornadas) | Formalização da *Essential Question*, condução e guarda dos artefatos da *Lean Inception* (Visão, Personas Mariana/Pedro, Jornadas, cortes de escopo e Canvas MVP), validação dos critérios de aceite e governança ética/LGPD. |
| **R2** | **Solution Architect** *(Arquiteto de Soluções)* | Projeta a arquitetura ponta a ponta do sistema de IA, avalia trade-offs tecnológicos e define contratos de integração. | **André Maia** (`@andre-maia51`) | **Bruno Ricardo de Menezes** (infra MLOps) e **Carlos Eduardo Mota** (arquitetura de dados) | Elaboração do [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md) sob custo zero (R$ 0,00), definição do [Contrato JSON](/arquitetura/contrato-json-e-metadados-rag.md) entre interface, API e agentes, desenho do esquema de metadados obrigatórios do RAG e coerência arquitetural ponta a ponta. |
| **R3** | **Data Scientist** *(Cientista de Dados)* | Traduz o problema em solução de IA/ML, conduz experimentação, seleção de modelos, engenharia de prompts e avaliação por métricas objetivas. | **Pedro Henrique Faria** (`@PhFariaa`) | **Carlos Eduardo Mota** (qualidade do corpus/chunking) e **Bruno Ricardo de Menezes** (logging no MLflow) | Implementação e ajuste do motor RAG (embeddings, estratégia de recuperação, *top-k*, *reranking*/filtros), criação e engenharia de prompts dos agentes (Estruturador/Roteador, Triagem Vacinal e Medicamentos/Condutas), construção do conjunto de avaliação crítica e benchmark **LLM puro × RAG + Multiagentes** no MLflow. |
| **R4** | **Data Engineer** *(Engenheiro de Dados)* | Constrói e mantém pipelines de coleta, limpeza, normalização, enriquecimento, versionamento e indexação dos dados. | **Carlos Eduardo Mota** (`@CADU110`) | **André Maia** (arquitetura e esquema de dados) e **Pedro Henrique Faria** (testes de recuperação) | Coleta curada de bulas oficiais da Anvisa e calendários/protocolos clínicos do Ministério da Saúde (dengue, malária, gripe e calendário adulto/gestante), normalização textual, chunking estruturado, preenchimento validado dos 5 metadados obrigatórios (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`) e pipeline *batch* de carga na Base Vetorial local (`#11`). |
| **R5** | **Software Engineer** *(Engenheiro de Software)* | Aplica padrões de engenharia de software, qualidade de código, APIs, interface de usuário e testes automatizados para transformar modelos em produto. | **Breno Soares Fernandes** (`@Brenofrds`) | **André Maia** (contratos) e **Bruno Ricardo de Menezes** (Docker/CI) | Desenvolvimento da API REST em FastAPI/Flask validando rigorosamente o Contrato JSON (`POST /api/v1/consultar` e `POST /api/v1/feedback`), desenvolvimento do Painel de Apoio à Decisão em **Streamlit** (formulário estruturado + relato textual, selos de risco, citações literais, *disclaimer* fixo e botão *Útil*/*Inútil*), integração com os agentes (`#21`) e testes automatizados de API e contrato. |
| **R6** | **DevOps Engineer** *(Engenheiro DevOps)* | Automatiza integração e entrega contínuas (CI/CD), padroniza ambientes, containers e provisionamento reprodutível de infraestrutura. | **Bruno Ricardo de Menezes** (`@EhOBruno`) | **Breno Soares Fernandes** (containerização da API e Streamlit) | Configuração das esteiras de CI no **GitHub Actions** (linting, testes unitários, validação de schema JSON, verificação de build), criação e manutenção de `Dockerfile` e `docker-compose.yml` unificando todos os serviços localmente sem custo. |
| **R7** | **ML / MLOps Engineer** *(Engenheiro de MLOps / LLMOps)* | Papel *cross-domain* que opera a infraestrutura de ML/LLM, rastreamento de experimentos, registro de modelos, *serving* observável e monitoramento contínuo. | **Bruno Ricardo de Menezes** (`@EhOBruno`) | **Pedro Henrique Faria** (métricas de qualidade) e **Breno Soares Fernandes** (instrumentação da API) | Operação do **MLflow Tracking e Model Registry** (versionamento de pipelines, prompts e índices vetoriais), instrumentação de métricas da API e do ciclo de feedback no **Prometheus**, construção de dashboards e alertas operacionais no **Grafana** e governança de reprodutibilidade e *human-in-the-loop*. |

---

## 3. Justificativa da Consolidação de 7 Papéis em 5 Integrantes

Equipes enxutas de MVP raramente dispõem de 7 especialistas dedicados exclusivamente a cada função. Conforme reconhecido por Kreuzberger et al. (2023), a consolidação de papéis adjacentes é uma prática recomendada desde que se preserve a **segregação de responsabilidades entre dados, modelagem, software e operação**:

1. **Consolidação de `R1` + `R2` em André Maia (Arquiteto de Soluções e Dados):** Unificar a visão de negócio/produto (`R1`) com a arquitetura de soluções e dados (`R2`) elimina ruído entre requisitos clínicos do Challenge 2 e decisões técnicas (ADR, contratos JSON e conformidade LGPD), mantendo o escopo estritamente alinhado à *Lean Inception*.
2. **Consolidação de `R6` + `R7` em Bruno Ricardo de Menezes (Engenheiro de MLOps / LLMOps):** Na prática moderna de LLMOps sob infraestrutura containerizada local (Docker Compose + GitHub Actions), automação DevOps (`R6`) e operação de MLflow/Prometheus/Grafana (`R7`) compartilham a mesma base tecnológica e de infraestrutura, evitando handoffs lentos no cronograma de 6 semanas.
3. **Dedicação exclusiva nos três núcleos de maior risco técnico:** Engenharia de Dados (`R4` — Carlos Eduardo), Ciência de Dados / RAG & Multiagentes (`R3` — Pedro Henrique) e Engenharia de Software / API & Streamlit (`R5` — Breno Soares) permanecem dedicados a integrantes distintos, garantindo paralelismo real a partir das issues `#11` (dados), `#13`–`#16` (RAG e agentes) e `#12`/`#21` (interface e API).

---

## 4. Matriz RACI por Macroentrega e Roadmap

Legenda: **R** = Responsável pela execução (*Responsible*) | **A** = Aprovador final (*Accountable*) | **C** = Consultado (*Consulted*) | **I** = Informado (*Informed*).

| Semana / Entrega | Macroatividade | André (`R1`/`R2`) | Carlos (`R4`) | Pedro (`R3`) | Breno (`R5`) | Bruno (`R6`/`R7`) |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| **Semana 1** *(26/10–01/11)* | Lean Inception, Essential Question, ADR-001, Contratos JSON/RAG e Riscos/LGPD | **R / A** | **C** | **C** | **C** | **C** |
| **Semana 2** *(02/11–08/11)* | Coleta Anvisa/MS, limpeza, metadados obrigatórios e ingestão na Base Vetorial (`#11`) | **A** | **R** | **C** | **I** | **C** |
| **Semana 2** *(02/11–08/11)* | Motor RAG e benchmark comparativo **LLM puro × RAG** no MLflow | **I** | **C** | **R / A** | **I** | **C** |
| **Semana 3** *(09/11–15/11)* | Sistema Multiagentes (Estruturador/Roteador, Triagem Vacinal, Medicamentos/Condutas) (`#13`–`#16`) | **A** | **C** | **R** | **C** | **C** |
| **Semana 4** *(16/11–22/11)* | Agente Estruturador/Multimodal (perfil tabular + relato textual → JSON) | **C** | **I** | **R** | **R / A** | **I** |
| **Semana 5** *(23/11–29/11)* | API REST em Docker + Painel Streamlit + fluxo de feedback (`#21` e `#22`) | **A** | **I** | **C** | **R** | **C** |
| **Semana 5** *(23/11–29/11)* | CI/CD (GitHub Actions), Docker Compose, MLflow Registry e Prometheus/Grafana | **I** | **C** | **C** | **C** | **R / A** |
| **Semana 6** *(30/11–06/12)* | Testes ponta a ponta (Mariana/Pedro), auditoria de 100% em casos críticos e relatório final | **R / A** | **R** | **R** | **R** | **R** |
| **Entrega** *(07/12)* | Apresentação final, demonstração funcional e validação do repositório | **R / A** | **R** | **R** | **R** | **R** |

---

## 5. Governança de Colaboração e Revisão Cruzada

Para assegurar qualidade contínua e evitar pontos únicos de falha no repositório:

* **Revisão obrigatória por papéis adjacentes em Pull Requests:**
  * Alterações no pipeline de ingestão e metadados (`R4`) são revisadas pelo Cientista de Dados (`R3`) e pelo Arquiteto (`R2`).
  * Alterações em prompts, agentes e avaliação (`R3`) são revisadas pelo Engenheiro de MLOps (`R7`) e pelo Engenheiro de Software (`R5`).
  * Alterações em contratos da API e interface Streamlit (`R5`) são revisadas pelo Arquiteto (`R2`) e pelo Cientista de Dados (`R3`).
  * Alterações em CI/CD, Dockerfiles, MLflow e Prometheus/Grafana (`R6`/`R7`) são revisadas pelo Engenheiro de Software (`R5`) e pelo Arquiteto (`R2`).
* **Padrão de contribuição:** Todos os PRs seguem o template oficial do repositório (`.github/pull_request_template.md`) com título semântico (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`), referência explícita à issue relacionada e roteiro reproduzível de teste.
