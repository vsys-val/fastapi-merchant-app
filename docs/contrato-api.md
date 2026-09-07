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
| `429 Too Many Requests` | Limite temporário de requisições excedido |
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
  "password": "uma senha longa e memorável"
}
```

A senha e seu hash nunca aparecem na resposta.

Regras da conta:

- o e-mail é normalizado com remoção de espaços nas extremidades e conversão para minúsculas;
- e-mails que diferem apenas por maiúsculas, minúsculas ou espaços nas extremidades representam a mesma conta;
- a senha deve possuir entre 15 e 128 caracteres;
- espaços e diferentes tipos de caractere são aceitos, sem composição obrigatória;
- senhas presentes na lista local de senhas muito comuns são rejeitadas;
- a senha é armazenada somente como hash Argon2id;
- o salt exclusivo é gerado e administrado automaticamente pela biblioteca;
- a senha original nunca é armazenada nem pode ser recuperada a partir do hash.

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
  "token_type": "bearer",
  "expires_in": 86400
}
```

Respostas:

- `200 OK`: autenticação concluída;
- `401 Unauthorized`: e-mail ou senha inválidos;
- `422 Unprocessable Content`: formato dos dados inválido.

A falha de autenticação usa a mensagem genérica “E-mail ou senha inválidos”, sem revelar se o e-mail está cadastrado.

Proteção contra tentativas automatizadas:

- máximo de 5 tentativas malsucedidas por conta em uma janela de 15 minutos;
- máximo de 20 tentativas por endereço IP em uma janela de 1 minuto;
- o bloqueio é sempre temporário;
- limite excedido retorna `429 Too Many Requests`;
- login bem-sucedido zera o contador associado à conta;
- as respostas permanecem genéricas e não revelam se o e-mail existe.

### Token de acesso

- formato JWT;
- assinatura `HS256`;
- chave secreta forte fornecida por variável de ambiente e nunca versionada no código;
- validade de 24 horas;
- conteúdo mínimo: `sub` com o ID do usuário, `iat` com o instante de emissão e `exp` com a expiração;
- nome, e-mail, senha e outros dados privados não são incluídos;
- não há refresh token nem revogação antecipada no MVP;
- logout é realizado no cliente pela remoção do token, sem endpoint na API.

### Consultar a própria conta

`GET /users/me`

Exige autenticação.

Resposta de sucesso — `200 OK`:

```json
{
  "id": 42,
  "name": "Valério",
  "email": "valerio@example.com"
}
```

Respostas:

- `200 OK`: conta autenticada encontrada;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada.

No MVP, a conta é imutável após o cadastro. Não existem endpoints para alteração de nome, e-mail ou senha.

### Listar as próprias avaliações

`GET /users/me/reviews`

Exige autenticação.

Regras:

- resposta paginada, com 20 itens por padrão e máximo de 100;
- avaliações ordenadas da mais recente para a mais antiga;
- cada item contém a avaliação completa e um resumo do produto associado;
- usuário sem avaliações recebe `200 OK` com `items: []`.

Respostas:

- `200 OK`: página de avaliações do usuário;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `422 Unprocessable Content`: paginação inválida.

### Listar os próprios produtos

`GET /users/me/products`

Exige autenticação.

Regras:

- resposta paginada, com 20 itens por padrão e máximo de 100;
- produtos ordenados do cadastro mais recente para o mais antigo;
- retorna somente produtos ativos cadastrados pelo usuário;
- produtos logicamente excluídos não aparecem;
- usuário sem produtos ativos recebe `200 OK` com `items: []`.

Respostas:

- `200 OK`: página de produtos do usuário;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `422 Unprocessable Content`: paginação inválida.

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

### Limites e normalização de texto

- nome público da conta: de 2 a 100 caracteres;
- nome do produto: de 2 a 120 caracteres;
- marca: de 1 a 80 caracteres;
- variante: até 80 caracteres;
- comentário de avaliação: até 1.000 caracteres.

Os textos aceitam Unicode, inclusive letras acentuadas e nomes como `Açaí`, `Pão de Açúcar` e `Ypê`. Espaços nas extremidades são removidos antes da validação, e valores formados apenas por espaços são inválidos.

### Código de barras e GTIN

`barcode` é opcional e, quando informado, representa o número codificado pelas barras da embalagem. A API armazena o número como texto, não a imagem das barras, para preservar zeros à esquerda.

São aceitos somente:

- GTIN-8;
- GTIN-12;
- GTIN-13;
- GTIN-14.

Regras de validação:

- deve conter somente algarismos;
- deve possuir 8, 12, 13 ou 14 dígitos;
- o dígito verificador deve ser matematicamente válido segundo o algoritmo do GTIN;
- o GTIN deve ser único no catálogo;
- não há exigência de prefixo `789` ou `790`, pois produtos importados vendidos no Brasil podem usar outros prefixos.

A validação do dígito verificador confirma apenas a consistência estrutural do número. Ela não comprova que o produto existe, que foi cadastrado oficialmente na GS1 ou que nome, marca e quantidade informados correspondem ao GTIN.

