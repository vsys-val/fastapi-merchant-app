# Casos de uso do MVP

## Objetivo

Este documento descreve como os atores interagem com a API para alcançar objetivos do produto. Ele complementa os requisitos de `docs/requisitos.md` e será ampliado de forma incremental durante a modelagem.

## Convenções

- **Pré-condição:** estado que deve ser verdadeiro antes do caso de uso.
- **Fluxo principal:** caminho esperado quando tudo ocorre corretamente.
- **Fluxo alternativo:** outro caminho válido que ainda conclui o objetivo.
- **Fluxo de exceção:** situação que impede a conclusão do objetivo.
- **Pós-condição:** estado garantido depois de uma conclusão bem-sucedida.

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
