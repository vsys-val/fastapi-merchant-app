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

Ao consultar um produto, a aplicação deverá apresentar separadamente:

- **Sua experiência:** avaliação feita pelo usuário autenticado, com destaque;
- **Experiência da comunidade:** indicadores agregados das avaliações dos usuários.

A avaliação pessoal não alterará matematicamente os indicadores da comunidade.

## Identificação dos produtos

Cada produto deverá possuir:

- nome obrigatório;
- marca obrigatória;
- código de barras opcional.

Quando informado, o código de barras deverá ser único. Ele ajudará a localizar rapidamente um item e a evitar registros duplicados, mas não será obrigatório porque alguns produtos não possuem código próprio.

O código representa o item comercial. Versões, sabores, tamanhos ou embalagens diferentes podem possuir códigos diferentes.

## Estrutura da avaliação

Não haverá uma nota geral escolhida manualmente pelo usuário. A avaliação será estruturada para reduzir respostas impulsivas e tornar o motivo da experiência mais claro.

O principal resumo será a **intenção de recompra**, com três respostas:

- compraria novamente;
- talvez comprasse novamente;
- não compraria novamente.

A avaliação também poderá conter critérios separados, motivos predefinidos e um comentário opcional. Os critérios e motivos exatos ainda serão definidos.

Para a comunidade, a aplicação poderá apresentar a proporção de usuários em cada intenção de recompra e os indicadores agregados de cada critério definido.

Cada usuário terá no máximo uma avaliação atual para cada produto. A avaliação poderá ser editada, e a nova versão substituirá os valores anteriores. O MVP não armazenará um histórico de avaliações.

## Responsabilidades da API e da interface

A API não possui telas. Ela será responsável por:

- receber os dados enviados por uma interface;
- validar valores obrigatórios e formatos;
- aplicar as regras de negócio;
- salvar e consultar informações;
- devolver respostas e erros claros.

Uma futura interface web ou móvel poderá mostrar uma tela de confirmação antes de enviar a avaliação. Essa confirmação não faz parte da API.

Para reduzir o impacto de enganos, a API validará os valores recebidos e permitirá a edição da avaliação conforme a regra que ainda será definida.

## Jornadas identificadas

1. O usuário cria uma conta e entra na aplicação.
2. No mercado, pesquisa um produto.
3. Consulta sua própria avaliação, quando existente.
4. Consulta os indicadores e as avaliações da comunidade.
5. Em casa, cadastra ou atualiza sua experiência com o produto.

## Decisões confirmadas

| Tema | Decisão |
|---|---|
| Momento de uso | Durante a compra e depois do consumo |
| Escopo de usuários | Vários usuários |
| Autenticação | Cadastro e login no MVP |
| Visibilidade | Avaliações de outros usuários são visíveis |
| Apresentação das avaliações | Experiência pessoal e indicadores da comunidade separados |
| Peso da opinião pessoal | Destaque próprio, sem alterar os indicadores comunitários |
| Identificação do produto | Nome e marca obrigatórios; código de barras opcional |
| Unicidade do código de barras | Único quando informado |
| Nota geral manual | Não haverá |
| Principal resumo da avaliação | Intenção de recompra: sim, talvez ou não |
| Tela de confirmação | Responsabilidade de uma futura interface, não da API |
| Avaliações por usuário e produto | Uma avaliação atual, editável |
| Histórico de avaliações | Fora do MVP |
| Unicidade da avaliação | A combinação de usuário e produto deverá ser única |

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

- Quais outras informações serão obrigatórias ou opcionais no cadastro de um produto?
- Quais critérios separados farão parte da avaliação?
- Quais motivos predefinidos poderão ser selecionados?
- Um usuário poderá excluir sua avaliação?
- Como produtos ainda não cadastrados entrarão no catálogo?
- Quais filtros e formas de pesquisa estarão no MVP?
