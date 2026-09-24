# ADR-0002 — Intenção de recompra como resumo principal

- Status: aceita
- Data: 2026-08-17
- Origem: `98fffbb` (docs: define avaliação estruturada e responsabilidades da API)

## Contexto

Sem nota geral ([ADR-0001](0001-avaliacao-estruturada-sem-nota.md)), a listagem de produtos ainda precisa de **um** sinal que caiba em uma linha de resultado de busca no celular. Esse sinal deve responder diretamente à pergunta que a pessoa faz no corredor.

## Alternativas consideradas

- **Média ponderada dos três critérios.** Esconde a regra de cálculo e volta a ser uma "nota".
- **Critério "qualidade" como destaque.** Um produto pode ter qualidade alta e mesmo assim não valer a recompra, por exemplo por ser caro demais.
- **Intenção de recompra (sim / talvez / não).** É a própria decisão que o produto quer apoiar.

## Decisão

A **intenção de recompra** é obrigatória e é o resumo principal. Os valores são `yes` (compraria novamente), `maybe` (talvez comprasse) e `no` (não compraria novamente).

- Na **busca**, cada item traz só a distribuição de recompra da comunidade e, para usuário logado, a própria intenção (`your_repurchase_intent`).
- No **detalhe**, aparecem a recompra e os três critérios.

## Consequências

- ➕ O resultado de busca responde à pergunta do usuário sem abrir o produto.
- ➕ O payload da listagem é pequeno (`ProductListCommunitySummary` só com recompra).
- ➖ "Talvez" pode virar a resposta de conforto. Acompanhar a distribuição real depois do lançamento.

## Rastreabilidade

RN16 · RF12 · UC04, UC05 · T26, T27 · `app/catalog.py` (`_list_summary`, `_community_summary`) · frontend: `ProductCard` e "Lembrete para você"
