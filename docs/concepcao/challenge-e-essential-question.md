# Challenge 2 e Essential Question

Este documento formaliza o enquadramento do projeto **EvidencIA Saúde** no **Challenge 2** da disciplina de Sistemas de Machine Learning (UnB), estabelecendo a *Big Idea*, o *Challenge Statement*, as 5 restrições obrigatórias, a *Essential Question* do grupo e o cronograma oficial de entregas.

---

## 1. Big Idea e Challenge Statement

### Big Idea: Qualidade de Vida

> *"Empoderando pessoas com IA para compreender melhor, decidir melhor e viver melhor."*

### Challenge Statement

> **Projetar e desenvolver uma solução baseada em IA capaz de apoiar a tomada de decisão em um contexto relacionado à qualidade de vida.**

A partir dessa diretriz, o grupo escolheu atuar no domínio da **saúde preventiva e manejo inicial seguro pelo cidadão**, atacando dois problemas concretos e recorrentes no cotidiano brasileiro:

1. **Insegurança e atraso na imunização:** cidadãos — em especial públicos com restrições clínicas específicas, como gestantes — têm dificuldade em cruzar cartões vacinais físicos com o Calendário Nacional de Vacinação do Ministério da Saúde e identificar contraindicações.
2. **Automedicação de alto risco em doenças agudas:** diante de sintomas de doenças endêmicas ou sazonais (como dengue, malária e gripe), cidadãos frequentemente recorrem a medicamentos contraindicados (por exemplo, anti-inflamatórios não esteroidais como Ibuprofeno em suspeita de dengue) sem compreender bulas técnicas da Anvisa ou protocolos clínicos oficiais.

---

## 2. Formalização da Essential Question

> **Essential Question do EvidencIA Saúde:**  
> *"Como apoiar cidadãos na tomada de decisão segura sobre vacinação pendente, manejo de sintomas e contraindicações de medicamentos usando evidências oficiais da Anvisa e do Ministério da Saúde?"*

### Decomposição Analítica da Essential Question

| Dimensão da Pergunta | Definição no Projeto | Conexão com a Big Idea |
| :--- | :--- | :--- |
| **Quem é empoderado?** | Cidadãos leigos (representados pelas personas Mariana e Pedro) em situações de dúvida vacinal ou sintomas agudos. | **Compreender melhor:** traduzir bulas e protocolos técnicos em linguagem acessível e estruturada. |
| **Qual decisão é apoiada?** | Identificar vacinas pendentes, reconhecer contraindicações graves de vacinas/medicamentos e adotar condutas iniciais seguras antes ou até o atendimento profissional. | **Decidir melhor:** substituir buscas fragmentadas e chatbots sujeitos a alucinação por triagem fundamentada. |
| **Qual o impacto esperado?** | Reduzir atrasos vacinais evitáveis e prevenir eventos adversos por automedicação contraindicada. | **Viver melhor:** promover prevenção e segurança em saúde no dia a dia. |
| **Qual a garantia de confiabilidade?** | Respostas ancoradas exclusivamente em documentos oficiais da **Anvisa** e do **Ministério da Saúde** recuperados via motor **RAG** e orquestrados por **agentes especializados**. | **IA Responsável:** rastreabilidade literal da evidência, explicitação de limitações e conformidade com a LGPD. |

---

## 3. Atendimento às 5 Restrições do Challenge 2

O Challenge 2 estabelece cinco restrições inegociáveis. A tabela abaixo registra como cada uma é atendida e auditada na arquitetura e documentação do **EvidencIA Saúde**:

