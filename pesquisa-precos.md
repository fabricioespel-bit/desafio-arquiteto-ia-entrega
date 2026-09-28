# Pesquisa de preços e disponibilidade

Coletado em **26/set/2026**. Preços em USD, tabela pública *on-demand*, sem desconto negociado. Fontes no
fim do documento. Disponibilidade de modelos **testada com chamadas reais** num projeto GCP de laboratório.

## 1. Nomes atuais dos produtos (rebranding)

O Google renomeou a linha de IA. O documento final deve usar os nomes novos:

| Nome antigo | Nome atual (set/2026) |
|---|---|
| Vertex AI | **Gemini Enterprise Agent Platform** ("Agent Platform") |
| Vertex AI Agent Engine | **Agent Runtime** (+ Sessions, Memory Bank) |
| Vertex AI Search | **Agent Search** |
| Dialogflow CX / Agent Builder conversacional | **Customer Experience Agent Studio** |
| Vertex AI RAG Engine | **RAG Engine on Gemini Enterprise Agent Platform** |
| — | **Agent Gateway** (Agent-to-Anywhere): governança de chamadas/autorização dos agentes |

## 2. Modelos Gemini (padrão, ≤ 200k tokens de contexto, por 1M tokens)

| Modelo | Input | Input em cache | Output | Observação |
|---|---|---|---|---|
| Gemini 3.1 Flash-Lite | $0.25 | $0.025 | $1.50 | GA |
| Gemini 3.5 Flash-Lite | $0.30 | $0.03 | $2.50 | |
| Gemini 3.8 / 3.7 / 3.6 Flash | $0.75 | $0.075 | $3.75 | **preço promocional até 31/dez/2026**; de 1/jan/2027 em diante: $1.50 / $0.15 / $7.50 |
| Gemini 3.5 Flash | $1.50 | $0.15 | $9.00 | |
| Gemini 2.5 Flash | $0.30 | — | — | geração anterior; única disponível em `southamerica-east1` (ver seção 3) |
| Gemini 2.5 Pro | $1.25 | $0.125 | $10.00 | GA |
| Gemini 3.1 Pro | $2.00 | $0.20 | $12.00 | **Preview** |

- Endpoint **regional** (não-global) custa **+10%**.
- O tier **Priority** custa 1,8× o padrão; **Flex/Batch** custa 0,5× (serve para evals offline e reprocessamento).
- **Embeddings** (Gemini Embedding): $0.00015 por 1.000 tokens online (≈ $0.15/1M) e $0.00012 em batch.
- **Métricas de eval gerenciadas** baseadas em modelo são cobradas nos SKUs do modelo juiz.

> **Para o FinOps:** o Flash 3.x tem **preço promocional que dobra em jan/2027**. A estimativa para 50k
> conversas precisa mostrar os dois cenários, senão o custo do piloto fica subestimado pela metade a partir
> do 4º mês.

## 3. Disponibilidade por região (teste real, 26/set/2026)

| Modelo | `southamerica-east1` | `us-central1` | `global` |
|---|---|---|---|
| gemini-2.5-flash | ✅ | ✅ | ✅ |
| gemini-2.5-pro | ❌ | ✅ | ✅ |
| gemini-3.x Flash / Flash-Lite (3.1, 3.5, 3.7, 3.8) | ❌ | ❌ | ✅ |
| gemini-3.1-pro-preview | ❌ | ❌ | ✅ |

**Achado arquitetural importante:** em São Paulo só há o Gemini 2.5 Flash. Os modelos 3.x existem apenas no
**endpoint global**, que não garante o local de processamento. Para um banco, isso vira um trade-off real
entre residência de dados e capacidade do modelo, e merece uma ADR própria:
- **Opção A:** usar só modelos regionais em `southamerica-east1` (hoje, 2.5 Flash). Residência garantida,
  mas modelo mais antigo e sem Pro na região.
- **Opção B:** endpoint global para inferência, desde que **nenhum dado identificador nem financeiro chegue ao modelo** (o texto restante chega pseudonimizado)
  (tokenização/DLP antes do prompt), com dados em repouso, sessões e auditoria em `southamerica-east1`.
  Exige validar com Jurídico/DPO: LGPD, transferência internacional (art. 33) e a política de nuvem Bacen
  (Res. CMN 4.893/2021).
- **Recomendação preliminar:** o blueprint suporta as duas opções por configuração (o modelo é parâmetro).
  O piloto começa na Opção B com dados pessoais minimizados, e a decisão final fica com Compliance.

## 4. Agent Runtime (ex-Agent Engine)

| Recurso | Preço | Franquia mensal |
|---|---|---|
| Agent Compute | $0.085 / vCPU-h | 50 vCPU-h |
| Agent Memory | $0.009 / GiB-h | 100 GiB-h |
| Agent Storage (Sessions, Memory Bank) | $0.30 / GiB-mês | 1 GiB-mês |
| Sessions / Memory Bank: leitura | 1 vCPU-h ($0.085) a cada 3M operações | |
| Sessions / Memory Bank: escrita | 1 vCPU-h ($0.085) a cada 1M operações | |
| Agent Gateway | 1 vCPU-h ($0.085) a cada 15 mil chamadas/autorizações | |

- O tempo ocioso entre turnos **não é cobrado** no Runtime.
- A cobrança de Sessions e Memory Bank nesse modelo começou em **1/set/2026**.
- **Disponível em `southamerica-east1`** (teste real, 28/set/2026: listagem de `reasoningEngines` na região
  retornou HTTP 200).

## 5. RAG Engine

- É cobrado pelos componentes: ingestão, parsing por LLM (opcional), embeddings, banco vetorial e
  reranking (LLM ou Ranking API).
