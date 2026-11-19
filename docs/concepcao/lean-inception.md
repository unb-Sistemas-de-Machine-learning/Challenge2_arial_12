# Lean Inception e Canvas MVP

> **Contexto:** Challenge 2 — *Big Idea: Qualidade de Vida* ("Empoderando pessoas com IA para compreender melhor, decidir melhor e viver melhor.")  
> **Produto:** **EvidencIA Saúde**  
> **Entrega Final:** 07/12 | **Equipe:** 5 pessoas | **Custo Previsto:** R$ 0,00 (Stack 100% *Open Source*)

Este documento transpõe e consolida os artefatos produzidos nas atividades da **Lean Inception** para alinhar visão de produto, limites de escopo, perfis de usuários, pontos de contato com a IA, recortes funcionais e critérios de validação do MVP.

---

## 1. Visão do Produto e Essential Question *(Atividade 1)*

### Essential Question

> *"Como apoiar cidadãos na tomada de decisão segura sobre vacinação pendente, manejo de sintomas e contraindicações de medicamentos usando evidências oficiais da Anvisa e do Ministério da Saúde?"*

### Declaração da Visão do Produto

* **Para:** cidadãos que precisam cuidar da imunização e agir diante de sintomas ou doenças;
* **Cujo problema é:** a dúvida sobre vacinas pendentes, o que fazer em casos como dengue ou malária e o risco de tomar remédios contraindicados;
* **O EvidencIA Saúde** é um **assistente inteligente de apoio à decisão em saúde**;
* **Que:** identifica vacinas faltantes e alerta sobre condutas e contraindicações de vacinas e medicamentos de forma simples e multimodal;
* **Diferentemente de:** buscas no Google, leitura de bulas complexas ou chatbots genéricos que alucinam;
* **O nosso produto:** responde exclusivamente com base em evidências oficiais estruturadas da Anvisa e do Ministério da Saúde via RAG (*Retrieval-Augmented Generation*) e múltiplos agentes especializados.

---

## 2. Escopo Conceitual: É / NÃO É / FAZ / NÃO FAZ *(Atividade 2)*

| O Produto **É** | O Produto **NÃO É** |
| :--- | :--- |
| Um sistema de apoio à decisão em saúde preventiva e manejo inicial baseado em evidências oficiais (Anvisa e Ministério da Saúde). | Um médico, prontuário clínico definitivo ou prescritor de receitas controladas. |

| O Produto **FAZ** | O Produto **NÃO FAZ** |
| :--- | :--- |
| • Cruza o perfil e o cartão vacinal do usuário com o calendário oficial do Ministério da Saúde.<br>• Verifica indicações e contraindicações de vacinas e medicamentos via RAG em bulas da Anvisa e protocolos clínicos.<br>• Alerta sobre riscos graves de contraindicação. | • Diagnóstico médico fechado.<br>• Qualquer recomendação sem citar a fonte oficial extraída pelo motor RAG. |

---

## 3. Personas Segmentadas *(Atividade 3)*

### Persona 1: Mariana *(Foco: Imunização e Segurança na Gestação)*

* **Perfil:** 32 anos, gestante de 20 semanas, professora do ensino fundamental. Possui rotina corrida entre aulas e consultas de pré-natal, guarda um cartão de vacina de papel antigo e rasurado da adolescência e tem forte receio de tomar qualquer substância que possa afetar a gravidez.
* **Comportamento:**
  * Não lembra quais reforços da vida adulta já tomou.
  * Pesquisa no Google ou em grupos de mães se gestante pode tomar vacinas como febre amarela, dTpa ou dengue.
  * Fica paralisada diante de informações contraditórias na internet e acaba adiando a ida ao posto de saúde.
* **Necessidades:**
  * Identificar quais vacinas faltam de forma prática.
  * Confirmar com segurança se possui contraindicação para alguma vacina devido à gestação.
  * Receber respostas baseadas em evidências confiáveis do Ministério da Saúde e da Anvisa para apoiar sua decisão.

### Persona 2: Pedro *(Foco: Doenças Agudas e Risco de Automedicação)*

