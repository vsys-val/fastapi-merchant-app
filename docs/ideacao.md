# Ideação do produto

## Status do documento

Documento vivo. Reúne as decisões de produto confirmadas durante a fase de ideação.  
As questões ainda não decididas ficam registradas separadamente para não serem tratadas como requisitos.

## Problema

Ao comprar produtos em supermercados e mercearias, uma pessoa pode esquecer experiências anteriores e acabar comprando novamente algo de que não gostou.

## Proposta inicial

Criar uma aplicação que permita registrar e consultar experiências com produtos comprados em supermercados e mercearias, ajudando o usuário a tomar decisões de compra mais conscientes.

## Contextos principais de uso

### Durante a compra

O usuário consulta produtos e avaliações anteriores enquanto está no mercado, antes de decidir o que colocar no carrinho.

### Depois do consumo

Em casa, após experimentar o produto, o usuário registra sua experiência para consultas futuras.

## Público e acesso

O MVP será pensado para vários usuários e deverá possuir:

- cadastro;
- login;
- avaliações associadas ao autor;
- proteção das operações que exigem autenticação.

## Visibilidade das avaliações

As avaliações poderão ser vistas por outros usuários.

Na página ou resposta referente a um produto, a aplicação deverá apresentar separadamente:

- **Sua nota:** avaliação feita pelo usuário autenticado;
- **Média da comunidade:** média das avaliações feitas pelos usuários.

A avaliação pessoal será mais relevante para a decisão do usuário por ser exibida separadamente e com destaque. Ela não alterará matematicamente a média da comunidade.

## Jornadas identificadas

1. O usuário cria uma conta e entra na aplicação.
2. No mercado, pesquisa um produto.
3. Consulta sua própria avaliação, quando existente.
4. Consulta a média e as avaliações da comunidade.
5. Em casa, cadastra ou atualiza sua experiência com o produto.

## Decisões confirmadas

| Tema | Decisão |
|---|---|
| Momento de uso | Durante a compra e depois do consumo |
| Escopo de usuários | Vários usuários |
| Autenticação | Cadastro e login no MVP |
| Visibilidade | Avaliações de outros usuários são visíveis |
| Apresentação das notas | Nota pessoal e média da comunidade separadas |
| Peso da opinião pessoal | Destaque próprio, sem alterar a média comunitária |

## Artefatos planejados

Antes da implementação, serão produzidos:

1. definição do problema e proposta de valor;
2. jornadas de uso;
3. requisitos funcionais e regras de negócio;
4. casos de uso;
5. diagrama UML de casos de uso;
6. diagrama UML de classes;
7. modelo do banco de dados;
8. contrato inicial da API;
9. plano incremental de implementação;
10. documentação de execução e uso.

## Questões em aberto

- Como identificar produtos iguais?
- Quais informações serão obrigatórias no cadastro de um produto?
- Como funcionará a escala e o conteúdo de uma avaliação?
- Um usuário poderá alterar ou excluir sua avaliação?
- Haverá apenas uma avaliação atual por usuário e produto ou um histórico?
- Como produtos ainda não cadastrados entrarão no catálogo?
- Quais filtros e formas de pesquisa estarão no MVP?
