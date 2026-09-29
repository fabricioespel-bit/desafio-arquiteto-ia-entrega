# Desafio técnico: Arquiteto(a) de Soluções Especialista em IA

Resposta de Fabricio Espel ao desafio técnico: arquitetura de ponta a ponta de um assistente agêntico para o
Motor de Relacionamento com o Cliente, desenhado como blueprint replicável.

## Documento

**[Fabricio-Espel_Desafio-Arquiteto-Solucoes-IA_Assistente-Agentico.pdf](Fabricio-Espel_Desafio-Arquiteto-Solucoes-IA_Assistente-Agentico.pdf)**:
corpo de 6 páginas, na ordem dos 7 itens do enunciado, com apêndice de referência (premissas e fontes de
custo, sensibilidade, implantação, integrações, drift, adoção, pontos de discovery e referências).

## Protótipo

**[agentic-cx-blueprint](https://github.com/fabricioespel-bit/agentic-cx-blueprint)** (público): protótipo
desta arquitetura em versão genérica, com banco fictício. O núcleo determinístico (catálogo, política,
confirmação amarrada, idempotência e servidor MCP de cartões) e o agente integrado a ele (LLM só no
classificador) estão implementados e testados.

## Conteúdo do repositório

| Caminho | O que é |
|---|---|
| `documento.md` | Fonte do documento |
| `diagramas/gerar.py` | Gera os 4 diagramas (C4 Context, Container, Component e sequência) como SVG |
| `diagramas/*.svg` | Diagramas gerados |
| `build/build.py` | Gera o PDF a partir do Markdown e dos SVG (Markdown → HTML/CSS → PDF pelo Chrome) |
| `pesquisa-precos.md` | Pesquisa de preços e disponibilidade regional, com fontes e datas, base da estimativa de custos |

## Como regenerar o PDF

Requer Python 3.11+, [uv](https://docs.astral.sh/uv/) e Google Chrome.

```bash
python3 diagramas/gerar.py
cd build && uv run --with markdown --with pypdf python build.py
```