* **Perfil:** 26 anos, mora sozinho, técnico de campo que viaja a trabalho, frequentemente exposto a doenças sazonais ou endêmicas. É prático e imediatista quando fica doente.
* **Comportamento:**
  * Não lê bulas da Anvisa por achá-las longas e técnicas demais.
  * Ao sentir febre alta e dor no corpo, recorre à automedicação com o que tem em casa para não perder o dia de trabalho.
  * Faz perguntas rápidas em buscadores ou LLMs genéricos sobre o que tomar quando apresenta sintomas.
* **Necessidades:**
  * Checar rapidamente se pode tomar um medicamento diante da suspeita de uma doença.
  * Ser alertado sobre riscos graves de contraindicação.
  * Obter orientações claras sobre quais atitudes e cuidados adotar, fundamentadas em fontes oficiais para decidir melhor.

---

## 4. Jornadas do Usuário e Pontos de Contato com a IA *(Atividade 4)*

### Jornada 1 — Mariana *(Triagem Vacinal e Gestação)*

| Etapa | Passo da Jornada do Usuário | Ponto de Contato com a IA / Sistema |
| :--- | :--- | :--- |
| **1. Dúvida inicial** | Pega seu cartão de vacina físico e fica em dúvida sobre quais doses faltam e quais pode tomar na gestação. | *(Pré-acesso ao sistema)* |
| **2. Entrada de dados** | Acessa a aplicação, informa seu perfil (idade e condição de gestante) e adiciona manualmente as vacinas já tomadas. | **Agente Multimodal** recebe os dados do perfil e do cartão de vacinas e estrutura o perfil da usuária. |
| **3. Triagem vacinal** | Aguarda a verificação automática das doses que estão atrasadas para seu perfil e condição. | **Sistema Multiagentes** cruza as doses informadas com o calendário oficial do Ministério da Saúde. |
| **4. Checagem de segurança** | Questiona se pode tomar todas as vacinas pendentes agora (ex.: febre amarela, dengue, dTpa). | **Motor RAG** busca indicações e contraindicações para gestantes nas bases da Anvisa e do Ministério da Saúde. |
| **5. Apoio à decisão** | Visualiza a recomendação clara de quais vacinas são indicadas ou contraindicadas com as evidências oficiais. | **Painel de Apoio à Decisão** apresenta resposta estruturada com trecho oficial e explicitação de limitações. |
| **6. Decisão e Feedback** | Avalia a resposta como *Útil* e vai ao posto de saúde com segurança. | **MLOps / Monitoramento** registra o feedback do usuário para monitoramento contínuo do sistema. |

### Jornada 2 — Pedro *(Sintomas Agudos e Automedicação)*

| Etapa | Passo da Jornada do Usuário | Ponto de Contato com a IA / Sistema |
| :--- | :--- | :--- |
| **1. Sintoma e Impulso** | Sente febre alta e dor no corpo; pega um comprimido de Ibuprofeno na gaveta para tentar trabalhar. | *(Pré-acesso ao sistema)* |
| **2. Consulta rápida** | Antes de engolir o comprimido, faz um relato textual descrevendo os sintomas/suspeita e informa o nome do remédio na aplicação. | **Agente Multimodal** coleta o relato textual e o nome do medicamento, estruturando os dados de entrada. |
| **3. Orquestração** | Pede para saber se pode tomar aquele remédio e o que deve fazer diante dos sintomas. | **Sistema Multiagentes** aciona o *Agente de Interação Medicamentosa* e o *Agente de Condutas em Doenças*. |
| **4. Busca em bulas e protocolos** | O sistema processa o cruzamento entre a suspeita clínica (ex.: dengue ou malária) e o medicamento pretendido. | **Motor RAG** consulta a bula oficial da Anvisa e o protocolo de manejo clínico do Ministério da Saúde. |
| **5. Alerta e orientação** | Visualiza um *Alerta de Risco Grave* desaconselhando o medicamento e uma lista de condutas seguras. | **Painel de Apoio à Decisão** exibe o alerta baseado em evidências oficiais com orientações compreensíveis. |
| **6. Ação segura e Feedback** | Guarda o remédio, inicia os cuidados recomendados, busca atendimento médico e avalia a resposta no app. | **MLOps / Monitoramento** registra o feedback em produção para acompanhar a qualidade e retroalimentar o pipeline. |

---

## 5. Brainstorming, Clusters de Funcionalidades e Cortes de Escopo *(Atividade 5)*

