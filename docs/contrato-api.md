# Contrato da API

> Documento vivo. Este contrato será completado antes da implementação.

## Convenções gerais

- A API troca dados em JSON.
- Valores técnicos controlados são escritos em inglês e a interface é responsável pela tradução.
- Datas públicas usam ISO 8601 em UTC, por exemplo `2026-08-25T08:30:00Z`.
- Endpoints de consulta de produtos e avaliações são públicos.
- Quando um token opcional for enviado, ele deve ser válido; token inválido ou expirado retorna `401 Unauthorized`.
- Operações de criação, alteração e exclusão exigem autenticação.
- Erros de validação retornam `422 Unprocessable Content`.
- Recursos específicos inexistentes retornam `404 Not Found`.
- Respostas paginadas usam 20 itens por padrão e aceitam no máximo 100.
- Avaliações em listas aparecem da mais recente para a mais antiga.
- Operações compostas são atômicas: ou todos os dados são salvos, ou nenhum é.

## Códigos HTTP adotados

| Código | Significado no projeto |
|---|---|
| `200 OK` | Consulta ou atualização concluída com corpo na resposta |
| `201 Created` | Novo recurso criado |
| `204 No Content` | Exclusão concluída sem corpo na resposta |
| `401 Unauthorized` | Token ausente, inválido ou expirado; ou credenciais de login incorretas |
| `403 Forbidden` | Usuário autenticado sem permissão para a operação |
| `404 Not Found` | Recurso específico não encontrado |
| `409 Conflict` | Dados válidos conflitam com um recurso ou com seu estado atual |
| `422 Unprocessable Content` | Dados ou parâmetros não passaram pela validação |
| `500 Internal Server Error` | Falha inesperada do servidor |

## Formato de paginação

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Uma pesquisa sem resultados retorna `200 OK`, com `items` vazio.

## Contas e autenticação

### Criar conta

`POST /users`

Dados de entrada:

```json
{
  "email": "valerio@example.com",
  "name": "Valério",
  "password": "senha-segura"
}
```

A senha e seu hash nunca aparecem na resposta.

Respostas:

- `201 Created`: conta criada;
- `409 Conflict`: e-mail já cadastrado;
- `422 Unprocessable Content`: e-mail, senha ou outro campo inválido.

### Fazer login

`POST /auth/login`

Dados de entrada:

```json
{
  "email": "valerio@example.com",
  "password": "senha-segura"
}
```

Resposta de sucesso — `200 OK`:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

Respostas:

- `200 OK`: autenticação concluída;
- `401 Unauthorized`: e-mail ou senha inválidos;
- `422 Unprocessable Content`: formato dos dados inválido.

A falha de autenticação usa a mensagem genérica “E-mail ou senha inválidos”, sem revelar se o e-mail está cadastrado.

## Produtos

### Representação pública

Campos públicos:

- `id`;
- `name`;
- `brand`;
- `variant`, opcional;
- `quantity`;
- `unit`;
- `category`;
- `barcode`, opcional.

A chave de identidade e o ID do criador são internos.

Valores de entrada aceitos para unidade: `g`, `kg`, `ml`, `L` e `un`. A API normaliza e sempre responde com:

- massa em `g`;
- volume em `ml`;
- contagem em `un`.

Exemplos: `1.5 L` vira `1500 ml` e `2 kg` vira `2000 g`.

Categorias:

- `food`;
- `beverages`;
- `cleaning`;
- `personal_hygiene`;
- `household_utilities`;
- `other`.

### Pesquisar produtos

`GET /products`

Parâmetros:

| Parâmetro | Regra |
|---|---|
| `name` | correspondência parcial por nome |
| `brand` | correspondência parcial por marca |
| `barcode` | correspondência exata |
| `page` | página, iniciando em 1 |
| `page_size` | 20 por padrão; máximo de 100 |

Regras:

- `name` e `brand` podem ser combinados e usam lógica E (`AND`);
- `barcode` não pode ser combinado com `name` ou `brand`;
- combinações inválidas e limites de paginação inválidos retornam `422`.

Exemplos:

```http
GET /products?name=sorvete
GET /products?brand=kibon
GET /products?name=sorvete&brand=kibon
GET /products?barcode=7891234567890
```

Respostas:

- `200 OK`: página de resultados, inclusive quando vazia;
- `422 Unprocessable Content`: parâmetros inválidos.

### Consultar produto específico

`GET /products/{product_id}`

O token é opcional. A resposta contém:

- dados do produto;
- distribuição percentual das respostas da comunidade;
- quantidade total de avaliações consideradas;
- `your_review`, com a avaliação do usuário autenticado ou `null`.

Para um usuário autenticado, sua avaliação fica fora dos indicadores da comunidade. Para um visitante, todas as avaliações são consideradas.

Exemplo parcial:

```json
{
  "id": 42,
  "community_summary": {
    "total_reviews": 10,
    "repurchase_intent": {
      "yes": 60,
      "maybe": 30,
      "no": 10
    },
    "quality": {
      "high": 50,
      "adequate": 40,
      "low": 10
    }
  },
  "your_review": null
}
```

Respostas:

- `200 OK`: produto encontrado;
- `401 Unauthorized`: token opcional enviado, mas inválido ou expirado;
- `404 Not Found`: produto inexistente.

### Listar avaliações comunitárias

