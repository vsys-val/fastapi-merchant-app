# Casos de uso do MVP

## Objetivo

Este documento descreve como os atores interagem com a API para alcançar objetivos do produto. Ele complementa os requisitos de `docs/requisitos.md` e será ampliado de forma incremental durante a modelagem.

## Convenções

- **Pré-condição:** estado que deve ser verdadeiro antes do caso de uso.
- **Fluxo principal:** caminho esperado quando tudo ocorre corretamente.
- **Fluxo alternativo:** outro caminho válido que ainda conclui o objetivo.
- **Fluxo de exceção:** situação que impede a conclusão do objetivo.
- **Pós-condição:** estado garantido depois de uma conclusão bem-sucedida.

## UC01 — Cadastrar conta

### Objetivo

Permitir que um visitante crie uma conta para acessar as operações protegidas da API.

### Ator principal

**Visitante.**

### Gatilho

O visitante decide criar uma conta.

### Requisitos e regras relacionados

- **RF01:** cadastrar uma conta com nome público, e-mail e senha;
- **RN01:** cada usuário possui um identificador interno único;
- **RN02:** o nome público pode se repetir;
- **RN03:** o e-mail deve ser único e privado;
- **RNF01:** a senha deve ser armazenada somente como hash seguro.

### Pré-condições

1. O e-mail informado ainda não pertence a outra conta.
2. O visitante possui nome público, e-mail e senha para enviar.

### Fluxo principal

1. O visitante informa nome público, e-mail e senha.
2. O visitante envia os dados de cadastro.
3. A API valida os campos obrigatórios, o formato do e-mail e a política da senha.
4. A API verifica que o e-mail ainda não está cadastrado.
5. A API produz um hash seguro da senha.
6. O sistema gera um identificador único e salva a conta.
7. A API confirma o sucesso da operação sem devolver a senha nem seu hash.

### Fluxos de exceção

**E1 — Dados obrigatórios ausentes**

1. A API identifica um campo obrigatório ausente.
2. A operação é rejeitada e nenhuma conta é salva.
3. A API indica o campo que deve ser preenchido.

**E2 — Formato de e-mail inválido**

1. A API identifica que o e-mail não possui formato válido.
2. A operação é rejeitada e nenhuma conta é salva.
3. A API associa uma mensagem clara de validação ao campo `email`.

**E3 — E-mail já cadastrado**

1. A API encontra uma conta associada ao e-mail.
2. A operação é rejeitada para preservar a unicidade do e-mail.
3. A API informa que não foi possível criar outra conta com esse e-mail.

**E4 — Senha fora da política**

1. A API identifica que a senha não atende à política de segurança.
2. A operação é rejeitada e nenhuma conta é salva.
3. A API informa quais critérios da senha não foram atendidos.

### Pós-condição de sucesso

Uma nova conta fica armazenada com identificador único, nome público, e-mail único e hash da senha. A senha original não é armazenada nem devolvida.

## UC02 — Realizar login

### Objetivo

Permitir que uma pessoa com conta válida se autentique e receba um token temporário para acessar operações protegidas.

### Ator principal

**Visitante com conta cadastrada.**

### Gatilho

O visitante decide entrar na aplicação.

### Requisitos e regras relacionados

- **RF02:** autenticar por e-mail e senha e fornecer um token de acesso;
- **RN04:** operações que alteram dados exigem autenticação;
- **RNF01:** senhas são verificadas por meio de hash seguro;
- **RNF02:** senha, hash e token não devem aparecer em respostas públicas.

### Pré-condições

1. O visitante possui uma conta cadastrada.
2. A conta contém um e-mail único e um hash de senha válido.

### Fluxo principal

1. O visitante informa e-mail e senha.
2. O visitante envia as credenciais.
3. A API localiza a conta pelo e-mail.
4. A API usa uma função segura para verificar a senha recebida contra o hash armazenado.
5. A API gera um token de acesso temporário associado à identidade do usuário.
6. A API devolve o token e seu tipo, sem devolver a senha nem o hash.
7. Nas requisições protegidas seguintes, o cliente envia o token para que a API identifique o usuário.

### Fluxos de exceção

**E1 — Credenciais ausentes ou inválidas**

1. A API identifica que o e-mail ou a senha não foi informado corretamente.
2. A autenticação é rejeitada e nenhum token é emitido.
3. A API retorna uma mensagem genérica de credenciais inválidas.