As ideias levantadas no brainstorming foram agrupadas em 5 clusters técnicos que definem exatamente o que entra no MVP e quais restrições garantem a viabilidade do cronograma até 07/12:

### Cluster 1: Entrada Unificada *(Perfil + Relato Textual)*

* **Escopo MVP:** Seleção de perfil (faixa etária e *flags* como gestante/comorbidades), checklist manual de vacinas tomadas, campo de texto livre para relato de sintomas/doença e nome do medicamento, além do agente estruturador que converte os dados (tabular + texto) em um JSON padronizado para os agentes.
* **Corte de Escopo:** Sem login/cadastro complexo, sem histórico salvo em conta, sem upload de foto (OCR) e sem entrada por áudio (ASR).

> **Alinhamento com a Semana 4 (Multimodalidade):** No MVP, a multimodalidade concentra-se na fusão de **entradas estruturadas/tabulares** (perfil clínico + checklist de doses vacinais) com **entradas não estruturadas em linguagem natural** (relato textual de sintomas e medicamentos) pelo Agente Estruturador. O [Contrato JSON](/arquitetura/contrato-json-e-metadados-rag.md) já prevê extensibilidade para incorporação futura de OCR e ASR sem quebra de interface.

### Cluster 2: Triagem e Orquestração Multiagentes

* **Escopo MVP:** Agente Orquestrador/Roteador que identifica se a dúvida é sobre vacinação ou sobre interação medicamento/doença; Agente de Imunização (checa atraso vacinal no calendário do MS e contraindicações); Agente de Medicamentos e Condutas (avalia remédio × doença e orienta atitudes seguras).
* **Corte de Escopo:** Limitar a cobertura inicial ao calendário adulto/gestante e a um recorte fechado de doenças-alvo (ex.: dengue, malária e gripe) para não atrasar a engenharia de dados.

### Cluster 3: Motor RAG Oficial *(Anvisa + Ministério da Saúde)*

* **Escopo MVP:** Base vetorial indexada com bulas selecionadas da Anvisa e protocolos clínicos/calendários do Ministério da Saúde; mecanismo de recuperação semântica focado em trechos de indicação, contraindicação e manejo clínico.
* **Corte de Escopo:** Pipeline *batch* simples de extração apenas dos documentos necessários para os casos de uso do MVP, sem *web scraping* em tempo real.

### Cluster 4: Painel de Apoio à Decisão e Evidências

* **Escopo MVP:** Card de resposta padronizado destacando o selo visual de risco (*Indicada*, *Contraindicada* ou *Alerta de Risco Grave*), lista de condutas seguras, exibição obrigatória da citação literal da fonte oficial (Anvisa/MS) e aviso fixo (*disclaimer*) de limitações médicas.
* **Corte de Escopo:** Interface web de página única em **Streamlit** integrada à API REST, focada exclusivamente na consulta e na visualização do resultado.

### Cluster 5: Coleta de Feedback e Monitoramento *(MLOps)*

* **Escopo MVP:** Botão simples de avaliação da resposta (*Útil* / *Inútil*) ao final da consulta, conectado ao registro de feedback, latência e parâmetros de execução para monitoramento e rastreabilidade.
* **Corte de Escopo:** Sem retreino automático complexo de pesos de LLM e sem reindexação autônoma; o gatilho de feedback aciona alerta operacional para revisão humana e reindexação controlada da base documental.

---

## 6. Canvas MVP Consolidado *(Atividade 9)* :id=canvas-mvp

### Proposta do MVP

Apoiar a tomada de decisão segura em saúde por meio de um sistema multiagentes com RAG, capaz de identificar vacinas faltantes, indicar condutas em doenças e alertar contraindicações de vacinas e medicamentos usando exclusivamente evidências oficiais da Anvisa e do Ministério da Saúde.

### Funcionalidades Essenciais do MVP