| # | Restrição do Challenge 2 | Como o EvidencIA Saúde Atende | Artefatos de Evidência |
| :-: | :--- | :--- | :--- |
| **1** | **Entender o problema antes da solução** | Condução completa de *Lean Inception* (Visão, É/Não É/Faz/Não Faz, Personas, Jornadas de 6 etapas, Clusters com cortes explícitos e Canvas MVP) antes da implementação de código. | [Lean Inception e Canvas MVP](/concepcao/lean-inception.md) |
| **2** | **Justificar decisões técnicas** | Formalização de *Architecture Decision Record* (ADR-001) avaliando os 9 componentes de MLOps (C1–C9) sob restrição de custo zero (R$ 0,00), justificando adoções, simplificações e omissões, além de contratos JSON e metadados padronizados. | [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md) e [Contrato JSON e Metadados](/arquitetura/contrato-json-e-metadados-rag.md) |
| **3** | **Explicitar riscos e limitações** | Mapeamento formal de riscos clínicos e operacionais, análise de vieses (documental, linguístico, de pré-treinamento e de automação), *disclaimers* médicos obrigatórios, política *fail-safe* e adequação à LGPD. | [Riscos Clínicos, Viés, Ética e LGPD](/governanca/riscos-vies-etica-lgpd.md) |
| **4** | **Validar com métricas objetivas** | Experimentação rastreada no MLflow comparando **LLM puro × RAG + Multiagentes**, exigindo fidelidade à fonte oficial e **100% de acerto nos casos críticos de contraindicação**, além de latência e feedback *"Útil"/"Inútil"* no Prometheus/Grafana. | [As 5 Perguntas de MLOps](/arquitetura/perguntas-fundamentais-mlops.md) e [Canvas MVP](/concepcao/lean-inception.md?id=canvas-mvp) |
| **5** | **Utilizar evidências confiáveis** | Restrição estrita da base de conhecimento a bulas oficiais da **Anvisa** e calendários/protocolos clínicos do **Ministério da Saúde**, com esquema de metadados obrigatórios e regra de contrato que proíbe recomendações sem citação literal. | [Contrato JSON e Metadados do RAG](/arquitetura/contrato-json-e-metadados-rag.md) |

---

## 4. Pilares Conceituais e Temáticos da Disciplina

O desenho do **EvidencIA Saúde** cobre integralmente o ecossistema conceitual do Challenge 2:

* **Fundamentos de Concepção:** entendimento do problema, levantamento de requisitos, mapeamento de *stakeholders* e definição de métricas objetivas.
* **Engenharia de IA Generativa e Agentes:** *prompt engineering*, sistemas multiagentes especializados, gestão de contexto/memória de sessão e recuperação aumentada por geração (**RAG**).
* **Qualidade, Confiabilidade e IA Responsável:** mitigação de riscos clínicos e vieses, rastreabilidade de fontes oficiais, observabilidade operacional e privacidade de dados sensíveis sob a **LGPD**.

---

## 5. Roadmap Oficial do Challenge 2

O planejamento do projeto segue o cronograma oficial de 6 semanas até a entrega final em **07/12**, respeitando as restrições de prazo e os feriados do período:

| Semana | Período | Foco | Entregável Principal | Alinhamento no EvidencIA Saúde |
| :-: | :--- | :--- | :--- | :--- |
| **1** | 26/10 – 01/11 | Problema, stakeholders, riscos e métricas | Definições do projeto | Lean Inception, Essential Question, Papéis (R1–R7), ADR-001, Contratos JSON/RAG e Documento de Riscos, Viés e LGPD. |
| **2** | 02/11 – 08/11 | Base de conhecimento, recuperação e comparação LLM × RAG | Primeiro mecanismo RAG + respostas baseadas em evidências | Ingestão batch Anvisa/MS com metadados obrigatórios (`#11`), base vetorial local e benchmark LLM puro × RAG no MLflow. |
| **3** | 09/11 – 15/11 | Sistema multiagentes | Primeiro sistema multiagentes | Agente Estruturador/Roteador + Agente de Triagem Vacinal + Agente de Medicamentos e Condutas respeitando o contrato JSON (`#13`–`#16`). |
| **4** | 16/11 – 22/11 | Multimodalidade | Agentes multimodais | Agente Estruturador/Multimodal unificando entradas estruturadas (perfil + checklist vacinal) e não estruturadas (relato textual), preparado para evolução futura (OCR/ASR). |
| **5** | 23/11 – 29/11 | Integração completa | Aplicação funcional | API REST em Docker + Painel Streamlit + MLflow Registry + Prometheus/Grafana + ciclo de feedback (`#20`, `#21` e `#22`). |
| **6** | 30/11 – 06/12 | Testes e refinamento | Relatório final + apresentação | Validação ponta a ponta das jornadas da Mariana e do Pedro, auditoria de 100% em casos críticos de contraindicação e consolidação do relatório. |
| **Entrega** | **07/12** | **Entrega final** | **Aplicação, relatório e apresentação** | Demonstração funcional completa sob custo zero (R$ 0,00), código versionado e documentação publicada. |

> **Feriados no período:** 02/11 (Finados) e 20/11 (Consciência Negra), já considerados nos cortes de escopo do MVP definidos na Lean Inception.
