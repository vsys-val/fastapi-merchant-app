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
| RF04 | A API deve permitir pesquisar produtos por nome, marca ou código de barras. |
| RF05 | A API deve retornar os dados de um produto, as avaliações da comunidade e, quando houver usuário autenticado, sua própria avaliação separadamente. |
| RF06 | A API deve permitir que um usuário autenticado cadastre um produto ausente no catálogo. |
| RF07 | A API deve permitir que o criador corrija um produto enquanto nenhum outro usuário o tiver avaliado. |
| RF08 | A API deve permitir que um usuário autenticado crie sua avaliação de um produto. |
| RF09 | A API deve permitir que o autor edite a própria avaliação. |
| RF10 | A API deve permitir que o autor exclua a própria avaliação. |
| RF11 | A API deve permitir consultar as avaliações comunitárias de um produto. |
| RF12 | A API deve fornecer indicadores comunitários agregados por produto. |

## Regras de negócio

### Usuários e autenticação

| ID | Regra |
|---|---|
| RN01 | Cada usuário deve possuir um identificador interno único. |
| RN02 | O nome público pode se repetir entre usuários. |
| RN03 | O e-mail deve ser único e não pode ser exibido publicamente. |
| RN04 | A senha original nunca deve ser armazenada; somente seu hash seguro. |
| RN05 | Consultas são públicas, mas operações que alteram dados exigem autenticação. |

### Produtos

| ID | Regra |
|---|---|
| RN06 | Todo produto deve possuir nome, marca, quantidade, unidade e categoria. |
| RN07 | A variante e o código de barras são opcionais. |
| RN08 | Cada produto deve pertencer a exatamente uma categoria principal. |
| RN09 | As categorias do MVP são: alimentos, bebidas, limpeza, higiene pessoal, utilidades domésticas e outros. |
| RN10 | Quando informado, o código de barras deve ser único. |
| RN11 | O catálogo deve manter um registro canônico compartilhado para cada produto. |
| RN12 | A API deve procurar duplicidade pelo código de barras ou pela combinação normalizada de nome, marca, variante, quantidade e unidade. |
| RN13 | Uma tentativa de cadastrar produto duplicado deve ser rejeitada como conflito e indicar o registro existente. |
| RN14 | O criador pode editar os dados do produto somente enquanto nenhum outro usuário o tiver avaliado. |
| RN15 | Nome e marca devem aceitar pesquisa textual parcial; código de barras exige correspondência exata. |

### Avaliações

| ID | Regra |
|---|---|
| RN16 | Cada usuário pode manter no máximo uma avaliação atual por produto. |
| RN17 | A intenção de recompra é obrigatória e aceita: compraria novamente, talvez comprasse ou não compraria novamente. |
| RN18 | Qualidade percebida, atendimento às expectativas e custo-benefício são obrigatórios. |
| RN19 | Qualidade aceita: baixa, adequada ou alta. |
| RN20 | Expectativa aceita: não atendeu, atendeu ou superou. |
| RN21 | Custo-benefício aceita: ruim, justo ou bom. |
| RN22 | Toda avaliação deve possuir pelo menos um motivo estruturado como aspecto e percepção positiva ou negativa. |
| RN23 | Um aspecto não pode aparecer mais de uma vez na mesma avaliação. |
| RN24 | Os aspectos disponíveis são: sabor, cheiro ou fragrância, textura ou consistência, eficácia ou desempenho, quantidade ou rendimento, facilidade de uso ou preparo, embalagem, durabilidade ou conservação, composição ou ingredientes, segurança ou tolerância, preço e outro. |
| RN25 | O aspecto “outro” exige comentário explicativo. Nos demais casos, o comentário é opcional. |
| RN26 | Somente o autor pode editar ou excluir sua avaliação. |
| RN27 | A avaliação pessoal deve ser apresentada separadamente dos indicadores comunitários. |
| RN28 | Os indicadores comunitários devem ser calculados a partir das avaliações existentes no momento da consulta. |
| RN29 | O MVP mantém apenas a avaliação atual e não armazena histórico de versões. |

## Fora do escopo inicial

- recuperação de senha por e-mail;
- critérios de avaliação específicos por categoria;
- histórico de avaliações;
- múltiplas categorias por produto;
- filtros avançados por variante ou categoria;
- administração e mesclagem manual de produtos duplicados;
- interface web ou aplicativo móvel.
