# Riscos Clínicos, Viés, Limitações Éticas e Conformidade com a LGPD

Por atuar diretamente no domínio da **saúde do cidadão** — apoiando decisões sobre imunização em grupos vulneráveis (como gestantes) e prevenção de automedicação em doenças agudas (como dengue e malária) —, o **EvidencIA Saúde** enquadra-se como um sistema de **IA de alto impacto**.

Este documento atende diretamente às restrições do Challenge 2 (*"Explicitar riscos e limitações"* e *"Utilizar evidências confiáveis"*) e formaliza a matriz de riscos clínicos e operacionais, a análise de vieses, os limites éticos do MVP e o plano de conformidade com a **Lei Geral de Proteção de Dados Pessoais (LGPD — Lei nº 13.709/2018)**.

---

## 1. Matriz de Riscos Clínicos, Técnicos e Operacionais

A classificação de severidade combina **Probabilidade** (`Baixa`, `Média`, `Alta`) e **Impacto** (`Moderado`, `Alto`, `Crítico`), com prioridade absoluta à segurança do paciente (*Patient Safety First*).

| ID | Categoria | Descrição do Risco e Cenário Crítico | Prob. | Impacto | Severidade | Mitigação Preventiva (Design / Engenharia) | Mitigação Detetiva e Resposta (Operação) | Responsável |
| :-: | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :-: |
| **RSK-01** | **Clínico (Falso Negativo)** | O sistema falha em alertar uma contraindicação medicamentosa grave (ex.: não barrar Ibuprofeno ou AAS em suspeita de dengue — Jornada Pedro). | Média | Crítico | **Crítica** | Filtragem prioritária por `secao="contraindicacoes"` e `publico_alvo` no RAG; prompt conservador com precedência de risco; exigência de **100% de acerto** em casos críticos no benchmark MLflow antes de promover versão. | Testes de regressão clínica a cada mudança de prompt/índice; bloqueio automático de promoção no MLflow Registry se acurácia crítica < 100%. | `R3` / `R2` |
| **RSK-02** | **Clínico (Falso Negativo)** | Indicação indevida de vacina de vírus vivo atenuado (ex.: febre amarela ou dengue) para gestante ou imunossuprimido (Jornada Mariana). | Média | Crítico | **Crítica** | *Flag* explícita `gestante=true` e `comorbidades` no Contrato JSON; cruzamento obrigatório na seção `gravidez_e_lactacao` e `contraindicacoes` das bases do MS/Anvisa; regra de precedência global `CONTRAINDICADA`. | Conjunto de cenários de teste específicos para gestantes (diferentes semanas gestacionais) auditado no MLflow Tracking. | `R3` / `R4` |
| **RSK-03** | **IA Generativa (Alucinação)** | O LLM inventa dosagens, contraindicações inexistentes ou recomendações sem respaldo nos documentos oficiais. | Média | Crítico | **Crítica** | Arquitetura RAG restrita exclusivamente ao corpus Anvisa/MS; temperatura baixa; **regra de contrato *Zero Evidence, Zero Recommendation*** forçando `EVIDENCIA_INSUFICIENTE` quando não há trecho oficial recuperado acima do limiar. | Métrica de fidelidade (*groundedness*) registrada no MLflow; exibição obrigatória do `trecho_literal` no painel para conferência direta pelo usuário. | `R3` / `R5` |
| **RSK-04** | **Dados / RAG (Desatualização ou Chunking)** | Bula ou nota técnica da Anvisa/MS desatualizada no índice *batch*, ou quebra de *chunk* separando o nome do fármaco da frase de contraindicação. | Média | Alto | **Alta** | *Chunking* estruturado por seção documental com sobreposição controlada (`overlap`), curadoria manual de `R4` e registro obrigatório de `data_publicacao` e `versao_ingestao` nos metadados. | Exibição da fonte e edição oficial citada na interface; alertas operacionais no Grafana para revisões *batch* periódicas sob controle humano. | `R4` / `R7` |
| **RSK-05** | **Clínico / Uso (Atraso em Emergência)** | Cidadão com sinais de alarme graves (ex.: dengue hemorrágica, dispneia, desmaio) utiliza o aplicativo em vez de buscar pronto-socorro imediatamente. | Baixa | Crítico | **Alta** | Destaque visual imediato de `sinais_de_alarme` nas respostas clínicas e *disclaimer* médico fixo e proeminente orientando UPA, pronto-socorro ou **SAMU (192)** em emergências. | Monitoramento da frequência de `ALERTA_RISCO_GRAVE` no Grafana e revisão contínua da clareza textual dos alertas na UX. | `R1` / `R5` |
| **RSK-06** | **Escopo (Uso Fora do Domínio)** | Usuário consulta doenças raras, pediatria complexa ou medicamentos fora do recorte documental do MVP. | Alta | Alto | **Alta** | Agente Orquestrador classifica explicitamente `rota_definida="fora_de_escopo"` e aciona *fallback* seguro (`EVIDENCIA_INSUFICIENTE`) sem tentar responder com conhecimento paramétrico do LLM. | Monitoramento da taxa de `EVIDENCIA_INSUFICIENTE` no Prometheus/Grafana para identificar demandas prioritárias de expansão pós-MVP. | `R2` / `R3` |
| **RSK-07** | **Viés de Pré-treinamento** | O LLM base mistura diretrizes estrangeiras (FDA/CDC dos EUA) que divergem do Calendário Nacional do PNI (Brasil) ou de bulas da Anvisa. | Média | Alto | **Alta** | Prompt de sistema vincula explicitamente a resposta **apenas** aos trechos recuperados com `orgao_emissor` em `["ANVISA", "MINISTERIO_DA_SAUDE"]`; validação comparativa **LLM puro × RAG** no MLflow evidencia e elimina esse erro. | Auditoria qualitativa de citações e verificação automatizada de que toda evidência citada possui `orgao_emissor` oficial brasileiro. | `R3` / `R4` |
| **RSK-08** | **Privacidade / LGPD** | Usuário digita dados pessoais identificáveis (nome completo, CPF, telefone) no campo de relato textual livre ou comentário de feedback. | Média | Alto | **Alta** | Arquitetura *stateless* (relatos de consulta não são persistidos em banco de dados nem gravados em texto plano nos logs/Prometheus); aviso visual explícito na tela para não informar dados pessoais; sanitização/mascaramento de padrões (CPF/e-mail/telefone) em comentários de feedback. | Revisão de logs e métricas em CI/CD (`R6`/`R7`) garantindo ausência total de PII nas séries do Prometheus, dashboards Grafana e artefatos do MLflow. | `R2` / `R5` / `R7` |
| **RSK-09** | **MLOps (Envenenamento de Feedback)** | Usuários marcam *"Inútil"* por discordarem de uma contraindicação correta (ex.: queriam tomar o remédio) ou enviam ruído, tentando degradar o sistema. | Média | Moderado | **Média** | **Omissão deliberada de reindexação/retreinamento autônomo** (conforme [ADR-001](/arquitetura/adr-001-arquitetura-mlops-mvp.md)); feedback serve exclusivamente como indicador de observabilidade para triagem humana (*human-in-the-loop*). | Alertas no Grafana disparam investigação técnica pela equipe (`R3`/`R4`/`R7`), nunca alteração automática em produção. | `R7` / `R3` |
| **RSK-10** | **Operacional / Infraestrutura** | Latência elevada da API, falha de container ou indisponibilidade da Base Vetorial local / runtime do LLM. | Média | Moderado | **Média** | Containerização completa via Docker Compose, `GET /health` com verificação da Base Vetorial, *timeouts* explícitos e resposta controlada `503 SERVICO_INDISPONIVEL` sem gerar orientação incompleta. | Monitoramento em tempo real de latência (p50/p95), taxa de erros HTTP `5xx` e *uptime* no Prometheus + Grafana. | `R6` / `R7` / `R5` |

