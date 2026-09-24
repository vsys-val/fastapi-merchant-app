# ADR-0006 — Avaliação pessoal separada dos indicadores comunitários

- Status: aceita
- Data: 2026-08-17
- Origem: `4ca0f89` (define autoria pública das avaliações) e seção "Visibilidade das avaliações" da ideação

## Contexto

Ao abrir um produto, a Ana quer duas respostas diferentes: *"o que **eu** achei?"* e *"o que **os outros** acharam?"*. Se a avaliação dela entrar na média, dois problemas aparecem:

1. em produtos com poucas avaliações, a comunidade vira um eco da própria opinião (1 de 2 avaliações = 50%);
2. a opinião pessoal, que é o sinal mais forte para a recompra, fica diluída.

## Decisão

- Para **usuário autenticado**, a própria avaliação vem em `your_review` (detalhe) ou `your_repurchase_intent` (busca) e é **excluída** dos indicadores e da lista comunitária.
- Para **visitante**, todas as avaliações compõem os indicadores.
- Os indicadores são calculados **sob demanda** a partir das avaliações existentes. Nada é armazenado.

## Consequências

- ➕ A interface mostra "Sua experiência" em destaque e "Resumo da comunidade" como sinal independente.
- ➕ Sem denormalização, editar ou excluir uma avaliação reflete na consulta seguinte, sem job de recálculo.
- ➖ O mesmo produto mostra números diferentes para visitante e para autor. Isso é intencional e está documentado no contrato.
- ➖ O cálculo sob demanda custa mais por consulta. Aceitável no volume do MVP; cache é evolução prevista no [roadmap](../roadmap.md).

## Rastreabilidade

RF05, RF12 · RN26, RN27 · UC05 · T26, T27 · `app/catalog.py::_split_reviews`
