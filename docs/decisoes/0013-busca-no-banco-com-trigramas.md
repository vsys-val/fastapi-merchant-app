# ADR-0013 — Busca no banco com trigramas e sugestões aproximadas

- Status: aceita
- Data: 2026-09-25
- Origem: item do [roadmap](../roadmap.md) e risco R3 da [visão de produto](../visao-produto.md#8-hipóteses-e-riscos)

## Contexto

`search_products` carregava todos os produtos ativos e filtrava, ordenava e paginava em Python. O custo crescia com o catálogo, não com o resultado. Medido com 50 mil produtos no PostgreSQL local, uma busca por nome levava **~970 ms**, acima do guarda-corpo de p95 < 800 ms da busca. Além disso, um erro de digitação ("arros", "detergnte") devolvia lista vazia, e a pessoa concluía que o produto não existia e o cadastrava de novo.

Restrições: os testes de serviço rodam em SQLite; a produção usa PostgreSQL 17 no Supabase, onde as extensões ficam no schema `extensions`, fora do `search_path` do papel da API.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Ignorar acentos no banco | `unaccent()` em cada consulta · coluna gerada com `unaccent` · **colunas normalizadas pela aplicação** | Colunas: `unaccent` não é `IMMUTABLE` (não serve para coluna gerada nem índice sem *wrapper*), e a mesma função Python já define a identidade do produto. O comportamento fica igual em SQLite e PostgreSQL |
| Busca parcial rápida | `LIKE '%termo%'` sem índice · busca textual (`tsvector`) · **`LIKE` + índice GIN de trigramas** | Trigramas: aceleram `LIKE` com curinga no início e não mudam a semântica de "contém" (RN14); `tsvector` trabalha com palavras inteiras e mudaria o resultado |
| Erro de digitação | Sempre misturar parecidos · **só quando não há resultado exato, com aviso** · não tratar | Só sem resultado: a busca exata continua previsível, e a sugestão aparece quando a alternativa seria uma tela vazia |
| Onde fica a extensão | `public` · **`extensions` quando existir, com `USAGE` ao papel da API** | Segue o padrão do Supabase (o advisor alerta para extensões em `public`); PostgreSQL comum usa `public` |

## Decisão

- `produtos` ganha `nome_busca` e `marca_busca`: sem acentos, minúsculas e espaços simples, mantidas por `@validates` no modelo e preenchidas pela migração `0008`.
- A busca exata filtra com `LIKE` escapado (`%` e `_` digitados são literais), conta, ordena por nome, marca e `id` e pagina **no banco**.
- Sem resultado exato para nome ou marca, a busca procura itens com `word_similarity ≥ 0,5` (operador `<%`, que usa o índice) e responde `approximate: true`, ordenando pela semelhança. Categoria continua obrigatória nessa etapa. Código de barras nunca é aproximado.
- A etapa aproximada roda num *savepoint*: em SQLite ou sem a extensão, a busca apenas não sugere nada.
- Buscas respondidas só com parecidos não contam como "busca com resultado" no painel ([ADR-0012](0012-painel-e-instrumentacao-propria.md)); têm indicador próprio.

## Consequências

- ➕ Com 50 mil produtos: busca exata em ~10 ms (antes ~970 ms); busca aproximada em ~30–55 ms.
- ➕ Erros de digitação comuns encontram o produto, o que reduz cadastros duplicados.
- ➕ SQLite continua servindo aos testes de serviço; a busca aproximada é coberta por testes no PostgreSQL do CI.
- ➖ Duas colunas derivadas a mais; o modelo é a única fonte que as atualiza. Escrita direta por SQL precisaria atualizá-las.
- ➖ O limiar 0,5 é uma escolha inicial: aceita "arros" → "arroz", recusa "ypioca" → "ypê". Deve ser recalibrado com o indicador de buscas só com parecidos.
- ➖ A extensão fica instalada mesmo após o *downgrade*, para não quebrar outros usos.

## Rastreabilidade

RF04 · RN14, RN42 · UC04 · US03 · T23–T25, T48 · `app/catalog.py::search_products`, `_approximate_matches`, migração `0008`
