# Contrato JSON de Agentes/API e Esquema de Metadados do RAG

Este documento especifica formalmente o **esquema de metadados obrigatórios da base vetorial (RAG)** e os **contratos JSON de entrada, comunicação interna entre agentes, saída da API REST e coleta de feedback** do projeto **EvidencIA Saúde**.

O objetivo é padronizar a fronteira entre dados, inteligência (RAG + multiagentes), backend, interface e observabilidade, destravando o desenvolvimento paralelo das issues listadas na Seção 1.

---

## 1. Mapeamento de Destravamento de Issues

| Issue | Frente de Trabalho | Papel Principal | Seções deste Documento que a Destravam |
| :-: | :--- | :---: | :--- |
| **`#11`** / **`#14`** | Ingestão documental (Anvisa/MS), *chunking*, indexação e motor de recuperação com filtro por metadados | `R4` (Eng. de Dados) + `R3` | [Seção 2 — Esquema de Metadados Obrigatórios do RAG](#metadados-rag) |
| **`#12`** | Interface unificada de consulta (Streamlit) | `R5` (Eng. de Software) | [Seções 3 e 5](#contrato-entrada) |
| **`#13`** | Agente Estruturador e Roteador | `R3` (Cientista de Dados) + `R2` | [Seções 3 e 4.1](#contrato-entrada) |
| **`#15`** / **`#16`** | Agentes especialistas de Triagem Vacinal e de Medicamentos e Condutas | `R3` (Cientista de Dados) + `R2` | [Seções 2, 4.2 e 5](#contrato-saida) |
| **`#19`** / **`#21`** / **`#22`** | *Guardrails*, API REST em Docker, feedback e telemetria | `R5` (Eng. de Software) + `R6`/`R7` | [Seções 3, 5, 6 e 7](#contrato-saida) |
| **`#24`** | Golden dataset de casos críticos e especificação de prompts e schemas dos agentes | `R3` (Cientista de Dados) | [Seções 3, 4 e 5](#contrato-saida) — ver também [Prompts e Schemas](/agentes/prompts-e-schemas.md) e [Golden Dataset](/avaliacao/golden-dataset.md) |

---

## 2. Esquema de Metadados Obrigatórios do RAG *(Issue `#11`)* :id=metadados-rag

Para garantir filtragem semântica precisa (ex.: isolar contraindicações para gestantes) e rastreabilidade literal das fontes oficiais, **todo *chunk* indexado na Base Vetorial local deve conter obrigatoriamente os 5 campos abaixo**:

### 2.1. Campos Obrigatórios

| Campo | Tipo Lógico | Obrigatório | Valores Permitidos / Formato | Finalidade no Motor RAG |
| :--- | :--- | :---: | :--- | :--- |
| `orgao_emissor` | `string` (enum) | **Sim** | `"ANVISA"`, `"MINISTERIO_DA_SAUDE"` | Identificar a autoridade sanitária oficial emissora da evidência. |
| `titulo_documento` | `string` | **Sim** | Título oficial completo e normalizado (ex.: `"Bula Paciente - Ibuprofeno 400mg"`, `"Dengue: Diagnóstico e Manejo Clínico - Adulto e Criança (6ª ed.)"`) | Exibir referência bibliográfica clara ao cidadão no Painel de Apoio à Decisão. |
| `categoria` | `string` (enum) | **Sim** | `"bula_medicamento"`, `"bula_vacina"`, `"calendario_vacinal"`, `"protocolo_clinico"`, `"nota_tecnica"` | Direcionar consultas dos agentes especialistas para o tipo correto de documento. |
| `secao` | `string` (enum) | **Sim** | `"indicacoes"`, `"contraindicacoes"`, `"advertencias_e_precaucoes"`, `"gravidez_e_lactacao"`, `"interacoes_medicamentosas"`, `"esquema_vacinal"`, `"manejo_clinico"`, `"sinais_de_alarme"`, `"condutas_gerais"` | Priorizar trechos críticos de segurança (ex.: filtrar diretamente `contraindicacoes` ou `gravidez_e_lactacao`). |
| `publico_alvo` | `string` / `array<string>` *(ver nota abaixo)* | **Sim** | Vocabulário controlado: `"geral"`, `"adulto"`, `"gestante"`, `"lactante"`, `"idoso"`, `"imunossuprimido"`, `"pacientes_com_dengue"`, `"pacientes_com_malaria"`, `"pacientes_com_gripe"` | Filtrar orientações específicas ao perfil clínico da pessoa consultante (ex.: gestante de 20 semanas ou suspeita de dengue). |

> **Nota Técnica de Implementação (`#11` — Compatibilidade com Base Vetorial Local):**  
> Alguns motores vetoriais locais (como **ChromaDB**) aceitam apenas tipos escalares primitivos (`str`, `int`, `float`, `bool`) nos metadados de cada *chunk*, enquanto outros (como **Qdrant local**) aceitam nativamente listas de strings.  
> **Convenção adotada:**
> * No **JSON de saída da API REST** e nos **contratos internos em Python**, `publico_alvo` é **sempre** serializado como `array<string>` (ex.: `["adulto", "gestante"]`).
> * Caso a base vetorial escolhida em `#11` exija tipos escalares, armazenar `publico_alvo` como string canônica delimitada por pipe com delimitadores nas extremidades (ex.: `"|adulto|gestante|"`) ou campos booleanos auxiliares (`alvo_gestante: true`) e reconverter para `array<string>` na camada de recuperação antes de devolver ao agente.

### 2.2. Campos Complementares Recomendados *(Rastreabilidade MLOps)*

Além dos 5 metadados obrigatórios, recomenda-se anexar os seguintes campos técnicos durante a ingestão *batch*:

| Campo | Tipo | Obrigatório no MVP | Descrição |
| :--- | :--- | :---: | :--- |
| `chunk_id` | `string` | Recomendado (chave única) | Identificador determinístico do trecho (ex.: `ms-dengue-6ed-p42-c03`). |
| `entidade_principal` | `string` | Recomendado | Princípio ativo (DCB), vacina ou doença principal do trecho em minúsculas (ex.: `"ibuprofeno"`, `"febre_amarela"`, `"dtpa"`, `"dengue"`). |
| `data_publicacao` | `string` (`YYYY-MM` ou `YYYY`) | Recomendado | Ano/mês da edição oficial ou publicação da bula/nota técnica. |
| `versao_ingestao` | `string` | Recomendado | Tag semântica da carga *batch* versionada no MLflow (ex.: `"corpus-v1.0.0"`). |
| `pagina_origem` | `integer` ou `null` | Opcional | Número da página no PDF oficial de origem para auditoria. |
| `url_referencia` | `string` ou `null` | Opcional | Link oficial do portal da Anvisa ou Ministério da Saúde. |

### 2.3. Exemplos de *Chunks* Indexados na Base Vetorial

**Exemplo 1 — Protocolo Clínico de Dengue (Ministério da Saúde) — Cenário Pedro:**

```json
{
  "chunk_id": "ms-dengue-6ed-manejo-aines-01",
  "texto": "Os anti-inflamatórios não esteroidais (AINEs), como ibuprofeno, diclofenaco e nimesulida, bem como os salicilatos (ácido acetilsalicílico), são contraindicados em pacientes com suspeita ou confirmação de dengue devido ao risco aumentado de hemorragias e agravamento clínico.",
  "metadados": {
    "orgao_emissor": "MINISTERIO_DA_SAUDE",
    "titulo_documento": "Dengue: Diagnóstico e Manejo Clínico - Adulto e Criança (6ª edição)",
    "categoria": "protocolo_clinico",
    "secao": "contraindicacoes",
    "publico_alvo": ["geral", "pacientes_com_dengue"],
    "entidade_principal": "ibuprofeno",
    "data_publicacao": "2024-02",
    "versao_ingestao": "corpus-v1.0.0",
    "pagina_origem": 31
  }
}
```

**Exemplo 2 — Calendário Nacional de Vacinação (Ministério da Saúde) — Cenário Mariana:**

```json
{
  "chunk_id": "ms-calendario-gestante-dtpa-01",
  "texto": "A vacina dTpa (difteria, tétano e coqueluche acelular) é recomendada para todas as gestantes a partir da 20ª semana de gestação, a cada gravidez, visando proteção materna e transferência de anticorpos ao recém-nascido.",
  "metadados": {
    "orgao_emissor": "MINISTERIO_DA_SAUDE",
    "titulo_documento": "Calendário Nacional de Vacinação - Gestante (PNI)",
    "categoria": "calendario_vacinal",
    "secao": "indicacoes",
    "publico_alvo": ["adulto", "gestante"],
    "entidade_principal": "dtpa",
    "data_publicacao": "2024-01",
    "versao_ingestao": "corpus-v1.0.0",
    "pagina_origem": 2
  }
}
```

### 2.4. Regra de Validação na Ingestão *(Quality Gate)*

O script de ingestão (`#11`) e o workflow de CI no GitHub Actions devem rejeitar automaticamente qualquer *chunk* em que:
1. Qualquer um dos 5 campos obrigatórios (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`) esteja ausente, nulo ou vazio;
2. `orgao_emissor`, `categoria`, `secao` ou os itens de `publico_alvo` contenham valores fora do vocabulário controlado definido na Seção 2.1;
3. O campo `texto` tenha menos de 30 caracteres úteis.

---

## 3. Contrato JSON de Entrada (`POST /api/v1/consultar`) :id=contrato-entrada

Este é o payload enviado pela interface **Streamlit** (`#12`) à **API REST** (`#21`), recebido pelo **Agente Estruturador/Roteador** (`#13`). Schema Pydantic correspondente: `EntradaConsulta` em `src/agents/schemas.py`.

> **Regra de Privacidade (LGPD):** O contrato **não aceita e não define** campos de identificação pessoal (nome, CPF, e-mail, telefone, endereço ou cartão SUS). O `request_id` é um UUID efêmero gerado apenas para correlação técnica e vinculação anônima de feedback.

### 3.1. Especificação dos Campos de Entrada

| Caminho do Campo | Tipo | Obrigatório | Validações / Valores Permitidos | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `request_id` | `string` (UUID v4) | Opcional | Se omitido, gerado pela API REST | Identificador técnico efêmero da consulta (sem PII). |
| `origem_entrada` | `string` (enum) | Opcional | Padrão: `"formulario_texto"` *(extensível pós-MVP para `"ocr_imagem"`, `"asr_audio"`)* | Identifica a modalidade da entrada para evolução multimodal futura. |
| `perfil_usuario` | `object` | **Sim** | Objeto não nulo | Dados clínicos mínimos necessários para triagem segura. |
| `perfil_usuario.faixa_etaria` | `string` (enum) | **Sim** | `"adulto"`, `"idoso"`, `"adolescente"`, `"crianca"` *(MVP prioriza adulto/gestante)* | Faixa etária para cruzamento no calendário do MS e bulas. |
| `perfil_usuario.idade_anos` | `integer` ou `null` | Opcional | `0` a `120` | Idade exata quando informada pelo usuário. |
| `perfil_usuario.gestante` | `boolean` | **Sim** | `true` ou `false` (padrão `false`) | *Flag* crítica de segurança para vacinas e medicamentos. |
| `perfil_usuario.semanas_gestacao` | `integer` ou `null` | Opcional | `1` a `42` (válido apenas se `gestante = true`) | Permite verificar janelas gestacionais (ex.: dTpa ≥ 20 semanas). |
| `perfil_usuario.lactante` | `boolean` | Opcional | Padrão `false` | Indica amamentação ativa. |
| `perfil_usuario.comorbidades` | `array<string>` | Opcional | Padrão `[]` (ex.: `["hipertensao", "diabetes", "imunossuprimido", "doenca_hepatica", "doenca_renal"]`) | Condições crônicas relevantes para contraindicações. |
| `perfil_usuario.alergias_conhecidas` | `array<string>` | Opcional | Padrão `[]` (ex.: `["aines", "ovo", "dipirona"]`) | Alergias conhecidas declaradas pelo cidadão. |
| `historico_vacinal` | `array<object>` | Opcional | Padrão `[]` | Checklist manual das vacinas já tomadas (Jornada Mariana). |
| `historico_vacinal[].vacina` | `string` | Sim *(se item presente)* | Nome padronizado da vacina (ex.: `"hepatite_b"`, `"dupla_adulto_dt"`, `"triplice_viral"`, `"febre_amarela"`, `"dtpa"`, `"influenza"`, `"dengue"`) | Identificação da vacina no checklist. |
| `historico_vacinal[].doses_tomadas` | `integer` | Sim *(se item presente)* | `>= 0` | Quantidade de doses registradas no cartão físico. |
| `historico_vacinal[].ano_ultima_dose` | `integer` ou `null` | Opcional | `1950` a `2026` | Ano aproximado da última dose (útil para reforços decenais como dT). |
| `consulta` | `object` | **Sim** | Objeto não nulo | Relato livre e entidades explícitas da dúvida atual. |
| `consulta.relato_textual` | `string` | **Sim** | Mínimo 5, máximo 2000 caracteres | Texto livre com sintomas, suspeita de doença ou dúvida sobre vacinas/remédios. |
| `consulta.medicamento_consultado` | `string` ou `null` | Opcional | Máximo 120 caracteres | Nome do medicamento pretendido (ex.: `"Ibuprofeno"`). |
| `consulta.vacina_consultada` | `string` ou `null` | Opcional | Máximo 120 caracteres | Vacina específica sobre a qual o usuário tem dúvida. |
| `consulta.suspeita_doenca` | `string` ou `null` | Opcional | Ex.: `"dengue"`, `"malaria"`, `"gripe"` ou `null` | Doença suspeita informada explicitamente, se houver. |

### 3.2. Exemplos de Payloads de Entrada

**Exemplo A — Jornada da Mariana *(Triagem Vacinal e Gestação)*:**

```json
{
  "request_id": "9f3b1c2e-7b4d-4d62-a2c9-5a8b6f1e4c11",
  "origem_entrada": "formulario_texto",
  "perfil_usuario": {
    "faixa_etaria": "adulto",
    "idade_anos": 32,
    "gestante": true,
    "semanas_gestacao": 20,
    "lactante": false,
    "comorbidades": [],
    "alergias_conhecidas": []
  },
  "historico_vacinal": [
    { "vacina": "hepatite_b", "doses_tomadas": 3, "ano_ultima_dose": 2012 },
    { "vacina": "dupla_adulto_dt", "doses_tomadas": 1, "ano_ultima_dose": 2014 }
  ],
  "consulta": {
    "relato_textual": "Estou grávida de 20 semanas e não lembro dos reforços da vida adulta. Quais vacinas faltam para mim e posso tomar febre amarela, dengue e dTpa agora?",
    "medicamento_consultado": null,
    "vacina_consultada": "febre_amarela, dengue, dtpa",
    "suspeita_doenca": null
  }
}
```

**Exemplo B — Jornada do Pedro *(Sintomas Agudos e Automedicação)*:**

```json
{
  "request_id": "2c8a4f90-1e33-4a9b-8f12-0d7c3e9a5b44",
  "origem_entrada": "formulario_texto",
  "perfil_usuario": {
    "faixa_etaria": "adulto",
    "idade_anos": 26,
    "gestante": false,
    "semanas_gestacao": null,
    "lactante": false,
    "comorbidades": [],
    "alergias_conhecidas": []
  },
  "historico_vacinal": [],
  "consulta": {
    "relato_textual": "Estou com febre alta e muita dor no corpo desde ontem, suspeito que seja dengue. Posso tomar um comprimido de Ibuprofeno para conseguir trabalhar e o que devo fazer?",
    "medicamento_consultado": "Ibuprofeno",
    "vacina_consultada": null,
    "suspeita_doenca": "dengue"
  }
}
```

---

## 4. Contrato Interno de Orquestração Multiagentes *(Issues `#13`, `#15` e `#16`)*

O sistema tem **3 agentes**, definidos no Cluster 2 da *Lean Inception* e nas issues do Épico 4:

| ID do agente | Issue | Papel |
| :--- | :-: | :--- |
| `agente_estruturador_roteador` | `#13` | Normaliza a entrada (tabular + texto), verifica o escopo e define rota e filtros do RAG. |
| `agente_triagem_vacinal` | `#15` | Triagem vacinal e segurança na gestação. |
| `agente_medicamentos_condutas` | `#16` | Medicamento × doença × perfil, condutas seguras e sinais de alarme. |

Para manter baixo acoplamento, o fluxo interno segue dois envelopes padronizados. Os schemas Pydantic e os prompts de cada agente estão em [Especificação dos Agentes: Prompts e Schemas](/agentes/prompts-e-schemas.md).

### 4.1. Saída do Agente Estruturador/Roteador *(Roteamento)*

O **Agente Estruturador/Roteador** normaliza os dados tabulares + relato textual e define a rota e os filtros de metadados para o RAG (schema `SaidaEstruturadorRoteador`):

```json
{
  "request_id": "2c8a4f90-1e33-4a9b-8f12-0d7c3e9a5b44",
  "rota_definida": "hibrida",
  "agentes_alvo": ["agente_medicamentos_condutas"],
  "entidades_normalizadas": {
    "medicamentos_dcb": ["ibuprofeno"],
    "vacinas": [],
    "doencas_suspeitas": ["dengue"],
    "sintomas": ["febre alta", "dor no corpo"]
  },
  "filtros_rag_recomendados": {
    "categorias": ["bula_medicamento", "protocolo_clinico"],
    "secoes_prioritarias": ["contraindicacoes", "manejo_clinico", "sinais_de_alarme"],
    "publico_alvo": ["geral", "adulto", "pacientes_com_dengue"]
  },
  "dentro_do_escopo_mvp": true,
  "entrada_suficiente": true,
  "motivo_insuficiencia": null
}
```

**Valores válidos para `rota_definida`:**
* `"triagem_vacinal"` → aciona `agente_triagem_vacinal`
* `"interacao_medicamentosa"` → aciona `agente_medicamentos_condutas`
* `"condutas_doenca"` → aciona `agente_medicamentos_condutas`
* `"hibrida"` → aciona um ou ambos os especialistas (ex.: medicamento + conduta na mesma consulta, ou vacina + medicamento)
* `"fora_de_escopo"` → não aciona especialistas; resposta segura explicando o recorte atual do MVP e orientando atendimento médico/UBS

Quando o relato é incompreensível ou não traz dúvida identificável, o agente devolve `entrada_suficiente: false`, explica em `motivo_insuficiencia` e usa a rota `fora_de_escopo`.

### 4.2. Envelope de Retorno de Cada Agente Especialista

Cada agente especialista devolve ao consolidador um objeto com o mesmo formato estrutural (schemas `SaidaTriagemVacinal` e `SaidaMedicamentosCondutas`):

```json
{
  "agente_origem": "agente_medicamentos_condutas",
  "classificacao_parcial": "ALERTA_RISCO_GRAVE",
  "achados_estruturados": {
    "medicamento_avaliado": "Ibuprofeno",
    "doenca_ou_condicao_contexto": "Suspeita de dengue",
    "status_uso": "CONTRAINDICADO",
    "condutas_seguras": [
      "Não utilizar anti-inflamatórios não esteroidais nem ácido acetilsalicílico.",
      "Iniciar hidratação oral e procurar avaliação em unidade de saúde."
    ],
    "sinais_de_alarme": ["Dor abdominal intensa e contínua", "Vômitos persistentes"],
    "evidencia_ids": ["EV-01"],
    "resumo_agente": "Ibuprofeno é um anti-inflamatório não esteroidal (AINE) contraindicado em suspeita de dengue devido ao risco aumentado de hemorragias."
  },
  "evidencias_recuperadas": [
    {
      "evidencia_id": "EV-01",
      "chunk_id": "ms-dengue-6ed-manejo-aines-01",
      "orgao_emissor": "MINISTERIO_DA_SAUDE",
      "titulo_documento": "Dengue: Diagnóstico e Manejo Clínico - Adulto e Criança (6ª edição)",
      "categoria": "protocolo_clinico",
      "secao": "contraindicacoes",
      "publico_alvo": ["geral", "pacientes_com_dengue"],
      "trecho_literal": "Os anti-inflamatórios não esteroidais (AINEs), como ibuprofeno, diclofenaco e nimesulida, bem como os salicilatos (ácido acetilsalicílico), são contraindicados em pacientes com suspeita ou confirmação de dengue devido ao risco aumentado de hemorragias e agravamento clínico.",
      "score_similaridade": 0.93
    }
  ]
}
```

---

## 5. Contrato JSON de Saída (`200 OK` — Issues `#19` e `#21`) :id=contrato-saida

Este é o payload consolidado devolvido pela API REST ao Painel **Streamlit**.

### 5.1. Especificação dos Campos de Saída

| Caminho do Campo | Tipo | Obrigatório | Valores Permitidos / Regras | Descrição |
| :--- | :--- | :---: | :--- | :--- |
| `request_id` | `string` (UUID v4) | **Sim** | Mesmo UUID da entrada | Permite correlacionar a etapa de feedback posterior (`POST /api/v1/feedback`). |
| `timestamp_resposta` | `string` (ISO 8601 UTC) | **Sim** | Ex.: `"2026-11-19T20:30:00Z"` | Data e hora da geração da resposta. |
| `rota_acionada` | `string` (enum) | **Sim** | `"triagem_vacinal"`, `"interacao_medicamentosa"`, `"condutas_doenca"`, `"hibrida"`, `"fora_de_escopo"`, `"evidencia_insuficiente"` | Rota efetivamente executada pelo Orquestrador. |
| `agentes_executados` | `array<string>` | **Sim** | Ex.: `["agente_estruturador_roteador", "agente_triagem_vacinal"]` | Rastreabilidade dos agentes participantes da resposta. |
| `classificacao_risco` | `string` (enum) | **Sim** | `"INDICADA"`, `"CONTRAINDICADA"`, `"ALERTA_RISCO_GRAVE"`, `"ORIENTACAO_GERAL"`, `"EVIDENCIA_INSUFICIENTE"` | Selo visual principal exibido em destaque no card do Streamlit. |
| `resumo_decisao` | `string` | **Sim** | Texto claro e acessível ao cidadão | Síntese direta da orientação fundamentada nas evidências. |
| `detalhamento_vacinal` | `object` ou `null` | Condicional | Preenchido nas rotas `triagem_vacinal` ou `hibrida` | Detalha vacinas em dia e lista de vacinas pendentes com status individual (`INDICADA`, `CONTRAINDICADA`, `AVALIAR_COM_MEDICO`) e `evidencia_ids`. |
| `detalhamento_clinico_medicamentoso` | `object` ou `null` | Condicional | Preenchido nas rotas `interacao_medicamentosa`, `condutas_doenca` ou `hibrida` | Detalha `medicamento_avaliado`, `doenca_ou_condicao_contexto`, `status_uso`, `condutas_seguras` e `sinais_de_alarme`. |
| `evidencias_oficiais` | `array<object>` | **Sim** | Mínimo 1 item quando `classificacao_risco != "EVIDENCIA_INSUFICIENTE"` | Lista de citações literais recuperadas pelo RAG com os **5 metadados obrigatórios** (`orgao_emissor`, `titulo_documento`, `categoria`, `secao`, `publico_alvo`), `evidencia_id`, `chunk_id`, `trecho_literal` e `score_similaridade`. |
| `disclaimer_medico` | `string` | **Sim** | Texto fixo não vazio | Aviso legal e ético obrigatório informando limitações médicas. |
| `metadados_execucao` | `object` | **Sim** | `versao_pipeline`, `versao_prompt`, `versao_indice_rag`, `modelo_llm`, `latencia_ms` | Rastreabilidade MLOps conectada ao MLflow Registry e Prometheus. |

### 5.2. Invariantes de Segurança (*Guardrails* Obrigatórios)

A camada de validação da API REST (`#19`/`#21`) e dos agentes (`#13`, `#15` e `#16`) deve impor três invariantes inegociáveis antes de serializar qualquer resposta `200 OK`:

1. **Regra Anti-Alucinação (*Zero Evidence, Zero Recommendation*):** se `evidencias_oficiais` estiver vazio ou nenhum trecho atingir o limiar mínimo de similaridade definido no MLflow, a API **bloqueia** qualquer recomendação gerada pelo LLM, força `classificacao_risco = "EVIDENCIA_INSUFICIENTE"` e `rota_acionada = "evidencia_insuficiente"`, retornando mensagem padronizada de encaminhamento a profissional de saúde.
2. **Precedência Máxima de Severidade:** quando múltiplos agentes retornam achados distintos em uma mesma consulta (ex.: uma vacina indicada e outra contraindicada na gestação), o campo global `classificacao_risco` deve refletir sempre a maior severidade observada, segundo a ordem:  
   `ALERTA_RISCO_GRAVE` > `CONTRAINDICADA` > `ORIENTACAO_GERAL` > `INDICADA`.
3. **Obrigatoriedade de *Disclaimer*:** `disclaimer_medico` é injetado de forma determinística pelo backend (nunca delegado exclusivamente à geração livre do LLM).

### 5.3. Exemplos de Payloads de Saída

**Saída A — Resposta para Mariana *(Triagem Vacinal na Gestação)*:**

```json
{
  "request_id": "9f3b1c2e-7b4d-4d62-a2c9-5a8b6f1e4c11",
  "timestamp_resposta": "2026-11-19T20:32:10Z",
  "rota_acionada": "triagem_vacinal",
  "agentes_executados": [
    "agente_estruturador_roteador",
    "agente_triagem_vacinal"
  ],
  "classificacao_risco": "CONTRAINDICADA",
  "resumo_decisao": "Para gestantes com 20 semanas, a vacina dTpa é INDICADA a cada gestação. Contudo, vacinas de vírus vivo atenuado consultadas (como a vacina da dengue) são CONTRAINDICADAS na gestação, e a vacina da febre amarela é geralmente contraindicada, exigindo avaliação médica individualizada apenas em cenários de alto risco epidemiológico.",
  "detalhamento_vacinal": {
    "vacinas_em_dia": ["hepatite_b"],
    "vacinas_pendentes": [
      {
        "vacina": "dTpa",
        "status": "INDICADA",
        "justificativa": "Recomendada para todas as gestantes a partir da 20ª semana de gestação.",
        "evidencia_ids": ["EV-01"]
      },
      {
        "vacina": "Dengue",
        "status": "CONTRAINDICADA",
        "justificativa": "Vacina de vírus vivo atenuado contraindicada para gestantes segundo diretrizes oficiais.",
        "evidencia_ids": ["EV-02"]
      },
      {
        "vacina": "Febre Amarela",
        "status": "CONTRAINDICADA",
        "justificativa": "Contraindicada em gestantes como regra geral; aplicação apenas sob avaliação médica rigorosa em surtos de alto risco.",
        "evidencia_ids": ["EV-03"]
      }
    ]
  },
  "detalhamento_clinico_medicamentoso": null,
  "evidencias_oficiais": [
    {
      "evidencia_id": "EV-01",
      "chunk_id": "ms-calendario-gestante-dtpa-01",
      "orgao_emissor": "MINISTERIO_DA_SAUDE",
      "titulo_documento": "Calendário Nacional de Vacinação - Gestante (PNI)",
      "categoria": "calendario_vacinal",
      "secao": "indicacoes",
      "publico_alvo": ["adulto", "gestante"],
      "trecho_literal": "A vacina dTpa (difteria, tétano e coqueluche acelular) é recomendada para todas as gestantes a partir da 20ª semana de gestação, a cada gravidez, visando proteção materna e transferência de anticorpos ao recém-nascido.",
      "score_similaridade": 0.94
    },
    {
      "evidencia_id": "EV-02",
      "chunk_id": "anvisa-bula-vacina-dengue-gest-01",
      "orgao_emissor": "ANVISA",
      "titulo_documento": "Bula Profissional/Paciente - Vacina Dengue (atenuada)",
      "categoria": "bula_vacina",
      "secao": "gravidez_e_lactacao",
      "publico_alvo": ["gestante"],
      "trecho_literal": "Esta vacina é contraindicada em mulheres grávidas e lactantes por se tratar de vacina contendo vírus vivos atenuados.",
      "score_similaridade": 0.91
    },
    {
      "evidencia_id": "EV-03",
      "chunk_id": "ms-nota-febre-amarela-gest-02",
      "orgao_emissor": "MINISTERIO_DA_SAUDE",
      "titulo_documento": "Manual de Normas e Procedimentos para Vacinação - Febre Amarela",
      "categoria": "nota_tecnica",
      "secao": "contraindicacoes",
      "publico_alvo": ["gestante"],
      "trecho_literal": "A vacinação contra febre amarela é contraindicada para gestantes, salvo situações de elevado risco epidemiológico mediante avaliação médica criteriosa de risco-benefício.",
      "score_similaridade": 0.89
    }
  ],
  "disclaimer_medico": "Aviso importante: o EvidencIA Saúde é um assistente informativo baseado em documentos oficiais da Anvisa e do Ministério da Saúde. Ele não realiza diagnóstico médico, não substitui consulta pré-natal ou avaliação em unidade de saúde (UBS) e não prescreve medicamentos ou vacinas.",
  "metadados_execucao": {
    "versao_pipeline": "v1.0.0",
    "versao_prompt": "prompts-v1.2",
    "versao_indice_rag": "corpus-v1.0.0",
    "modelo_llm": "llm-config-mvp",
    "latencia_ms": 1420
  }
}
```

**Saída B — Resposta para Pedro *(Alerta de Risco Grave — Ibuprofeno + Suspeita de Dengue)*:**

```json
{
  "request_id": "2c8a4f90-1e33-4a9b-8f12-0d7c3e9a5b44",
  "timestamp_resposta": "2026-11-19T20:35:04Z",
  "rota_acionada": "hibrida",
  "agentes_executados": [
    "agente_estruturador_roteador",
    "agente_medicamentos_condutas"
  ],
  "classificacao_risco": "ALERTA_RISCO_GRAVE",
  "resumo_decisao": "ALERTA DE RISCO GRAVE: Não tome Ibuprofeno diante de suspeita de dengue. Anti-inflamatórios não esteroidais (AINEs) são contraindicados na dengue por aumentarem o risco de hemorragias e agravamento clínico. Priorize hidratação oral vigorosa, repouso e avaliação médica em unidade de saúde.",
  "detalhamento_vacinal": null,
  "detalhamento_clinico_medicamentoso": {
    "medicamento_avaliado": "Ibuprofeno",
    "doenca_ou_condicao_contexto": "Suspeita de dengue",
    "status_uso": "CONTRAINDICADO",
    "condutas_seguras": [
      "Não utilizar anti-inflamatórios não esteroidais (ex.: ibuprofeno, diclofenaco) nem ácido acetilsalicílico.",
      "Iniciar hidratação oral imediata e frequente (água, soro de reidratação oral e líquidos).",
      "Manter repouso e procurar avaliação médica em unidade de saúde para estadiamento clínico adequado."
    ],
    "sinais_de_alarme": [
      "Dor abdominal intensa e contínua",
      "Vômitos persistentes",
      "Sangramento de mucosas (gengiva, nariz) ou manchas roxas",
      "Tontura, queda de pressão ao levantar ou sonolência/irritabilidade"
    ]
  },
  "evidencias_oficiais": [
    {
      "evidencia_id": "EV-01",
      "chunk_id": "ms-dengue-6ed-manejo-aines-01",
      "orgao_emissor": "MINISTERIO_DA_SAUDE",
      "titulo_documento": "Dengue: Diagnóstico e Manejo Clínico - Adulto e Criança (6ª edição)",
      "categoria": "protocolo_clinico",
      "secao": "contraindicacoes",
      "publico_alvo": ["geral", "pacientes_com_dengue"],
      "trecho_literal": "Os anti-inflamatórios não esteroidais (AINEs), como ibuprofeno, diclofenaco e nimesulida, bem como os salicilatos (ácido acetilsalicílico), são contraindicados em pacientes com suspeita ou confirmação de dengue devido ao risco aumentado de hemorragias e agravamento clínico.",
      "score_similaridade": 0.95
    },
    {
      "evidencia_id": "EV-02",
      "chunk_id": "ms-dengue-6ed-sinais-alarme-04",
      "orgao_emissor": "MINISTERIO_DA_SAUDE",
      "titulo_documento": "Dengue: Diagnóstico e Manejo Clínico - Adulto e Criança (6ª edição)",
      "categoria": "protocolo_clinico",
      "secao": "sinais_de_alarme",
      "publico_alvo": ["geral", "pacientes_com_dengue"],
      "trecho_literal": "Diante de sinais de alarme como dor abdominal intensa e contínua, vômitos persistentes, hipotensão postural, letargia ou sangramento de mucosas, o paciente deve buscar atendimento de urgência imediatamente.",
      "score_similaridade": 0.90
    }
  ],
  "disclaimer_medico": "Aviso importante: o EvidencIA Saúde é um assistente informativo baseado em documentos oficiais da Anvisa e do Ministério da Saúde. Ele não realiza diagnóstico médico, não substitui consulta profissional e não prescreve medicamentos. Em caso de sinais de alarme ou emergência, procure imediatamente uma UPA, pronto-socorro ou ligue para o SAMU (192).",
  "metadados_execucao": {
    "versao_pipeline": "v1.0.0",
    "versao_prompt": "prompts-v1.2",
    "versao_indice_rag": "corpus-v1.0.0",
    "modelo_llm": "llm-config-mvp",
    "latencia_ms": 1680
  }
}
```

**Saída C — Resposta *Fail-Safe* (`EVIDENCIA_INSUFICIENTE` / Fora do Escopo do MVP):**

```json
{
  "request_id": "7a1d5e88-90c4-4b21-b811-44fe22aa9900",
  "timestamp_resposta": "2026-11-19T20:40:12Z",
  "rota_acionada": "evidencia_insuficiente",
  "agentes_executados": ["agente_estruturador_roteador"],
  "classificacao_risco": "EVIDENCIA_INSUFICIENTE",
  "resumo_decisao": "Não foram encontradas evidências oficiais suficientes na base atual do EvidencIA Saúde (Anvisa e Ministério da Saúde) para responder com segurança à sua consulta. Para evitar orientações imprecisas, o sistema não emite recomendações sem respaldo documental oficial. Procure orientação de um médico, farmacêutico ou unidade de saúde.",
  "detalhamento_vacinal": null,
  "detalhamento_clinico_medicamentoso": null,
  "evidencias_oficiais": [],
  "disclaimer_medico": "Aviso importante: o EvidencIA Saúde é um assistente informativo com recorte inicial focado no calendário vacinal adulto/gestante e protocolos selecionados (dengue, malária e gripe). Ele não substitui atendimento médico ou farmacêutico.",
  "metadados_execucao": {
    "versao_pipeline": "v1.0.0",
    "versao_prompt": "prompts-v1.2",
    "versao_indice_rag": "corpus-v1.0.0",
    "modelo_llm": "llm-config-mvp",
    "latencia_ms": 410
  }
}
```

---

## 6. Contrato JSON de Feedback (`POST /api/v1/feedback`)

Conecta a **Etapa 6 das Jornadas** (Mariana e Pedro) ao monitoramento em produção (**Prometheus + Grafana**), sem coletar dados pessoais identificáveis:

### 6.1. Payload de Entrada do Feedback

```json
{
  "request_id": "2c8a4f90-1e33-4a9b-8f12-0d7c3e9a5b44",
  "avaliacao": "UTIL",
  "motivo_opcional": "clara_e_confiavel",
  "comentario_livre": "O alerta sobre ibuprofeno com trecho do Ministério da Saúde foi muito claro.",
  "timestamp_feedback": "2026-11-19T20:36:15Z"
}
```

* **`avaliacao`** *(obrigatório)*: `"UTIL"` ou `"INUTIL"`.
* **`motivo_opcional`** *(opcional)*: `"clara_e_confiavel"`, `"faltou_detalhe"`, `"nao_entendi"`, `"fonte_incompleta"`, `"outro"` ou `null`.
* **`comentario_livre`** *(opcional, máx. 500 caracteres)*: exibido na interface com aviso explícito para **não inserir nome, CPF, telefone ou dados identificáveis**; sanitizado antes de persistência analítica.

### 6.2. Resposta da API (`201 Created`)

```json
{
  "status": "registrado",
  "request_id": "2c8a4f90-1e33-4a9b-8f12-0d7c3e9a5b44"
}
```

---

## 7. Endpoints Auxiliares e Contrato Padronizado de Erros

### 7.1. Endpoints da API REST (`#21`)

| Método | Rota | Finalidade | Consumidor Principal |
| :-: | :--- | :--- | :--- |
| `POST` | `/api/v1/consultar` | Executa o pipeline Estruturador → Orquestrador → Especialistas + RAG e retorna resposta estruturada com evidências. | Streamlit |
| `POST` | `/api/v1/feedback` | Registra avaliação *"Útil"* / *"Inútil"* vinculada ao `request_id` e incrementa contadores no Prometheus. | Streamlit |
| `GET` | `/health` | Verifica disponibilidade da API e conectividade com a Base Vetorial local (`status: "ok"` / `"degraded"`). | Docker Healthcheck / CI |
| `GET` | `/metrics` | Expõe métricas técnicas e de produto no formato Prometheus (*scraping* contínuo). | Prometheus |

### 7.2. Envelope Padronizado de Erros (`400`, `422`, `500`, `503`)

```json
{
  "erro": {
    "codigo": "PAYLOAD_INVALIDO",
    "mensagem": "O campo 'perfil_usuario.semanas_gestacao' só pode ser preenchido quando 'perfil_usuario.gestante' for true.",
    "request_id": "9f3b1c2e-7b4d-4d62-a2c9-5a8b6f1e4c11",
    "detalhes": [
      {
        "campo": "perfil_usuario.semanas_gestacao",
        "motivo": "Inconsistência lógica com gestante=false"
      }
    ]
  }
}
```

| Código HTTP | Código Interno | Situação |
| :-: | :--- | :--- |
| `400` / `422` | `PAYLOAD_INVALIDO` | Violação de tipos, enums ou regras lógicas do Contrato JSON de entrada. |
| `500` | `ERRO_INTERNO_PIPELINE` | Falha inesperada na execução dos agentes; nunca retorna recomendação parcial não validada. |
| `503` | `SERVICO_INDISPONIVEL` | Indisponibilidade temporária da Base Vetorial local ou do provedor/runtime de LLM. |