---

## 2. Análise e Mitigação de Vieses

Sistemas de IA em saúde estão sujeitos a vieses técnicos, documentais e comportamentais. O **EvidencIA Saúde** reconhece explicitamente quatro fontes principais de viés e adota contramedidas concretas:

### 2.1. Viés de Seleção e Cobertura Documental
* **Origem:** Por restrição de cronograma até 07/12, o corpus do MVP cobre o calendário vacinal adulto/gestante e um recorte fechado de doenças agudas (dengue, malária e gripe) e medicamentos associados. Populações pediátricas, idosos polimedicados complexos e doenças raras ficam sub-representados nesta versão.
* **Mitigação:** Declaração transparente do escopo na tela inicial e no *disclaimer*, somada à política *fail-safe* (`EVIDENCIA_INSUFICIENTE`) para qualquer tema fora da base curada, evitando respostas enviesadas ou improvisadas para grupos não cobertos.

### 2.2. Viés Linguístico e de Letramento em Saúde
* **Origem:** Bulas da Anvisa e protocolos clínicos do Ministério da Saúde empregam vocabulário técnico-científico (princípios ativos da Denominação Comum Brasileira — DCB, termos como *"anti-inflamatório não esteroidal"*, *"hipotensão postural"*), enquanto cidadãos utilizam linguagem coloquial ou nomes comerciais populares (ex.: *"Advil"*, *"Alivium"*, *"dor nas juntas"*, *"tontura ao levantar"*).
* **Mitigação:** O **Agente Estruturador/Multimodal** realiza normalização semântica (mapeando relatos coloquiais e marcas comuns para princípios ativos/sintomas padronizados antes da consulta RAG) e os agentes traduzem a resposta final em linguagem clara e acessível, preservando paralelamente o trecho literal oficial para auditabilidade.

