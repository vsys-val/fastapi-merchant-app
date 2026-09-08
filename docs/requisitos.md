# Requisitos do MVP

## Objetivo

Este documento transforma as decisões de `docs/ideacao.md` em comportamentos esperados da API e regras de negócio verificáveis.

## Atores

- **Visitante:** pessoa sem autenticação.
- **Usuário autenticado:** pessoa identificada por um token válido.

## Requisitos funcionais

| ID | Requisito |
|---|---|
| RF01 | A API deve permitir o cadastro de uma conta com nome público, e-mail e senha. |
| RF02 | A API deve permitir autenticação por e-mail e senha e fornecer um token de acesso. |
| RF03 | A API deve permitir que visitantes e usuários autenticados consultem produtos. |
| RF04 | A API deve permitir pesquisar produtos por nome, marca, categoria ou código de barras. |
| RF05 | A API deve retornar os dados de um produto, as avaliações da comunidade e, quando houver usuário autenticado, sua própria avaliação separadamente. |
| RF06 | A API deve permitir que um usuário autenticado cadastre um produto ausente no catálogo. |
| RF07 | A API deve permitir que o criador corrija um produto enquanto nenhum outro usuário o tiver avaliado. |
| RF08 | A API deve permitir que um usuário autenticado crie sua avaliação de um produto. |
| RF09 | A API deve permitir que o autor edite a própria avaliação. |
| RF10 | A API deve permitir que o autor exclua a própria avaliação. |
| RF11 | A API deve permitir consultar as avaliações comunitárias de um produto. |
| RF12 | A API deve fornecer indicadores comunitários agregados por produto. |
| RF13 | O responsável pode excluir logicamente produto sem avaliações; recadastro pode reativar o mesmo registro. |
| RF14 | O usuário deve consultar sua conta, suas avaliações e seus produtos ativos em endpoints privados. |
| RF15 | A API deve disponibilizar verificação operacional de conexão com o banco em `/health`. |

## Regras de negócio

### Usuários e autenticação

| ID | Regra |
|---|---|
| RN01 | Cada usuário deve possuir um identificador interno único. |
| RN02 | O nome público pode se repetir entre usuários. |
| RN03 | O e-mail deve ser único e não pode ser exibido publicamente. |
| RN04 | Consultas ao catálogo são públicas; consultas pessoais e operações que alteram dados exigem autenticação, exceto cadastro de conta e login. |

### Produtos

| ID | Regra |
|---|---|
| RN05 | Todo produto deve possuir nome, marca, quantidade, unidade e categoria. |
| RN06 | A variante e o código de barras são opcionais. |
| RN07 | Cada produto deve pertencer a exatamente uma categoria principal. |
| RN08 | As categorias do MVP são: alimentos, bebidas, limpeza, higiene pessoal, utilidades domésticas e outros. |
| RN09 | Quando informado, o código de barras deve ser único. |
| RN10 | O catálogo deve manter um registro canônico compartilhado para cada produto. |
| RN11 | A API deve procurar duplicidade pelo código de barras ou pela combinação normalizada de nome, marca, variante, quantidade e unidade. |
| RN12 | Uma tentativa de cadastrar produto ativo duplicado deve retornar conflito e indicar o registro existente; produto excluído sem avaliações pode ser reativado com o mesmo ID e novo responsável. |
| RN13 | O criador pode editar os dados do produto somente enquanto nenhum outro usuário o tiver avaliado. |
| RN14 | Nome e marca devem aceitar pesquisa textual parcial; código de barras exige correspondência exata. |

### Avaliações

| ID | Regra |
|---|---|
| RN15 | Cada usuário pode manter no máximo uma avaliação atual por produto. |
| RN16 | A intenção de recompra é obrigatória e aceita: compraria novamente, talvez comprasse ou não compraria novamente. |
| RN17 | Qualidade percebida, atendimento às expectativas e custo-benefício são obrigatórios. |
| RN18 | Qualidade aceita: baixa, adequada ou alta. |
| RN19 | Expectativa aceita: não atendeu, atendeu ou superou. |
| RN20 | Custo-benefício aceita: ruim, justo ou bom. |
| RN21 | Toda avaliação deve possuir pelo menos um motivo estruturado como aspecto e percepção positiva ou negativa. |
| RN22 | Um aspecto não pode aparecer mais de uma vez na mesma avaliação. |
| RN23 | Os aspectos disponíveis são: sabor, cheiro ou fragrância, textura ou consistência, eficácia ou desempenho, quantidade ou rendimento, facilidade de uso ou preparo, embalagem, durabilidade ou conservação, composição ou ingredientes, segurança ou tolerância, preço e outro. |
| RN24 | O aspecto “outro” exige comentário explicativo. Nos demais casos, o comentário é opcional. |
| RN25 | Somente o autor pode editar ou excluir sua avaliação. |
| RN26 | A avaliação pessoal deve ser apresentada separadamente e excluída dos indicadores e listas comunitárias para seu autor; visitantes consideram todas. |
| RN27 | Os indicadores comunitários devem ser calculados a partir das avaliações existentes no momento da consulta. |
| RN28 | O MVP mantém apenas a avaliação atual e não armazena histórico de versões. |

## Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | As senhas devem ser protegidas por um algoritmo de hash apropriado para senhas e nunca armazenadas em texto puro. |
| RNF02 | Dados sensíveis, como e-mail, hash de senha e token de acesso, não devem aparecer em respostas públicas. |
| RNF03 | A API deve oferecer documentação interativa gerada a partir do contrato OpenAPI. |
| RNF04 | O repositório deve possuir instruções claras para instalar, executar e testar a aplicação. |
| RNF05 | Entradas inválidas devem produzir respostas de erro claras e códigos HTTP adequados. |
| RNF06 | As regras críticas de autenticação, unicidade e autorização devem possuir testes automatizados. |

## Fora do escopo inicial

- recuperação de senha por e-mail;
- critérios de avaliação específicos por categoria;
- histórico de avaliações;
- múltiplas categorias por produto;
- filtros avançados por variante ou múltiplas categorias;
- administração e mesclagem manual de produtos duplicados;
- interface web ou aplicativo móvel.

## Especificações consolidadas

O [contrato da API](contrato-api.md) detalha limites, valores técnicos em inglês, normalização, paginação e respostas de erro. A [matriz de testes](matriz-testes.md) torna essas regras verificáveis.

- Persistência em PostgreSQL; quantidades com decimal exato e datas com fuso horário.
- Senhas Argon2id, 15–128 caracteres, espaços preservados e bloqueio local de senhas comuns.
- JWT HS256 por 24 horas, segredo externo ao repositório, sem refresh ou revogação antecipada; login sujeito aos limites definidos no contrato.
- Produtos são excluídos logicamente somente sem avaliações. Avaliações e motivos são excluídos fisicamente em transação.
- Unicidade e verificações de estado devem resistir a requisições concorrentes.
- Resultados paginados: padrão 20, máximo 100; datas públicas ISO 8601 em UTC; erros no envelope único.