`GET /products/{product_id}/reviews`

- resposta paginada;
- ordenação da mais recente para a mais antiga;
- exibe o nome público do autor, nunca seu e-mail ou ID interno;
- para usuário autenticado, exclui a própria avaliação;
- para visitante, inclui todas as avaliações.

Respostas:

- `200 OK`: página de avaliações, inclusive quando vazia;
- `401 Unauthorized`: token opcional enviado, mas inválido ou expirado;
- `404 Not Found`: produto inexistente;
- `422 Unprocessable Content`: paginação inválida.

### Cadastrar produto

`POST /products`

Exige autenticação.

Dados de entrada:

```json
{
  "name": "Sorvete de baunilha",
  "brand": "Marca X",
  "variant": "Baunilha",
  "quantity": 1.5,
  "unit": "L",
  "category": "food",
  "barcode": null
}
```

`name`, `brand`, `quantity`, `unit` e `category` são obrigatórios. `variant` e `barcode` são opcionais.

O sucesso retorna `201 Created` com todos os dados públicos do produto normalizados.

Quando o produto já existe, a resposta `409 Conflict` inclui uma referência ao registro canônico:

```json
{
  "detail": "Este produto já está cadastrado.",
  "existing_product_id": 42
}
```

Respostas:

- `201 Created`: produto criado;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `409 Conflict`: produto duplicado;
- `422 Unprocessable Content`: dados inválidos.

### Editar produto

`PATCH /products/{product_id}`

Exige autenticação. Apenas o criador pode editar, e somente enquanto nenhuma outra pessoa tiver avaliado o produto.

Regras do corpo parcial:

- campo ausente: mantém o valor atual;
- `null` em `variant` ou `barcode`: remove o valor;
- `null` em campo obrigatório: rejeita com `422`;
- uma edição que gere duplicidade é rejeitada e mantém o registro anterior;
- o sucesso retorna `200 OK` com a representação pública completa e normalizada.

Respostas:

- `200 OK`: produto atualizado;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `403 Forbidden`: usuário autenticado não é o criador;
- `404 Not Found`: produto inexistente;
- `409 Conflict`: produto bloqueado pelo uso comunitário ou edição geraria duplicidade;
- `422 Unprocessable Content`: dados inválidos.

## Avaliações

### Valores controlados

Intenção de recompra:

- `yes`;
- `maybe`;
- `no`.

Qualidade:

- `low`;
- `adequate`;
- `high`.

Atendimento à expectativa:

- `not_met`;
- `met`;
- `exceeded`.

Custo-benefício:

- `poor`;
- `fair`;
- `good`.

Percepção de um motivo:

- `positive`;
- `negative`.

Aspectos:

- `taste`;
- `fragrance`;
- `texture_consistency`;
- `effectiveness_performance`;
- `quantity_yield`;
- `ease_of_use_preparation`;
- `packaging`;
- `durability_preservation`;
- `composition_ingredients`;
- `safety_tolerance`;
- `price`;
- `other`.

### Cadastrar avaliação

`POST /products/{product_id}/reviews`

Exige autenticação.

Exemplo de entrada:

```json
{
  "repurchase_intent": "yes",
  "quality": "high",
  "expectation": "met",
  "value_for_money": "good",
  "reasons": [
    {
      "aspect": "taste",
      "perception": "positive"
    }
  ],
  "comment": "Compraria novamente."
}
```

Regras:

- todos os critérios universais são obrigatórios;
- deve existir pelo menos um motivo;
- o mesmo aspecto não pode aparecer mais de uma vez;
- `other` exige comentário não vazio;
- `comment` é opcional, exceto na regra anterior, e aceita até 1.000 caracteres;
- avaliação e motivos são validados e salvos em uma única transação;
- cada usuário pode ter somente uma avaliação por produto.

O sucesso retorna `201 Created` com a avaliação completa, incluindo `id`, `created_at` e `updated_at`.

Respostas:

- `201 Created`: avaliação criada;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `404 Not Found`: produto inexistente;
- `409 Conflict`: usuário já avaliou o produto;
- `422 Unprocessable Content`: avaliação ou algum motivo inválido.

### Editar avaliação

`PATCH /reviews/{review_id}`

Exige autenticação. Apenas o autor pode editar.

Regras:

- campos ausentes mantêm os valores atuais;
- se `reasons` for enviado, substitui toda a lista;
- `reasons: []` é inválido;
- a avaliação resultante deve obedecer a todas as regras de uma avaliação nova;
- se qualquer validação falhar, a avaliação anterior é mantida;
- o sucesso retorna `200 OK` com a avaliação completa atualizada;
- `created_at` permanece igual e `updated_at` é atualizado.

Respostas:

- `200 OK`: avaliação atualizada;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `403 Forbidden`: usuário autenticado não é o autor;
- `404 Not Found`: avaliação inexistente;
- `422 Unprocessable Content`: avaliação resultante inválida.

### Excluir avaliação

`DELETE /reviews/{review_id}`

Exige autenticação. Apenas o autor pode excluir. A avaliação e seus motivos são removidos fisicamente.

Respostas:

- `204 No Content`: exclusão concluída, sem corpo;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `403 Forbidden`: usuário autenticado não é o autor;
- `404 Not Found`: avaliação inexistente, inclusive após ela já ter sido excluída.