- Banco vetorial gerenciado: **Spanner Enterprise**.
  - Tier **Basic** (100 processing units): 0,1 nó × $0.41/réplica-h × 3 réplicas ≈ **$0.12/h ≈ US$ 90/mês**
    em `us-central1`.
  - Tier **Scaled**: de 1 a 10 nós (≈ US$ 900/mês por nó).
- Há também um modo *serverless*, sem preço publicado na página de billing (a confirmar).
- **Implicação:** no piloto, o custo fixo do banco vetorial (~US$ 90/mês) pesa mais do que o custo variável
  de embeddings de uma base pequena de documentos.
- **Disponível em `southamerica-east1`** (teste real, 28/set/2026: listagem de `ragCorpora` na região, API
  v1beta1, retornou HTTP 200).

## 6. Model Armor

- **Standalone:** grátis até **2M tokens/mês**; acima disso, **$0.10 por 1M tokens** (prompt + resposta analisados).
- Incluído, com cota, nos tiers Premium/Enterprise do Security Command Center (se o banco já tiver SCC,
  o custo marginal pode ser zero).
- Disponibilidade em `southamerica-east1` (teste de 28/set/2026): **inconclusiva, com sinal de ausência**.
  A API não está ativada no projeto (HTTP 403 na listagem de regiões), e o endpoint regional
  `modelarmor.southamerica-east1.rep.googleapis.com` nem conectou (HTTP 000). A confirmar na documentação.
- **Se não houver em SP, a exposição não muda:** o Model Armor analisa o mesmo texto que vai ao Gemini
  global, já mascarado no gateway. O que precisa ficar em SP é o **mascaramento (Sensitive Data
  Protection)**, que vê os dados reais: sua disponibilidade regional também está a confirmar.

## 7. WhatsApp Business Platform (Meta)

- **Mensagens de serviço** (iniciadas pelo cliente, dentro da janela de 24h): **gratuitas** desde 1/nov/2024.
- **Templates de utilidade** enviados dentro da janela aberta: **gratuitos**.
- Fora da janela, cobrança por mensagem entregue (Brasil, valores de referência de terceiros; confirmar no
  rate card oficial em BRL):
  - marketing: ~US$ 0.0625;
  - utilidade: ~US$ 0.008;
  - autenticação: ~US$ 0.0225.
- **BSP** (provedor de solução): se usado, soma um markup típico de **US$ 0.003 a 0.010 por mensagem**.
  Integração direta com a Cloud API da Meta não tem markup.

> **Correção de uma hipótese inicial:** supunha-se que "o custo do canal WhatsApp pode superar o custo
> de tokens". Para este caso de uso (atendimento **iniciado pelo cliente**), a Meta não cobra nada. O custo
> do canal só aparece em notificações proativas (fora da janela) **ou no markup de um BSP**. Com 50k
> conversas × ~8 mensagens × US$ 0.005, o markup chega a **~US$ 2.000/mês**, o que pode sim superar os tokens.
> Então a decisão "BSP vs. integração direta com a Cloud API" é uma alavanca de FinOps relevante.

## 8. Itens de menor peso (infra)

- **Cloud Run:** franquia de 240 mil vCPU-s/mês; *tier 1* de preços em `us-central1` e `southamerica-east1`.
  Custo marginal no piloto (webhook/API do canal).
- **Sensitive Data Protection:** cobrança por volume inspecionado. É irrelevante para textos curtos de
  conversa no volume do piloto (a detalhar na F6 se necessário).

## Pendências da pesquisa

- [ ] Rate card oficial da Meta em BRL (CSV/PDF), para substituir os valores de terceiros.
- [x] Agent Runtime e RAG Engine em `southamerica-east1`: **disponíveis** (teste real, 28/set/2026).
- [x] Model Armor em `southamerica-east1`: **não disponível** (documentação oficial de regiões, 28/set/2026:
  nenhuma região na América do Sul; mais próximas: `us-central1`, `us-east1`, `us-east4`, `us-west1`,
  multirregião `us` e `global`).
- [x] Sensitive Data Protection em `southamerica-east1`: **disponível, com endpoint regional** (dados em
  trânsito mantidos na região), documentação oficial, 28/set/2026.
- [ ] Preço do modo serverless do RAG Engine.
- [x] Decidido (26/set): Pro = **Gemini 2.5 Pro (GA)**; Flash padrão = **Gemini 3.8 Flash**; residência = **Opção B** (global sem dados identificadores nem financeiros + dados em SP).

## Fontes

- [Agent Platform — Generative AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) (Gemini, embeddings, tiers)
- [Gemini Enterprise Agent Platform pricing](https://cloud.google.com/vertex-ai/pricing) (Agent Runtime, Sessions, Memory Bank, Agent Gateway)
- [RAG Engine billing](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-engine-billing)
- [Spanner pricing](https://cloud.google.com/spanner/pricing)
- [Security Command Center pricing — Model Armor](https://cloud.google.com/security-command-center/pricing)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Model Armor locations](https://docs.cloud.google.com/model-armor/locations) e [Model Armor data residency](https://docs.cloud.google.com/model-armor/data-residency)
- [Sensitive Data Protection locations](https://docs.cloud.google.com/sensitive-data-protection/docs/locations)
- [WhatsApp Business Platform pricing (Meta)](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- [WhatsApp API pricing Brazil 2026 (Message Central)](https://www.messagecentral.com/blog/whatsapp-business-api-pricing-brazil) — referência de terceiros para as tarifas BR
- Disponibilidade regional: teste com `generateContent` num projeto GCP de laboratório, 26/set/2026
