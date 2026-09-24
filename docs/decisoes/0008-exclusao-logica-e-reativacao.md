# ADR-0008 — Exclusão lógica de produto e reativação por recadastro

- Status: aceita
- Data: 2026-09-08 (consolidada na implementação do MVP, PR #2)
- Origem: RF13 e "Precisões adotadas na consolidação" em `plano-implementacao.md`

## Contexto

O responsável pode querer remover um produto cadastrado por engano. Uma exclusão física liberaria o GTIN e a chave de identidade, mas perderia a rastreabilidade do registro. Uma exclusão de produto **com** avaliações apagaria a memória de outras pessoas.

## Decisão

- Um produto só pode ser excluído pelo responsável atual e **só se não tiver nenhuma avaliação**, nem a própria.
- A exclusão é **lógica** (`excluido_em`). O produto some de buscas, detalhes e listas.
- Se alguém cadastrar de novo o mesmo item (mesmo GTIN ou identidade), o registro é **reativado** com o **mesmo ID**, os novos dados e o novo responsável. A resposta é `200` em vez de `201`.

## Consequências

- ➕ Nenhuma avaliação se perde por exclusão de produto.
- ➕ As restrições de unicidade continuam válidas e não há "fantasmas" que impeçam recadastro.
- ➖ O `200` na criação é uma sutileza de contrato. Está documentada no contrato e testada (T16).

## Rastreabilidade

RF13 · RN12 · UC06, UC11 · T14–T16 · `app/products.py::create_product`, `delete_product`
