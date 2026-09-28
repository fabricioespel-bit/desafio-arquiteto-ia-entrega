# Assistente agêntico do Motor de Relacionamento

**Arquitetura de referência e blueprint replicável** · Fabricio Espel · setembro de 2026

---

## Resumo executivo

O piloto adiciona ao Motor de Relacionamento uma camada agêntica que atende o cliente no WhatsApp e no app,
responde com base no conhecimento oficial do banco e executa transações simples. Por ser o primeiro caso do
CoE, nasce como **blueprint**: o que é comum a qualquer área vira plataforma; o que é de domínio vira
configuração.

A tese central é **"o LLM interpreta, a regra autoriza"**: o modelo entende o cliente e redige respostas; se
uma ação pode ser executada, com quais parâmetros e com qual autenticação, quem decide é código
determinístico, testável e auditável. Quatro ideias estruturam o documento: **evolução, não substituição**
(convivência com o atendimento atual e migração por intenção); **quatro tipos de pedido**, com escalonamento
para humano como saída transversal; **defesa em profundidade**; e **quatro encaixes** que a próxima área
preenche. Premissas e fontes estão no apêndice.

---

## 1. Arquitetura de solução

### 1.1 Contexto (C4, nível 1)

> **[Diagrama 1: C4 Context]**

O escopo é a camada agêntica, dentro do Motor de Relacionamento e ao lado do atendimento atual, que é
preservado. O **app tem papel duplo**: canal e fator de autenticação. A **identidade chega pelo provedor de
identidade**, nunca pelo texto da conversa. A **plataforma de IA é sistema externo** por ser o único ponto em
que dado sai da jurisdição (endpoint global); por isso recebe só texto pseudonimizado, sem dados
identificadores nem financeiros.

### 1.2 Containers (C4, nível 2)

- **Plataforma compartilhada, operada pelo CoE:** gateway de canal, política, guardrails, auditoria,
  observabilidade. **Templates:** agente e base de conhecimento por área de negócio; servidor MCP por domínio
  de sistema.
- **Política consultada duas vezes:** pelo agente, para conduzir a conversa, e pelo servidor MCP, que barra na
  execução. Vale a do executor.
- **Cofre de sessão:** token do cliente e dados pessoais num Firestore em São Paulo, criptografado e com
  expiração, acessível por IAM só ao gateway e ao servidor MCP. O agente não tem permissão alguma, e a
  identidade chega ao MCP pelo contexto autenticado da requisição, nunca por parâmetro escolhido pelo LLM.
- **Guardrails em dois pontos:** o mascaramento (Sensitive Data Protection, em São Paulo) acontece no gateway,
  antes do agente; o Model Armor, sem região no Brasil, atua no agente sobre texto já pseudonimizado.
- **Integrações** só via servidor MCP (pelo gateway de APIs corporativo, com troca de token), gateway de canal
  ou barramento de eventos. O agente não chama APIs.

> **[Diagrama 2: C4 Container]**

### 1.3 Componentes do agente (C4, nível 3)

> **[Diagrama 3: C4 Component do Agente]**

O agente é um **grafo determinístico com LLM dentro dos nós**: o LLM classifica, responde perguntas de
conhecimento, esclarece e resume para o atendente; a sequência "autenticar → confirmar → executar" é do grafo
e não pode ser pulada. Ferramentas de escrita existem só no subfluxo transacional: um agente de conhecimento
manipulado por conteúdo malicioso não pode chamá-las, porque elas não estão no seu contexto.

### 1.4 Decisões principais

| Decisão | Escolha | Alternativa descartada | Por quê |
|---|---|---|---|
| **Build vs. buy** | Comprar a plataforma (Gemini, Agent Runtime, RAG Engine, Model Armor, provedor de WhatsApp); construir o diferencial (integração transacional, política, guardrails de ação, avaliação) | Suíte de atendimento pronta; construir tudo | O diferencial do banco está nas regras e no controle das ações, não no motor de linguagem. Padrões abertos nas fronteiras (MCP, OpenTelemetry) reduzem o lock-in |
| **Modelo único vs. multimodelo** | Gemini Flash por padrão; Gemini Pro só no conhecimento, por critério (várias fontes, falha na verificação, tema regulatório) | Pro para tudo; Flash para tudo | A maioria das mensagens é simples. O critério leva o Pro para onde muda o resultado e é validado na avaliação. Nunca no caminho transacional |
| **Orquestração** | ADK no Agent Runtime, com grafo determinístico e LLM nos nós | Agente autônomo com todas as ferramentas; orquestração própria; LangGraph | Autonomia onde agrega valor, previsibilidade onde não pode haver erro. Plataforma gerenciada, alinhada à stack GCP, reduz o custo de replicar |