* **F1. Entrada Estruturada + Textual:** Formulário de perfil/vacinas em papel e campo de texto livre para sintomas e nome do medicamento processados pelo Agente Multimodal/Estruturador.
* **F2. Sistema Multiagentes:** Orquestrador conectando os agentes especialistas (*Triagem Vacinal / Imunização*, *Interação Medicamentosa* e *Condutas em Doenças*).
* **F3. Motor RAG Oficial:** Busca semântica indexada com bulas da Anvisa e calendário/protocolos clínicos do Ministério da Saúde.
* **F4. Painel de Apoio à Decisão:** Exibição clara de status (*Indicada* / *Contraindicada* / *Alerta de Risco Grave*), trecho literal da fonte oficial e aviso de limitações médicas.
* **F5. Feedback e Pipeline MLOps:** Botão de avaliação do usuário conectado ao monitoramento contínuo e ao versionamento de código, dados e modelos.

### Resultados Esperados

1. **Impacto no Usuário:** Empoderar o cidadão para compreender melhor riscos clínicos e evitar automedicação perigosa ou atraso vacinal.
2. **Validação Científica:** Comprovar com métricas objetivas que o uso de RAG + Multiagentes elimina alucinações sobre contraindicações em comparação a um LLM puro.
3. **Maturidade de Engenharia:** Operar um fluxo de MLOps reprodutível da ingestão de dados ao *serving* e monitoramento.

### Métricas para Validar as Hipóteses de Negócio

| Dimensão | Ferramenta | Métrica Objetiva | Critério de Sucesso |
| :--- | :--- | :--- | :--- |
| **Qualidade e Segurança** | MLflow Tracking | Fidelidade à fonte oficial (*groundedness*) e acurácia em casos críticos de contraindicação (benchmark LLM puro × RAG + Multiagentes). | **100% de acerto** nos casos críticos de contraindicação e 0 recomendações sem evidência oficial citada. |
| **Valor para o Usuário** | API + Prometheus / Grafana | Percentual de avaliações positivas (*"Útil"*) registradas na etapa 6 das jornadas da Mariana e do Pedro. | Predominância consistente de feedback *"Útil"* com rastreabilidade dos casos *"Inútil"*. |
| **Operação MLOps** | Prometheus / Grafana + MLflow Registry | Latência média/p95 da API REST, estabilidade do container Docker e auditabilidade das versões de pipeline/prompts. | Estabilidade operacional em container e **100% das versões** de prompts, pipelines e índices auditáveis no *Model Registry*. |

### Stack Tecnológica, Custo e Equipe

* **Custo:** R$ 0,00 (Stack 100% *Open Source*).
* **Stack Definida:** GitHub + GitHub Actions (CI/CD), Base Vetorial local (Motor RAG), MLflow Tracking & Model Registry (Experimentação e Governança), Docker + API REST local (FastAPI/Flask para *Serving*), Streamlit (Interface leve) e Prometheus + Grafana (Monitoramento). Detalhamento técnico e justificativas completas no [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md).
* **Equipe:** 5 integrantes cobrindo os 7 papéis obrigatórios de MLOps (`R1` a `R7`). Consulte a [Matriz de Papéis e Responsabilidades](/arquitetura/papeis-e-responsabilidades.md).

---

## 7. Horizonte de Evolução *(Funcionalidades Futuras Pós-MVP)* :id=horizonte-pos-mvp

Funcionalidades mapeadas durante a *Lean Inception* e deliberadamente postergadas para evoluções futuras após a entrega do MVP em 07/12:

1. **Leitura de Fotos (Visão Computacional / OCR):** Upload de foto do cartão físico de vacinação (Mariana) e da caixa ou bula do remédio (Pedro) para extração automática sem digitação.
2. **Relato por Voz (Transcrição de Áudio / ASR):** Envio de áudio pelo usuário descrevendo os sintomas para conversão automática em texto na entrada do Agente Multimodal.
3. **Ingestão Contínua em Larga Escala (Apache Airflow):** DAG automatizada no Airflow para varrer periodicamente novas notas técnicas do Ministério da Saúde e atualizações do bulário eletrônico da Anvisa.
4. **Geolocalização de UBS e Hospitais:** Indicação da unidade básica de saúde ou pronto-socorro mais próximo sempre que o sistema emitir um *Alerta de Risco Grave*.
5. **Carteira Vacinal Persistente e Alertas:** Criação de conta opcional de usuário (com termo de consentimento e controle rigoroso de dados sensíveis sob a LGPD) para salvar o histórico vacinal e disparar lembretes automáticos sobre próximas doses ou campanhas sazonais.