### 2.3. Viés de Pré-treinamento Estrangeiro em LLMs
* **Origem:** Grandes Modelos de Linguagem (LLMs) pré-treinados contêm majoritariamente literatura médica norte-americana e europeia (diretrizes do CDC, FDA e EMA), que frequentemente divergem das normas do **Programa Nacional de Imunizações (PNI/MS)** e dos registros da **Anvisa** no Brasil (ex.: esquemas de vacinação contra febre amarela e dengue, ou disponibilidade de analgésicos como dipirona).
* **Mitigação:** Ancoragem estrita via RAG exclusivo em fontes brasileiras oficiais (`orgao_emissor` restrito a `ANVISA` e `MINISTERIO_DA_SAUDE`), comprovada empiricamente pelo benchmark **LLM puro × RAG + Multiagentes** no MLflow.

### 2.4. Viés de Automação (*Automation Bias*) e Confirmação
* **Origem:** Usuários tendem a confiar excessivamente em respostas bem formatadas geradas por IA ou a reformular perguntas até obter a validação desejada para se automedicar.
* **Mitigação:** Uso de selos visuais inequívocos (`ALERTA_RISCO_GRAVE`, `CONTRAINDICADA`), apresentação destacada da fonte literal da Anvisa/MS (deslocando a autoridade da "IA" para o órgão sanitário oficial) e reforço constante de que a decisão clínica definitiva pertence a um profissional de saúde.

---

## 3. Limitações Éticas e Princípios de IA Responsável

### 3.1. Limites Explícitos da Solução

Em consonância com a matriz *É / NÃO É / FAZ / NÃO FAZ* da *Lean Inception*, o **EvidencIA Saúde**:
1. **Não substitui consulta médica, farmacêutica ou de enfermagem**, nem atua como serviço de telemedicina ou triagem de pronto-socorro.
2. **Não emite diagnóstico médico fechado** nem prescreve medicamentos, doses individualizadas ou receitas controladas.
3. **Não realiza exame físico nem interpreta exames laboratoriais ou imagens** no MVP (OCR e ASR foram explicitamente cortados do escopo inicial).
4. **Não possui cobertura universal de doenças e fármacos** nesta versão: limita-se estritamente aos protocolos e bulas indexados na base oficial curada.
5. **Depende da veracidade e completude dos dados informados pelo cidadão** (ex.: esquecimento de alergias, comorbidades ou doses no cartão de vacina pode limitar a abrangência da verificação).