**Residência:** inferência no endpoint global, com sessões, base e auditoria em São Paulo; em SP há hoje só o
Gemini 2.5 Flash. O modelo é parâmetro, e a opção regional fica disponível se Compliance decidir. **RAG** por
padrão; GraphRAG quando um caso exigir relações que a busca perde. **A2A** previsto como evolução.

---

## 2. Fluxo agêntico

### 2.1 Tipos de pedido e a decisão "responder vs. executar"

| Tipo | Exemplo | Caminho | Exige |
|---|---|---|---|
| Informação geral | "Qual a anuidade do cartão?" | Busca na base, com citação | Nada |
| Consulta | "Qual meu limite?" | Ferramenta de leitura | Número vinculado |
| Transação | "Bloqueia meu cartão" | Política → confirmação → escrita | Autenticação conforme o risco |
| Fora de escopo | "Qual ação devo comprar?" | Recusa educada | — |

A decisão **não é do modelo**: (1) o LLM classifica numa intenção do catálogo; (2) o **catálogo** define tipo,
risco, autenticação, limites e fase liberada, e nega o que não conhece; (3) a **política** decide; (4) a
política gera a **confirmação amarrada aos parâmetros** (texto fixo, uso único, validade curta), o cliente
confirma por botão e o executor só aceita o que bate com ela. O catálogo é configuração versionada, alterada
com segregação de funções e publicada assinada; acima dele, um **piso de invariantes do CoE** (toda escrita
exige confirmação; intenção nova entra em shadow mode) que nenhuma área sobrescreve.

### 2.2 Fluxo de referência: bloqueio de cartão

É o caminho mais completo; os demais tipos são recortes dele.

> **[Diagrama 4: diagrama dinâmico do bloqueio]** 23h10, número vinculado: "perdi minha carteira, bloqueia
> meu cartão urgente".

1. **Gateway** valida, deduplica, identifica o número, mascara e roteia. *Sem LLM.*
2. **Classificador** identifica `bloqueio_temporario_cartao`. ***Única chamada ao LLM.***
3. **Ferramenta de leitura** lista os cartões para o subfluxo (código), que pergunta qual com botões. *Sem LLM:
   dados do cartão não passam pelo modelo.*
4. **Política** aprova com confirmação; o cliente toca em "Sim, bloquear". *Sem LLM.*
5. **Servidor MCP** executa em nome do cliente, com idempotência. *Sem LLM.*
6. **Evento** para antifraude, CRM e notificação por outro canal. *Sem LLM.*
7. **Resposta** em texto fixo, reforçando que o desbloqueio é só no app; tudo vai à **auditoria**. *Sem LLM.*

**Falhas:** na ambiguidade, pergunta direcionada com botões e, após duas tentativas, escalonamento; o limite
de confiança é maior para transações e calibrado na avaliação. Erro de classificação nunca vira ação: a
confirmação é a última barreira. Sem resposta do sistema, **nunca afirma sucesso**: consulta o estado, abre
protocolo, informa o canal 24h e reconcilia depois.

### 2.3 Fluxo de referência: pergunta de conhecimento

"Qual a anuidade do Gold?" (nível 0): **classificação** *(LLM)* → **cache semântico** para perguntas
repetidas, com mesma intenção e entidades e documentos vigentes; consulta e transação nunca são cacheadas
*(sem LLM)* → **busca** em documentos vigentes e com dono, com valores vindos da **tabela oficial** *(sem LLM)*
→ **resposta** com citação por afirmação *(LLM; Pro se o critério acionar)* → **verificação de
fundamentação**; se falhar duas vezes, recusa e oferece humano *(LLM)* → **Model Armor** e envio. Até três
chamadas por turno: é o fluxo de maior risco e maior custo.

### 2.4 Autenticação progressiva

O número do WhatsApp **identifica, mas não autentica**. Segue o padrão do mercado brasileiro: vínculo pelo
app, autorização separada para transacionar, fator por operação, limites por canal.

| Nível | Como se obtém | Libera |
|---|---|---|
| 0 | — | Informação geral |
| 1 | Número vinculado | Consultas |
| 2 | Autorização no app + sessão curta | Transações de baixo risco |
| 3 | Biometria no app para a operação | Transações de risco médio |

