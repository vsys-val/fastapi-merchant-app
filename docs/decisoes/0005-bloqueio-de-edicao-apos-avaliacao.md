# ADR-0005 — Bloqueio de edição do produto após avaliação de terceiros

- Status: aceita
- Data: 2026-08-17
- Origem: `0fe656c` (protege edição de produtos compartilhados)

## Contexto

Com o catálogo comunitário ([ADR-0004](0004-catalogo-canonico-comunitario.md)), o criador de um produto pode errar no cadastro e precisa corrigir. Mas, se outra pessoa já avaliou "Detergente X 500 ml", mudar o registro para "Detergente X 5 L" faria a avaliação dela apontar para um produto que ela nunca usou. Isso corrompe a memória alheia.

## Alternativas consideradas

- **Edição livre pelo criador.** Risco de corromper avaliações de terceiros, por erro ou de propósito.
- **Nenhuma edição.** Erros de digitação ficam para sempre.
- **Edição com moderação.** Exige fluxo administrativo, que está fora do MVP.
- **Edição pelo criador até que outra pessoa avalie.** Corrige o erro comum (logo após o cadastro) sem afetar ninguém.

## Decisão

O **responsável atual** pode editar o produto enquanto não existir avaliação de **outro** usuário. A avaliação do próprio responsável não bloqueia. Depois disso, a edição retorna `409 product_locked_by_reviews`.

## Consequências

- ➕ Protege a integridade do que cada pessoa avaliou.
- ➕ Cobre o caso mais comum: o erro percebido logo depois do cadastro.
- ➖ Erros descobertos tarde ficam no catálogo até existir moderação ([roadmap](../roadmap.md)).
- ➖ A interface web ainda não expõe a edição de produto. O requisito está implementado e testado só na API ([rastreabilidade](../rastreabilidade.md)).

## Rastreabilidade

RF07 · RN13 · UC07 · T12, T13, T32 · `app/products.py::update_product`