Códigos internos de supermercados e etiquetas locais não são tratados como identificadores globais, pois o mesmo número pode representar produtos diferentes em estabelecimentos distintos. Se o produto não possuir um GTIN válido, o cliente deve enviar `barcode: null`. Nesse caso, a prevenção de duplicidade usa a chave de identidade interna formada pelos dados normalizados do produto.

Resultados relacionados:

- formato ou dígito verificador inválido: `422 Unprocessable Content`;
- GTIN já associado a um produto: `409 Conflict`, incluindo `existing_product_id`;
- GTIN válido e ainda não utilizado: o cadastro pode prosseguir.

Categorias:

- `food`;
- `beverages`;
- `cleaning`;
- `personal_hygiene`;
- `household_utilities`;
- `other`.

### Pesquisar e explorar produtos

`GET /products`

Parâmetros:

| Parâmetro | Regra |
|---|---|
| `name` | correspondência parcial; mínimo de 2 caracteres |
| `brand` | correspondência parcial; mínimo de 2 caracteres |
| `category` | uma categoria controlada por consulta |
| `barcode` | correspondência exata |
| `page` | página, iniciando em 1 |
| `page_size` | 20 por padrão; máximo de 100 |

Regras:

- sem filtros, retorna o catálogo ativo completo e paginado;
- `name`, `brand` e `category` podem ser combinados e usam lógica E (`AND`);
- apenas uma categoria pode ser enviada por consulta;
- buscas por nome e marca ignoram diferenças entre maiúsculas, minúsculas e acentos;
- a normalização é usada somente para comparação, preservando o texto original na resposta;
- `barcode` não pode ser combinado com nenhum outro filtro;
- produtos logicamente excluídos nunca aparecem;
- resultados são ordenados por nome, depois por marca e finalmente por `id`;
- combinações inválidas, valores controlados inválidos e limites de paginação inválidos retornam `422`.

Exemplos:

```http
GET /products
GET /products?name=sorvete
GET /products?brand=kibon
GET /products?category=food
GET /products?name=arroz&category=food
GET /products?name=sorvete&brand=kibon
GET /products?barcode=7891234567890
```

Formato resumido de cada item:

```json
{
  "id": 42,
  "name": "Café torrado e moído",
  "brand": "Marca X",
  "variant": null,
  "quantity": 500,
  "unit": "g",
  "category": "food",
  "barcode": "7891234567895",
  "community_summary": {
    "total_reviews": 3,
    "repurchase_intent": {
      "yes": 33.3,
      "maybe": 33.3,
      "no": 33.3
    }
  },
  "your_repurchase_intent": null
}
```

Regras do resumo:

- o token é opcional;
- a avaliação do usuário autenticado não entra no resumo comunitário;
- `your_repurchase_intent` sempre existe e vale `null` para visitantes ou usuários que ainda não avaliaram o produto;
- sem avaliações comunitárias, `total_reviews` vale `0` e todas as porcentagens valem `0`;
- as porcentagens possuem uma casa decimal;
- por arredondamento, a soma pode resultar em `99.9` ou `100.1`; nenhuma categoria é ajustada artificialmente;
- comentários, motivos e demais critérios ficam restritos ao detalhe do produto e aos endpoints de avaliações.

Respostas:

- `200 OK`: página de resultados, inclusive quando vazia;
- `401 Unauthorized`: token opcional enviado, mas inválido ou expirado;
- `422 Unprocessable Content`: parâmetros inválidos.

### Consultar produto específico

`GET /products/{product_id}`

O token é opcional. A resposta contém:

- dados do produto;
- distribuição percentual das respostas da comunidade, com uma casa decimal e sem ajuste artificial de arredondamento;
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

### Excluir produto

`DELETE /products/{product_id}`

Exige autenticação. Apenas o criador pode solicitar a exclusão.

Regras:

- a exclusão é lógica e registra `deleted_at` em UTC;
- o produto somente pode ser excluído quando não possuir nenhuma avaliação, inclusive do próprio criador;
- se houver avaliação do criador, ele deve excluí-la explicitamente antes;
- avaliações de terceiros impedem a exclusão pelo criador;
- nenhuma avaliação é removida automaticamente;
- produtos excluídos não aparecem em pesquisas ou listagens;
- a consulta direta de um produto excluído retorna `404 Not Found`;
- não existe restauração explícita pelo usuário no MVP;
- o sucesso retorna `204 No Content`, sem corpo.

Respostas:

- `204 No Content`: exclusão lógica concluída;
- `401 Unauthorized`: autenticação ausente, inválida ou expirada;
- `403 Forbidden`: usuário autenticado não é o criador;
- `404 Not Found`: produto inexistente ou já excluído;
- `409 Conflict`: o produto possui uma ou mais avaliações.

### Recadastrar produto excluído

Se `POST /products` corresponder, por GTIN ou chave de identidade, a um produto logicamente excluído e sem avaliações:

- o registro anterior é reativado com `deleted_at: null`;
- o mesmo ID é preservado;
- os dados válidos e normalizados recebidos passam a representar o produto;
- o usuário autenticado que realizou o recadastro torna-se o responsável por futuras edições e exclusão;
- a resposta é `200 OK` com a representação pública completa;
- um novo registro não é criado.

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