A exigência segue o **risco da ação**: o bloqueio temporário, reversível, exige nível 1 e confirmação; o
desbloqueio, nível 3 e só no app, o que fecha o caminho do golpe da falsa central.

### 2.5 Memória e escalonamento

Curto prazo é a sessão. Longo prazo, só preferências de interação, com consentimento; **fatos transacionais
ficam nos sistemas de registro e no CRM**, consultados por ferramenta (evita dado desatualizado e
envenenamento de memória). Escala para humano por pedido, negativa da política, falta de fonte, falhas
repetidas, tema sensível ou frustração, com resumo; fora do horário, protocolo e canal 24h para urgências.

---

## 3. Guardrails, segurança e compliance

### 3.1 Ameaças e controles

| Ameaça | Controles (camadas) |
|---|---|
| **Alucinação** | Resposta só com trechos recuperados · citação · verificação de fundamentação · valores de fonte estruturada · recusa sem fonte |
| **Prompt injection** | Model Armor (entrada, conteúdo recuperado, saída) · escrita fora do contexto do LLM · política · confirmação amarrada · identidade pelo canal |
| **Vazamento** | Dados identificadores e financeiros fora do LLM (3.2) · ferramentas limitadas ao cliente autenticado |
| **Ações indevidas** | Negação por padrão · autenticação por risco · limites · política no executor · idempotência · antifraude |
| **Adulteração da configuração** | Catálogo versionado, assinado, somente leitura em produção · alerta a cada versão · piso do CoE |
| **Abuso e custo** | Limite de mensagens por cliente · teto de turnos e contexto · alertas de custo |
| **Base envenenada** | Fontes aprovadas e com dono · triagem de documentos · versionamento |

O Model Armor reduz o volume de ataques; a garantia vem das camadas determinísticas.

### 3.2 Dados do cliente fora do modelo

**O LLM redige; quem preenche os valores do cliente é código.** Identidade: o modelo não recebe CPF, nome ou
conta. O que o cliente digita: marcadores reversíveis (`[CPF_1]`), com o valor no cofre; número de cartão é
descartado, o que mantém a camada fora do escopo do PCI DSS. O que as ferramentas retornam: mensagens
transacionais são modelos fixos; consultas usam placeholders (`{limite_disponivel}`) preenchidos no envio.
**O limite:** o texto da conversa chega pseudonimizado, e dado pseudonimizado continua pessoal pela LGPD. O
risco cai, mas não zera; por isso a decisão de transferência é de Compliance/DPO.

### 3.3 LGPD e setor financeiro

- **LGPD:** minimização (art. 6) · exclusão e acesso (art. 18) · **toda negativa automática oferece humano
  (art. 20)** · transferência restrita a texto pseudonimizado (art. 33) · base para registro de tratamento e
  relatório de impacto (arts. 37–38) · transparência.
- **Auditoria:** intenção, versão do catálogo, regra, confirmação, hash dos parâmetros, resultado e versões,
  sem identificadores em claro; imutável, acesso restrito, retenção definida por Jurídico e Compliance.
- **Nuvem e modelos:** governança de nuvem do banco (Res. CMN 4.893/2021); mudanças versionadas, modelo com
  versão fixada, gate de avaliação, aprovação proporcional ao risco, agente no inventário de modelos.

---

## 4. Avaliação e observabilidade

**Offline (gate):** golden set, red team e regressão, em quatro níveis (recuperação, ingestão, resposta
final, contínuo), porque recuperação perfeita não garante resposta certa. Métricas por componente
(classificador, roteamento, trajetória); **zero ataques com escrita ou vazamento**; falso positivo de
guardrail também é defeito. Juiz LLM calibrado contra rótulos humanos, com modelo diferente do avaliado.
Limites definidos antes; são os critérios de promoção da seção 7.

**Online:** qualidade (juiz em amostra, falhas de fundamentação), segurança (ataques, bloqueios) e resultado
para o cliente, com **recontato em 24–72h** para não inflar a taxa de resolução.

**Observabilidade:** um trace por turno em **OpenTelemetry**, com um span por passo; um coletor distribui para
Cloud Trace, **Dynatrace** (OTLP) e Langfuse opcional. Trace, auditoria e conversa se correlacionam. Dos
traces saem latência p50/p95 e custo por conversa. Drift: distribuição de intenções, perguntas sem resposta
(backlog de conteúdo), qualidade e custo (detalhe no apêndice).