**E2 — E-mail inexistente ou senha incorreta**

1. A API não localiza a conta ou a verificação da senha falha.
2. A autenticação é rejeitada e nenhum token é emitido.
3. A API retorna “E-mail ou senha inválidos”, sem revelar qual credencial falhou.

### Expiração do token

O token de acesso não é permanente. Depois de expirar, deixa de autorizar requisições protegidas e o usuário precisa realizar login novamente. O uso de `refresh token` fica fora do MVP.

### Pós-condição de sucesso

O usuário possui um token de acesso válido por tempo limitado e pode apresentá-lo nas operações protegidas da API.

## UC04 — Pesquisar produto

### Objetivo

Permitir que um visitante ou usuário autenticado encontre produtos do catálogo por nome, marca ou código de barras.

### Atores

- **Visitante.**
- **Usuário autenticado.**

### Gatilho

O ator deseja localizar um produto no catálogo.

### Requisitos e regras relacionados

- **RF03:** permitir a consulta pública de produtos;
- **RF04:** pesquisar por nome, marca ou código de barras;
- **RN14:** nome e marca usam correspondência parcial; código de barras usa correspondência exata.

### Pré-condições

Nenhuma autenticação é necessária.

### Fluxo principal

1. O ator informa um nome, uma marca ou um código de barras.
2. O ator envia a pesquisa.
3. A API identifica o tipo de pesquisa recebido.
4. Para nome ou marca, a API procura correspondências parciais.
5. Para código de barras, a API procura uma correspondência exata.
6. A API devolve uma lista contendo zero ou mais produtos encontrados.

### Fluxos alternativos

**A1 — Pesquisa por nome ou marca**

1. A API realiza uma busca textual por correspondência parcial.
2. O caso de uso continua no passo 6 do fluxo principal.

**A2 — Pesquisa por código de barras**

1. A API realiza uma busca por correspondência exata.
2. O caso de uso continua no passo 6 do fluxo principal.

### Resultado sem correspondências

A ausência de produtos compatíveis não é um erro. A API conclui a operação com sucesso e devolve uma lista vazia.

### Pós-condição de sucesso

Nenhum dado é alterado. O ator recebe uma lista com zero ou mais produtos compatíveis com a pesquisa.

## UC05 — Consultar detalhes de um produto

### Objetivo

Permitir que um visitante ou usuário autenticado consulte os dados de um produto, suas avaliações públicas e seus indicadores comunitários, com personalização quando houver autenticação válida.

### Atores

- **Visitante.**
- **Usuário autenticado.**

### Gatilho

O ator deseja consultar um produto específico do catálogo.

### Requisitos e regras relacionados

- **RF03:** permitir a consulta pública de produtos;
- **RF05:** retornar dados do produto, informações comunitárias e a avaliação pessoal separadamente;
- **RF11:** consultar avaliações comunitárias;
- **RF12:** fornecer indicadores comunitários;
- **RN26:** apresentar a avaliação pessoal separadamente;
- **RN27:** calcular os indicadores a partir das avaliações existentes.

### Pré-condições

Nenhuma autenticação é obrigatória. O ator deve informar o identificador do produto que deseja consultar.

### Fluxo principal

1. O ator solicita os detalhes de um produto pelo identificador.
2. Quando houver token, a API valida a autenticação e identifica o usuário.
3. A API procura o produto pelo identificador.
4. A API reúne os dados do produto.
5. A API consulta as avaliações públicas e calcula os indicadores comunitários atuais.
6. Quando houver usuário autenticado, a API procura sua avaliação para o produto.
7. A API devolve os dados do produto, as informações comunitárias e o campo `your_review`.
8. Se o usuário autenticado possuir uma avaliação, ela é devolvida separadamente em `your_review`.

### Fluxos alternativos

**A1 — Consulta sem token**

1. O visitante solicita os detalhes sem enviar token.
2. A API realiza a consulta pública.
3. O campo `your_review` é devolvido como `null`.

**A2 — Usuário autenticado sem avaliação pessoal**

1. A API valida o token, mas não encontra avaliação daquele usuário para o produto.
2. O campo `your_review` é devolvido como `null`.

### Fluxos de exceção

**E1 — Token enviado, mas inválido ou expirado**

1. A API identifica que o token apresentado não é válido.
2. A requisição é rejeitada, em vez de ser tratada silenciosamente como consulta de visitante.
3. A API informa que é necessário realizar uma nova autenticação.

