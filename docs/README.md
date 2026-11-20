# EvidencIA Saúde

> **Sistema Multiagentes com RAG para Apoio à Decisão Segura em Saúde**  
> **Disciplina:** Sistemas de Machine Learning (UnB) — **Challenge 2**  
> **Big Idea:** Qualidade de Vida — *"Empoderando pessoas com IA para compreender melhor, decidir melhor e viver melhor."*  
> **Entrega Final:** 07/12 | **Equipe:** 5 integrantes | **Custo Previsto:** R$ 0,00 (Stack 100% Open Source)

---

## Sobre o Projeto

O **EvidencIA Saúde** é um assistente inteligente de apoio à decisão em saúde preventiva e manejo inicial de sintomas, desenvolvido no contexto do **Challenge 2** da disciplina de Sistemas de Machine Learning da Universidade de Brasília (UnB).

A solução apoia cidadãos na identificação de vacinas pendentes, na verificação de contraindicações de vacinas e medicamentos e na consulta de condutas seguras diante de doenças prevalentes, respondendo **exclusivamente com base em evidências oficiais da Anvisa e do Ministério da Saúde** por meio de **RAG (*Retrieval-Augmented Generation*)** e **múltiplos agentes especializados**.

> **Aviso Fundamental:** O EvidencIA Saúde **não é um médico, não realiza diagnóstico clínico fechado e não prescreve medicamentos**. Toda recomendação tem caráter estritamente informativo e é acompanhada de citação literal da fonte oficial (Anvisa ou Ministério da Saúde) e orientação para busca de atendimento profissional.

---

## Essential Question

> *"Como apoiar cidadãos na tomada de decisão segura sobre vacinação pendente, manejo de sintomas e contraindicações de medicamentos usando evidências oficiais da Anvisa e do Ministério da Saúde?"*

---

## Mapa da Documentação

Esta documentação consolida a concepção do produto, a arquitetura de MLOps sob custo zero, os contratos técnicos que destravam a implementação (`#11`, `#12` e `#24`) e as diretrizes de governança, ética e LGPD:

| Seção | Documento | Objetivo Principal |
| :--- | :--- | :--- |
| **Concepção** | [Challenge 2 e Essential Question](/concepcao/challenge-e-essential-question.md) | Formalização da Big Idea, restrições do desafio, *Essential Question* e Roadmap (26/10 a 07/12). |
| **Concepção** | [Lean Inception e Canvas MVP](/concepcao/lean-inception.md) | Visão do produto, É/Não É/Faz/Não Faz, Personas (Mariana e Pedro), Jornadas, Clusters de escopo, Canvas MVP e Horizonte Pós-MVP. |
| **Arquitetura & MLOps** | [As 5 Perguntas Fundamentais de MLOps](/arquitetura/perguntas-fundamentais-mlops.md) | Resposta estruturada às 5 perguntas fundamentais da disciplina de MLOps conectando concepção, operação e governança. |
| **Arquitetura & MLOps** | [Papéis e Responsabilidades (R1 a R7)](/arquitetura/papeis-e-responsabilidades.md) | Mapeamento dos 7 papéis de MLOps (Kreuzberger et al., 2023) entre os 5 integrantes do grupo e Matriz RACI. |
| **Arquitetura & MLOps** | [ADR-001: Arquitetura MLOps sob Custo Zero](/arquitetura/adr-001-arquitetura-mlops-mvp.md) | Decisões arquiteturais sobre os 9 componentes de MLOps (C1 a C9): adoções, simplificações e omissões justificadas no MVP. |
| **Arquitetura & MLOps** | [Contrato JSON e Metadados do RAG](/arquitetura/contrato-json-e-metadados-rag.md) | Especificação dos payloads de entrada, roteamento interno, saída, feedback e esquema de metadados obrigatórios do RAG (destravando `#11`, `#12` e `#24`). |
| **Governança & Ética** | [Riscos Clínicos, Viés, Ética e LGPD](/governanca/riscos-vies-etica-lgpd.md) | Matriz de riscos clínicos e operacionais, mitigação de vieses, limitações éticas, *disclaimers* e conformidade com a Lei nº 13.709/2018 (LGPD). |

---

## Equipe e Papéis no Projeto

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

Para o mapeamento completo dos 7 papéis da literatura de MLOps (`R1` a `R7`) e a Matriz RACI por macroentrega, consulte [Papéis e Responsabilidades (R1 a R7)](/arquitetura/papeis-e-responsabilidades.md).

---

## Como Executar a Documentação Localmente

Esta documentação utiliza **Docsify** e pode ser servida localmente sem etapa de build:

**Opção 1 — Usando Python (sem instalar dependências):**

```bash
python -m http.server 3000 --directory docs
```

**Opção 2 — Usando Docsify CLI (com live reload):**

```bash
npx docsify-cli serve docs --port 3000
```

Após executar um dos comandos acima, acesse `http://localhost:3000` no navegador.