---

## 5. FinOps e escalabilidade

### 5.1 Estimativa para 50 mil conversas por mês

Premissas estimadas, a medir no shadow mode (apêndice A). Por conversa, o modelo custa US$ 0,042 no
conhecimento e US$ 0,010–0,013 nos demais tipos: **conhecimento custa quatro vezes uma transação**.

| Por mês | 2026 (preço promocional) | 2027+ (preço padrão) |
|---|---|---|
| Modelos | ~US$ 1.350 | ~US$ 2.600 |
| Demais itens (guardrails, banco vetorial, runtime, serviços, avaliações) | ~US$ 750 | ~US$ 750 |
| **Plataforma** | **~US$ 2.100 (~US$ 0,04/conversa)** | **~US$ 3.300 (~US$ 0,07/conversa)** |
| WhatsApp (Meta), iniciado pelo cliente | US$ 0 | US$ 0 |
| Provedor de WhatsApp, se cobrar por mensagem | US$ 1.350–4.500 | US$ 1.350–4.500 |

Fontes públicas de Google Cloud e Meta (26/set/2026); fora da conta ficam licenças já existentes e pessoas.
Três leituras: **o custo de modelo dobra em 2027**; **o provedor de WhatsApp pode custar mais que toda a
IA**, o que torna a integração direta uma decisão financeira; e o custo por conversa deve ser comparado ao do
atendimento atual.

### 5.2 Sensibilidade e alavancas

O mix é a premissa mais incerta, mas não a que mais pesa: se conhecimento subir de 50% para 60%, o custo de
modelo sobe ~11%; com 100%, 56% (~US$ 2.100/mês), sem mudar a ordem de grandeza. Pesam mais o fim do preço
promocional (+92%) e um turno a mais nas conversas de conhecimento (+26%). **Nenhum orçamento de escala é
comprometido antes de o shadow medir o mix e os turnos reais.**

Alavancas: integração direta com a Meta; **cache semântico** de informação geral (~30% do custo de
conhecimento); cache de contexto (~20%); Flash-Lite no classificador, se aprovado na avaliação; limite de
raciocínio e de turnos; avaliações em lote. Juntas, reduzem o custo de modelo em 40–50%.

### 5.3 Escala para milhões

Com 2 milhões de conversas/mês, o modelo iria a ~US$ 54–104 mil sem otimização. A arquitetura escala com
**fila** entre webhook e agente (picos de vencimento e datas do varejo), **capacidade reservada** de modelo com
cotas, **roteador como válvula** (baixa o canário e devolve tráfego ao atendimento atual), **amostragem de
traces** e **showback** de custo por área e intenção.

---

## 6. Reusabilidade e papel do CoE

**Aceleradores:** o que precisa ser igual para todos é serviço; o que muda por domínio é template. **Agentes
por área de negócio, servidores MCP por domínio de sistema, plataforma compartilhada no centro** (catálogo
completo no apêndice). A próxima área preenche quatro encaixes: **catálogo de intenções, ferramentas**
(reutilizando os MCP existentes), **base de conhecimento** e **conjunto de avaliação**. Com as integrações
disponíveis, chega ao shadow em cerca de seis semanas; o gargalo passa a ser APIs legadas e conteúdo. O
blueprint elimina o trabalho repetido, não o novo.

**Modelo de operação:**

- **Entrada única, quatro trilhas:** autoatendimento, caminho pronto, co-construção (vira acelerador) e "não é
  IA". Recusar bem também é papel do CoE.
- **Carteira:** maior parte da capacidade no caminho pronto, fatia fixa para apostas estruturantes (ex.:
  GraphRAG), fatia pequena para exploração; valor × viabilidade × reuso, com limite de iniciativas por
  arquiteto e fila visível.
- **Níveis de envolvimento:** o CoE faz → faz com a área → a área faz e o CoE revisa → a área é autônoma. O
  objetivo é mover as áreas para a direita.
- **Governança como código** e, contra o Shadow AI, **caminho oficial mais fácil**; ADRs, trilhas por papel e
  comunidade. Métricas: tempo até o shadow, reuso, maturidade das áreas, custo por área, incidentes.

---

## 7. Roadmap e riscos

### 7.1 Fases

Promoção **por intenção**, critérios definidos antes e que valem de verdade, regressão automática em
violação de segurança. Segurança é critério absoluto; qualidade é relativa ao atendimento atual.