**E2 — Produto inexistente**

1. A API não encontra o identificador solicitado.
2. A consulta do recurso específico não pode ser concluída.
3. A API informa que o produto não foi encontrado.

### Pós-condição de sucesso

Nenhum dado é alterado. O ator recebe os detalhes do produto e as informações comunitárias; quando aplicável, recebe também sua avaliação pessoal separadamente.

## UC06 — Cadastrar produto

### Objetivo

Permitir que um usuário autenticado acrescente ao catálogo compartilhado um produto que ainda não possui registro canônico.

### Ator principal

**Usuário autenticado.**

### Gatilho

O usuário não encontra no catálogo o produto que deseja consultar ou avaliar.

### Requisitos e regras relacionados

- **RF06:** cadastrar um produto ausente no catálogo;
- **RN05–RN08:** campos obrigatórios, opcionais e categoria controlada;
- **RN09:** código de barras único quando informado;
- **RN10–RN12:** catálogo canônico, prevenção e rejeição de duplicidade.

### Pré-condições

1. O usuário está autenticado com token válido.
2. O produto ainda não possui um registro canônico no catálogo.

### Fluxo principal

1. O usuário informa nome, marca, quantidade, unidade e categoria.
2. Opcionalmente, informa variante e código de barras.
3. O usuário envia os dados do produto.
4. A API identifica o usuário autenticado.
5. A API valida os campos obrigatórios, formatos, unidade e categoria.
6. Quando houver código de barras, a API procura uma correspondência exata.
7. A API também procura duplicidade pela combinação normalizada de nome, marca, variante, quantidade e unidade.
8. Não havendo duplicidade, a API cria o produto e registra seu criador.
9. A API confirma o sucesso e devolve o produto criado.

### Fluxo alternativo

**A1 — Produto sem código de barras ou variante**

1. O usuário omite um ou ambos os campos opcionais.
2. A API realiza a verificação de duplicidade com os dados de identificação disponíveis.
3. O caso de uso continua no passo 8 do fluxo principal.

### Fluxos de exceção

**E1 — Usuário não autenticado**

1. A API não identifica um token válido.
2. A operação é rejeitada e nenhum produto é criado.
3. A API informa que a autenticação é necessária.

**E2 — Dados obrigatórios ausentes ou inválidos**

1. A API identifica um campo obrigatório ausente ou um valor inválido.
2. A operação é rejeitada e nenhum produto é criado.
3. A API informa quais dados precisam ser corrigidos.

**E3 — Código de barras já utilizado**

1. A API encontra um produto com o mesmo código de barras.
2. A criação é rejeitada como conflito.
3. A API indica o produto canônico existente.

**E4 — Produto equivalente já existente**

1. A API encontra correspondência pela identidade normalizada do produto.
2. A criação é rejeitada como conflito.
3. A API indica o produto canônico existente para que o usuário possa consultá-lo ou avaliá-lo.

### Pós-condição de sucesso

Um novo produto canônico fica disponível no catálogo compartilhado e vinculado ao usuário que o cadastrou.

## UC07 — Editar produto

### Objetivo

Permitir que o criador corrija os dados de um produto sem comprometer avaliações de outros usuários.

### Ator principal

**Usuário autenticado que cadastrou o produto.**

### Gatilho

O criador identifica que os dados do produto precisam ser corrigidos.

### Requisitos e regras relacionados

- **RF07:** permitir a correção condicionada de um produto;
- **RN09–RN12:** preservar código de barras único e registro canônico;
- **RN13:** somente o criador pode editar enquanto nenhum outro usuário tiver avaliado o produto.

### Pré-condições

1. O usuário está autenticado.
2. O produto existe.
3. O usuário autenticado é o criador do produto.
4. Nenhum outro usuário avaliou o produto.

### Fluxo principal

1. O criador solicita a edição do produto.
2. O criador informa os dados que deseja corrigir.
3. A API identifica o usuário autenticado.
4. A API confirma que ele é o criador do produto.
5. A API verifica que nenhum outro usuário avaliou o produto.
6. A API valida os novos dados e repete as verificações de unicidade e duplicidade.
7. A API atualiza o produto.
8. A API confirma o sucesso e devolve os dados atualizados.

### Fluxo alternativo

**A1 — O criador já avaliou o produto**

