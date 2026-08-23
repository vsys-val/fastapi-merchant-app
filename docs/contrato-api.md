# Contrato da API

> Documento vivo. Este contrato será completado antes da implementação.

## Convenções gerais

- A API troca dados em JSON.
- Endpoints de consulta de produtos e avaliações são públicos.
- Quando um token opcional for enviado, ele deve ser válido; token inválido ou expirado retorna `401 Unauthorized`.
- Operações de criação, alteração e exclusão exigem autenticação.
- Erros de validação retornam `422 Unprocessable Content`.
- Recursos específicos inexistentes retornam `404 Not Found`.
- Respostas paginadas usam 20 itens por padrão e aceitam no máximo 100.
- Avaliações em listas aparecem da mais recente para a mais antiga.

## Códigos HTTP adotados

| Código | Significado no projeto |
|---|---|
| `200 OK` | Consulta ou atualização concluída com corpo na resposta |
| `201 Created` | Novo recurso criado |
| `204 No Content` | Exclusão concluída sem corpo na resposta |
| `401 Unauthorized` | Token ausente, inválido ou expirado; ou credenciais de login incorretas |
| `403 Forbidden` | Usuário autenticado sem permissão para a operação |
| `404 Not Found` | Recurso específico não encontrado |
| `409 Conflict` | Dados válidos conflitam com um recurso existente |
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

## Operações ainda a detalhar

- `POST /products`
- `PATCH /products/{product_id}`
- `POST /products/{product_id}/reviews`
- `PATCH /reviews/{review_id}`
- `DELETE /reviews/{review_id}`