| Fase | O que acontece | Para avançar |
|---|---|---|
| **0. Fundação** | Discovery, integrações, base com donos, avaliação, relatório de impacto | Gate aprovado · red team sem escrita nem vazamento |
| **1. Shadow** | Amostra de 10–20% das conversas processada **sem responder, executar ou consultar dados do cliente** | Qualidade em amostra rotulada · zero incidentes · mix e custo medidos, orçamento aprovado |
| **2. Assistido** | Agente redige, atendente aprova | Aceitação sem edição ≥ 80% |
| **3. Autônomo: conhecimento e consulta** | Canário 5% → 25% → 100% por intenção | Recontato e CSAT não piores · fundamentação ≥ 95% · kill switch testado |
| **4. Autônomo: transações** | Bloqueio → 2ª via → vencimento | Zero execuções sem confirmação · zero duplicidade · reconciliação testada · aprovação de Risco |

Valores iniciais, calibrados no shadow. A fase assistida antecipa valor e gera dados rotulados a cada edição.

### 7.2 Top 3 riscos arquiteturais

1. **Resposta errada com aparência de certa:** silenciosa, regulatória e reputacional. *Mitigação:*
   verificação de fundamentação, valores de fonte estruturada, documentos com dono e validade, avaliação da
   resposta final.
2. **Ação indevida pelo canal** (injection, engenharia social, falsa central). *Mitigação:* catálogo com
   negação por padrão, autenticação por risco, confirmação amarrada, política no executor, escrita fora do
   LLM, desbloqueio só no app.
3. **Dependência de integrações legadas:** a latência do legado vira latência da conversa. *Mitigação:* APIs
   levantadas na fase 0, MCP com idempotência e reconciliação, fila, degradação honesta, kill switch.

Monitorados: veto ao endpoint global (regional configurável), fim do preço promocional, descontinuação de
modelo, guardrails em português, lock-in.

### 7.3 Desafios de adoção

Dono do conteúdo da base · ciclo de Risco, Compliance e Jurídico · adesão dos atendentes · prioridade dos
times de sistemas legados · convivência com o time do atendimento atual · confiança do cliente e golpes ·
métrica de sucesso que não premie só contenção · soluções paralelas. Como enfrentar cada um: apêndice F.

<div style="break-before: page"></div>

## Apêndice

### A. Premissas e fontes de custo

Mix 50% conhecimento, 25% consulta, 15% transação, 10% fora de escopo · turnos 3/3/5/3 · tokens por chamada:
classificador 1.500/100, resposta de conhecimento 6.000/800 (~500 de raciocínio, cobrado como saída),
verificação 4.000/150 · Pro em 10% dos turnos de conhecimento. Custo de modelo por conversa (2026):
conhecimento US$ 0,042 · consulta 0,013 · fora de escopo 0,012 · transação 0,010 · média 0,027.

| Componente | Valor usado | Fonte (26/set/2026) | Tipo |
|---|---|---|---|
| Gemini Flash | US$ 0,75/3,75 por 1M até dez/2026; 1,50/7,50 depois | Preços de IA generativa, Google Cloud | Público |
| Gemini Pro | US$ 1,25/10 por 1M | Idem | Público |
| Agent Runtime | US$ 0,085/vCPU-h; 0,009/GiB-h (~US$ 100/mês) | Preços da Agent Platform | Público × estimativa de uso |
| Banco vetorial | ~US$ 90/mês (100 unidades de processamento) | Preços do Spanner | Público × configuração |
| Model Armor | 2M tokens/mês grátis; US$ 0,10/1M (~US$ 35/mês) | Preços do Security Command Center | Público |
| Serviços, dados, observabilidade | ~US$ 300/mês | — | Estimativa |
| Avaliações | ~US$ 200/mês | — | Estimativa |
| WhatsApp | Grátis quando iniciado pelo cliente | Política de preços da Meta | Oficial |
| Provedor de WhatsApp | US$ 0,003–0,010 por mensagem | Referências de mercado | **Não oficial** |

### B. Sensibilidade

| Premissa | Variação | Efeito no custo de modelo |
|---|---|---|
| Preço promocional → padrão | jan/2027 | +92% (certo) |
| Turnos nas conversas de conhecimento | 3 → 4 | +26% |
| Uso do Pro | 10% → 30% | +17% |
| Conhecimento no mix | +10 p.p. | +11% (consulta −7%, transação −7,5%, fora de escopo −6%) |

### C. Implantação