1. A API encontra apenas uma avaliação feita pelo próprio criador.
2. A edição continua permitida, pois nenhum outro usuário é afetado.
3. O caso de uso continua no passo 6 do fluxo principal.

### Fluxos de exceção

**E1 — Usuário não autenticado**

1. A API não identifica um token válido.
2. A edição é rejeitada e o produto não é alterado.

**E2 — Produto inexistente**

1. A API não encontra o produto solicitado.
2. A edição é rejeitada e a API informa que o produto não foi encontrado.

**E3 — Usuário não é o criador**

1. A API identifica que o produto foi cadastrado por outro usuário.
2. A edição é rejeitada e o produto não é alterado.

**E4 — Produto avaliado por outro usuário**

1. A API encontra pelo menos uma avaliação cujo autor não é o criador do produto.
2. A edição é rejeitada e os dados originais são preservados.
3. A API informa que o produto está bloqueado devido ao uso comunitário.

**E5 — Novos dados inválidos ou duplicados**

1. A API detecta campos inválidos, código de barras já utilizado ou produto canônico equivalente.
2. A edição é rejeitada e os dados anteriores são preservados.
3. A API informa o conflito ou os campos que precisam ser corrigidos.

### Pós-condição de sucesso

O produto permanece com o mesmo identificador e passa a conter os dados corrigidos. Avaliações existentes do próprio criador continuam vinculadas a ele.

## UC08 — Cadastrar avaliação

### Objetivo

Permitir que um usuário autenticado registre sua experiência atual com um produto existente no catálogo.

### Ator principal

**Usuário autenticado.**

### Gatilho

O usuário decide avaliar um produto selecionado.

### Requisitos e regras relacionados

- **RF08:** criar uma avaliação de produto;
- **RN15:** no máximo uma avaliação atual por usuário e produto;
- **RN16–RN20:** intenção de recompra e três critérios obrigatórios com valores controlados;
- **RN21–RN24:** pelo menos um motivo estruturado e regras dos aspectos;
- **RN28:** somente a avaliação atual é mantida.

### Pré-condições

1. O usuário possui uma conta válida e está autenticado.
2. O produto que será avaliado já existe no catálogo.
3. O usuário ainda não possui uma avaliação para esse produto.

### Fluxo principal

1. O usuário seleciona o produto que deseja avaliar.
2. O usuário informa:
   - a intenção de recompra;
   - a qualidade percebida;
   - o atendimento às expectativas;
   - o custo-benefício;
   - pelo menos um motivo composto por aspecto e percepção;
   - um comentário, quando desejar.
3. O usuário envia a avaliação.
4. A API identifica o usuário autenticado.
5. A API valida os campos obrigatórios, os valores permitidos e os motivos.
6. A API verifica que ainda não existe uma avaliação desse usuário para o produto.
7. A API salva a avaliação vinculada ao identificador do usuário e ao identificador do produto.
8. A API confirma o sucesso da operação e devolve a avaliação criada.

### Fluxo alternativo

**A1 — Aspecto “outro”**

1. No passo 2 do fluxo principal, o usuário escolhe o aspecto `outro`.
2. O usuário fornece obrigatoriamente um comentário explicativo.
3. O caso de uso continua no passo 3 do fluxo principal.

### Fluxos de exceção

**E1 — Usuário não autenticado**

1. A API não consegue identificar um usuário autenticado.
2. A operação é rejeitada e nenhuma avaliação é salva.
3. A API informa que a autenticação é necessária.

**E2 — Produto inexistente**

1. A API não encontra o produto informado.
2. A operação é rejeitada e nenhuma avaliação é salva.
3. A API informa que o produto não existe no catálogo.

**E3 — Dados inválidos ou incompletos**

1. A API encontra um campo obrigatório ausente, um valor não permitido ou um motivo inválido.
2. A operação é rejeitada e nenhuma avaliação é salva, nem parcialmente.
3. A API informa quais dados precisam ser corrigidos.

**E4 — Avaliação já existente**

1. A API encontra uma avaliação do mesmo usuário para o mesmo produto.
2. A nova criação é rejeitada para preservar a unicidade da combinação usuário–produto.
3. A API informa o conflito; o usuário poderá usar o caso de uso de editar a própria avaliação.

### Pós-condição de sucesso

Uma avaliação válida fica armazenada e vinculada ao usuário e ao produto. Ela passa a compor as consultas e os indicadores comunitários daquele produto.
