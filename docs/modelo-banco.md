# Modelo relacional do MVP

## Decisões técnicas

- Banco de dados: SQLite.
- Identificadores: inteiros autoincrementais.
- Listas fixas: enumerações na aplicação e restrições `CHECK` no banco, sem tabelas de referência.
- Avaliações e motivos usam exclusão física.
- Produtos e contas não possuem exclusão no escopo inicial.
- Indicadores comunitários são calculados sob demanda e não são armazenados.
- Quantidades equivalentes são normalizadas para unidades-base antes da geração da chave de identidade:
  - massa em `g`;
  - volume em `ml`;
  - itens contáveis em `unidade`.

## Tabela `usuarios`

| Coluna | Tipo conceitual | Nulo | Regras |
|---|---|---:|---|
| `id` | INTEGER | não | chave primária autoincremental |
| `nome_publico` | TEXT | não | pode se repetir |
| `email` | TEXT | não | único e normalizado antes de salvar |
| `senha_hash` | TEXT | não | nunca armazenar a senha original |

## Tabela `produtos`

| Coluna | Tipo conceitual | Nulo | Regras |
|---|---|---:|---|
| `id` | INTEGER | não | chave primária autoincremental |
| `criador_id` | INTEGER | não | chave estrangeira para `usuarios.id` |
| `nome` | TEXT | não | entrada exibida ao usuário |
| `marca` | TEXT | não | entrada exibida ao usuário |
| `variante` | TEXT | sim | sabor, fragrância ou outra versão |
| `quantidade` | NUMERIC | não | valor normalizado |
| `unidade` | TEXT | não | `g`, `ml` ou `unidade` após normalização |
| `categoria` | TEXT | não | valor controlado |
| `codigo_barras` | TEXT | sim | único quando informado |
| `chave_identidade` | TEXT | não | única; gerada a partir dos dados normalizados |

A `chave_identidade` combina nome, marca, variante, quantidade e unidade após normalização. Exemplo:

```text
ype|desinfetante|capim-limao|1500|ml
```

O código de barras continua sendo uma verificação independente e exata.

## Tabela `avaliacoes`

| Coluna | Tipo conceitual | Nulo | Regras |
|---|---|---:|---|
| `id` | INTEGER | não | chave primária autoincremental |
| `usuario_id` | INTEGER | não | chave estrangeira para `usuarios.id` |
| `produto_id` | INTEGER | não | chave estrangeira para `produtos.id` |
| `intencao_recompra` | TEXT | não | valor controlado |
| `qualidade` | TEXT | não | valor controlado |
| `expectativa` | TEXT | não | valor controlado |
| `custo_beneficio` | TEXT | não | valor controlado |
| `comentario` | TEXT | sim | obrigatório quando houver aspecto `OUTRO` |
| `criado_em` | DATETIME | não | data de criação |
| `atualizado_em` | DATETIME | não | data da última atualização |

Restrição composta:

```text
UNIQUE(usuario_id, produto_id)
```

Ela garante uma única avaliação atual por usuário e produto.

## Tabela `motivos_avaliacao`

| Coluna | Tipo conceitual | Nulo | Regras |
|---|---|---:|---|
| `id` | INTEGER | não | chave primária autoincremental |
| `avaliacao_id` | INTEGER | não | chave estrangeira para `avaliacoes.id` com exclusão em cascata |
| `aspecto` | TEXT | não | valor controlado |
| `percepcao` | TEXT | não | `POSITIVA` ou `NEGATIVA` |

Restrição composta:

```text
UNIQUE(avaliacao_id, aspecto)
```

Ela impede repetir o mesmo aspecto dentro da avaliação.

## Integridade entre tabelas

| Origem | Destino | Regra de exclusão |
|---|---|---|
| `produtos.criador_id` | `usuarios.id` | restringir |
| `avaliacoes.usuario_id` | `usuarios.id` | restringir |
| `avaliacoes.produto_id` | `produtos.id` | restringir |
| `motivos_avaliacao.avaliacao_id` | `avaliacoes.id` | excluir em cascata |

A exclusão em cascata é usada somente entre avaliação e motivos. A exclusão de contas e produtos está fora do MVP.

## Regras validadas pela aplicação

Algumas regras atravessam múltiplos registros e serão validadas pela API dentro de uma transação:

- toda avaliação deve possuir pelo menos um motivo;
- o aspecto `OUTRO` exige comentário;
- somente o autor pode editar ou excluir a avaliação;
- somente o criador pode editar um produto;
- o produto fica bloqueado quando outro usuário o avalia;
- avaliação e motivos devem ser salvos ou atualizados integralmente, nunca parcialmente.

## Índices iniciais

Além dos índices criados pelas chaves e restrições únicas:

- índice em `produtos.nome`;
- índice em `produtos.marca`;
- índice em `avaliacoes.produto_id`;
- índice em `avaliacoes.usuario_id`;
- índice em `motivos_avaliacao.avaliacao_id`.