| Componente | Onde roda | Região |
|---|---|---|
| Gateway de canal, política, servidores MCP | Cloud Run | São Paulo |
| Agente (um por área) | Agent Runtime (portável para Cloud Run) | São Paulo (verificado) |
| Conhecimento | RAG Engine | São Paulo (verificado) |
| Mascaramento | Sensitive Data Protection | São Paulo (endpoint regional) |
| Model Armor | Gerenciado | EUA (sem região no Brasil), sobre texto pseudonimizado |
| Cofre, registro de execuções, cache | Firestore (bancos separados) | São Paulo |
| Auditoria | BigQuery + armazenamento imutável | São Paulo |
| Modelos Gemini | Plataforma de IA | Global (sem identificadores nem dados financeiros) |

Disponibilidade dos modelos e do Agent Runtime e RAG Engine verificada em chamadas reais em projeto GCP;
Model Armor e Sensitive Data Protection, pela documentação oficial de regiões.

### D. Integrações

A existência de cada API é premissa a confirmar no discovery.

| Sistema | Finalidade | Via | Modo |
|---|---|---|---|
| Cartões | Listar, limite/fatura, bloquear, status, 2ª via, vencimento | Servidor MCP | Leitura e escrita, síncrono |
| Tarifas e produtos | Valores oficiais | Servidor MCP | Leitura, síncrono |
| CRM / atendimento | Histórico; protocolo e handoff | Servidor MCP | Leitura e escrita |
| Antifraude | Consulta prévia · aviso após bloqueio | MCP · barramento | Síncrono · assíncrono |
| WhatsApp, app | Mensagens | Gateway de canal | Síncrono |
| Provedor de identidade | Token, nível, step-up | Gateway de canal | Síncrono |
| Atendimento atual | Intenções não migradas | Gateway (roteador) | Síncrono |
| Notificação | Push por outro canal | Barramento | Assíncrono |

### E. Drift e degradação

| Sinal | Ação |
|---|---|
| Mudança na distribuição de intenções | Alerta para negócio e segurança |
| Mais perguntas sem resposta | Backlog para os donos de conteúdo |
| Queda de qualidade | Investigação e rollback de versão |
| Aumento de custo ou latência | Revisão de roteamento e cache |

### F. Desafios de adoção

| Desafio | Como enfrentar |
|---|---|
| Dono do conteúdo | Dono nomeado por documento, com validade; lacunas viram backlog |
| Risco, Compliance, Jurídico | Desde a fase 0; avaliações como evidência; relatório de impacto; residência decidida cedo |
| Atendentes | Fase assistida como copiloto; atendentes como avaliadores |
| Sistemas legados | Patrocínio executivo; APIs mínimas e reutilizáveis |
| Atendimento atual | Convivência; roteador com governança compartilhada; migração negociada |
| Clientes | Transparência; comunicação anti-golpe; valor percebido incentiva o vínculo pelo app |
| Métrica de sucesso | Recontato e CSAT pesam tanto quanto contenção |
| Soluções paralelas | Caminho oficial mais fácil; custos medidos como argumento |

### G. A confirmar no discovery

Mix e volume reais por motivo de contato · plataforma e interface do atendimento atual · APIs de cartões,
tarifas, CRM e antifraude · jornada de autenticação existente no app e no WhatsApp · horário e ferramenta do
atendimento humano · gateway de APIs corporativo · contrato com o provedor de WhatsApp · retenção de
registros · posição de Compliance/DPO sobre o endpoint global.

### H. Referências de implementação própria

Decisões deste documento aplicam métodos que usei em projetos próprios:

- [rag-quality-assurance](https://github.com/fabricioespel-bit/rag-quality-assurance): avaliação em níveis e o
  caso de recuperação perfeita com resposta errada.
- [finops-llm-routing](https://github.com/fabricioespel-bit/finops-llm-routing): decisão de modelo por custo,
  com qualidade não negociável definida antes.
- [data-lake-engineering-decisions](https://github.com/fabricioespel-bit/data-lake-engineering-decisions):
  registro de decisões e governança de dados para agentes.
- [amigurumi-agent](https://github.com/fabricioespel-bit/amigurumi-agent): tracing de agente e humano no loop.
- [account-health-ml-service](https://github.com/fabricioespel-bit/account-health-ml-service): drift e critério
  de produção definido antes.
- Em repositórios privados: template de servidor MCP com OAuth por usuário e agentes ADK em produção no GCP.