### 3.2. Princípios Éticos Operacionalizados

* **Não Maleficência (*Primum non nocere*):** diante de qualquer dúvida ou ausência de evidência oficial sólida, o sistema prefere recusar a recomendação (`EVIDENCIA_INSUFICIENTE`) a correr o risco de induzir uma conduta insegura.
* **Transparência Radical e Explicabilidade:** toda orientação exibe explicitamente o órgão emissor, o título do documento, a seção e o trecho literal que a sustenta, permitindo verificação independente pelo cidadão ou pelo profissional de saúde na UBS.
* **Supervisão Humana (*Human-in-the-Loop*):** curadoria documental, validação de casos críticos no MLflow e promoção de novas versões para produção dependem sempre de aprovação humana auditável.

### 3.3. *Disclaimer* Médico Obrigatório

O texto abaixo é exibido de forma fixa na interface **Streamlit** (antes da consulta e junto ao resultado) e injetado deterministicamente no campo `disclaimer_medico` do [Contrato JSON](/arquitetura/contrato-json-e-metadados-rag.md):

> *"Aviso importante: o EvidencIA Saúde é um sistema de apoio informativo baseado em documentos oficiais da Anvisa e do Ministério da Saúde. Ele não realiza diagnóstico médico, não prescreve medicamentos ou vacinas e não substitui avaliação por médico, farmacêutico ou unidade básica de saúde (UBS). Em caso de sintomas graves, sinais de alarme ou emergência, procure imediatamente uma UPA, pronto-socorro ou ligue para o SAMU (192)."*

---

## 4. Conformidade com a LGPD (Lei nº 13.709/2018)

### 4.1. Enquadramento Legal dos Dados

De acordo com o **Art. 5º, inciso II** da Lei nº 13.709/2018 (LGPD), informações referentes à **saúde** — como condição de gestação, comorbidades, sintomas relatados, histórico vacinal e medicamentos em uso — constituem **Dados Pessoais Sensíveis**, exigindo padrão elevado de proteção, minimização e fundamentação legal específica (Art. 11).

### 4.2. Estratégia Arquitetural: *Privacy by Design* e Operação *Stateless*

Para eliminar riscos desnecessários de exposição ou vazamento de dados sensíveis de saúde no MVP, o **EvidencIA Saúde** adota a privacidade desde a concepção (*Privacy by Design*) como requisito arquitetural rígido:

1. **Ausência de Cadastro e Identificação Direta:** o MVP não exige criação de conta, login, senha nem coleta nome, CPF, RG, e-mail, telefone, endereço ou número do Cartão Nacional de Saúde (CNS).
2. **Processamento Efêmero (*Stateless*):** os dados do perfil (`faixa_etaria`, `gestante`, `comorbidades`), o checklist vacinal e o relato textual trafegam apenas em memória durante o ciclo da requisição `POST /api/v1/consultar` e **não são persistidos em banco de dados** após o retorno da resposta.
3. **Anonimização Técnica na Observabilidade (Art. 12 da LGPD):**
   * O **Prometheus + Grafana** armazena exclusivamente contadores e histogramas agregados (latência, rota executada, classificação de risco, contagem de *"Útil"* / *"Inútil"*), sem qualquer texto do usuário ou atributo identificável.
   * O **MLflow Tracking** utiliza apenas conjuntos sintéticos de validação baseados nas personas fictícias (Mariana e Pedro) e cenários de teste — nunca consultas reais de cidadãos.
   * O endpoint `POST /api/v1/feedback` associa a avaliação a um `request_id` técnico aleatório e temporário (UUID v4), sem vinculação a identidade física, e aplica sanitização automática caso o usuário insira acidentalmente padrões de PII no comentário opcional.
