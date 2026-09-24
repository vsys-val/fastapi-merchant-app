# ADR-0001 — Avaliação estruturada, sem nota geral

- Status: aceita
- Data: 2026-08-17
- Origem: `98fffbb` (docs: define avaliação estruturada e responsabilidades da API), `c8c7a89`, `efc363c`

## Contexto

O objetivo do produto é apoiar a decisão de recompra ([visão](../visao-produto.md)). Escalas numéricas como estrelas ou 0 a 10 são familiares, mas têm problemas conhecidos: a mesma nota significa coisas diferentes para pessoas diferentes, as distribuições se concentram nos extremos e um "3" não informa o que deu errado. O produto também cobre categorias muito diferentes, de café a desinfetante, e a avaliação precisa fazer sentido em todas.

## Alternativas consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| Nota de 1 a 5 estrelas | Familiar, rápida, fácil de agregar | Ambígua, pouco acionável, não diz o porquê |
| Curtir / não curtir | Mínima fricção | Perde nuances ("bom, mas caro") |
| **Critérios semânticos fixos** | Cada resposta tem significado explícito; comparável entre categorias | Um pouco mais de esforço para avaliar |
| Critérios por categoria | Máxima precisão | Explosão de modelos; adia o MVP |

## Decisão

Não haverá nota geral manual. A avaliação combina:

- **intenção de recompra** (ver [ADR-0002](0002-intencao-de-recompra-como-resumo.md));
- três **critérios universais** com três respostas semânticas cada:

| Critério | Respostas |
|---|---|
| Qualidade percebida | baixa · adequada · alta |
| Atendimento às expectativas | não atendeu · atendeu · superou |
| Custo-benefício | ruim · justo · bom |

A API usa valores controlados em inglês (`low`/`adequate`/`high` etc.). A interface os traduz.

## Consequências

- ➕ Indicadores comunitários são distribuições percentuais legíveis ("62% acham o custo-benefício justo"), não médias.
- ➕ O mesmo modelo serve para qualquer categoria. Não existem critérios por categoria no MVP.
- ➕ Três opções por critério reduzem a indecisão no celular.
- ➖ Avaliar leva mais tempo que dar uma nota. Mitigação: formulário em etapas no frontend e o [guarda-corpo de abandono](../visao-produto.md#7-métricas-de-sucesso).
- ➖ Não existe "ranking por nota". Ordenar por qualidade exigirá uma regra explícita no futuro.

## Rastreabilidade

RN16–RN20 · UC08, UC09 · T19, T27 · `app/schemas.py` (tipos `Literal`), CHECKs `ck_avaliacoes_*`
