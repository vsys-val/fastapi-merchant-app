# ADR-0007 — Uma avaliação atual por produto, sem histórico

- Status: aceita
- Data: 2026-08-17
- Origem: `f335771` (define avaliação única e editável por produto), `dfaf0ee` (define exclusão de avaliações)

## Contexto

Produtos mudam (fórmula nova, embalagem nova) e opiniões também. Permitir várias avaliações do mesmo usuário para o mesmo produto infla os indicadores. Guardar histórico de versões tem valor analítico, mas aumenta modelo, contrato e interface.

## Decisão

- Cada usuário tem **no máximo uma avaliação atual** por produto, garantido pela UNIQUE `(usuario_id, produto_id)`.
- A avaliação pode ser **editada**, e a nova versão substitui a anterior.
- A avaliação pode ser **excluída** fisicamente, junto com seus motivos, em uma única transação.
- Não há histórico de versões no MVP.

## Consequências

- ➕ Um voto por pessoa: os indicadores não são inflados por repetição.
- ➕ A memória mostra sempre a opinião mais recente, que é a relevante para a próxima compra.
- ➖ Perde-se a evolução da opinião ("era bom, piorou depois da nova fórmula"). Candidato a evolução.
- ➖ Uma segunda tentativa de criar avaliação retorna `409 review_already_exists` com o ID existente. A interface deve levar à edição.

## Rastreabilidade

RF08–RF10 · RN15, RN25, RN28 · UC08–UC10 · T18, T20–T22 · constraint `uq_avaliacoes_usuario_produto`