4. **Transparência e Consentimento Informado na Interface (Art. 11, I):** antes do envio da consulta, o painel Streamlit exibe aviso conciso informando quais dados são utilizados exclusivamente em tempo de execução para gerar a resposta, que nenhum prontuário é salvo e orientando o cidadão a não digitar informações pessoais identificáveis no campo de texto livre.

### 4.3. Atendimento aos 10 Princípios da LGPD (Art. 6º)

| Princípio (Art. 6º) | Aplicação Concreta no EvidencIA Saúde |
| :--- | :--- |
| **I. Finalidade** | Dados informados na sessão são usados exclusivamente para executar a triagem vacinal e a verificação de contraindicações/condutas naquela consulta específica. |
| **II. Adequação** | Todos os campos do Contrato JSON (`gestante`, `semanas_gestacao`, `historico_vacinal`, `medicamento_consultado`, `relato_textual`) são estritamente compatíveis com a finalidade informada. |
| **III. Necessidade (Minimização)** | Coleta reduzida ao mínimo clínico indispensável; exclusão total de cadastro, login e identificadores civis (nome, CPF, e-mail). |
| **IV. Livre Acesso** | O usuário visualiza imediatamente na própria tela os dados preenchidos, a resposta gerada e os trechos oficiais utilizados, sem retenção oculta. |
| **V. Qualidade dos Dados** | Validação estrita de schema na API REST (ex.: coerência entre `gestante` e `semanas_gestacao`) e curadoria rigorosa das fontes oficiais (Anvisa/MS). |
| **VI. Transparência** | Avisos claros de privacidade, escopo limitado do MVP, *disclaimer* médico fixo e citação literal de cada evidência utilizada. |
| **VII. Segurança** | Isolamento de serviços via Docker, proibição de logging de payloads clínicos em produção, sanitização de comentários de feedback e ausência de armazenamento persistente de prontuários. |
| **VIII. Prevenção** | Política *fail-safe* contra alucinação, testes críticos de contraindicação no MLflow e bloqueio de reindexação autônoma não auditada. |
| **IX. Não Discriminação** | Respostas padronizadas por evidências públicas universais do SUS/Ministério da Saúde e da Anvisa, com mitigação de barreiras de letramento em saúde. |
| **X. Responsabilização e Prestação de Contas** | Documentação completa de arquitetura (ADR-001), papéis (`R1`–`R7`), rastreabilidade de versões no MLflow Registry e registro formal desta matriz de riscos e LGPD. |

### 4.4. Requisitos Adicionais para Evoluções Pós-MVP

Caso funcionalidades mapeadas no [Horizonte de Evolução Pós-MVP](/concepcao/lean-inception.md?id=horizonte-pos-mvp) sejam implementadas em fases futuras — especificamente **Carteira Vacinal Persistente (com conta de usuário)**, **Upload de Fotos de Cartão de Vacina (OCR)** ou **Relato por Áudio (ASR)** —, o sistema passará a persistir e processar dados pessoais sensíveis identificáveis (incluindo eventual dado biométrico de voz e imagens contendo nome/CPF). Antes de entrar em produção, essas evoluções exigirão obrigatoriamente:

1. Elaboração de **Relatório de Impacto à Proteção de Dados Pessoais (RIPD)**;
2. Coleta e gestão auditável de **consentimento específico e destacado** do titular (Art. 11, I);
3. Criptografia em trânsito (TLS) e em repouso, controle rigoroso de acesso e descarte imediato de imagens/áudios brutos após extração textual;
4. Implementação de fluxo de atendimento aos **Direitos do Titular (Art. 18 da LGPD)**, incluindo acesso, correção, portabilidade e eliminação definitiva da conta e do histórico.
