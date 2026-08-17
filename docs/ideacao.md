# Ideação do produto

## Status do documento

Documento vivo. Reúne as decisões de produto confirmadas durante a fase de ideação.  
As questões ainda não decididas ficam registradas separadamente para não serem tratadas como requisitos.

## Problema

Ao comprar produtos em supermercados e mercearias, uma pessoa pode esquecer experiências anteriores e acabar comprando novamente algo de que não gostou.

## Proposta inicial

Criar uma aplicação que permita registrar e consultar experiências com produtos comprados em supermercados e mercearias, ajudando o usuário a tomar decisões de compra mais conscientes.

O escopo não se limita a alimentos e bebidas. Ele inclui também produtos de limpeza, higiene, utilidades domésticas e outros itens normalmente encontrados nesses estabelecimentos.

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
- variante opcional, como sabor ou fragrância;
- quantidade obrigatória;
- unidade obrigatória, como g, kg, ml, L ou unidade;
- código de barras opcional.

Quando informado, o código de barras deverá ser único. Ele ajudará a localizar rapidamente um item e a evitar registros duplicados, mas não será obrigatório porque alguns produtos não possuem código próprio.

O código representa o item comercial. Versões, variantes, tamanhos ou embalagens diferentes podem possuir códigos diferentes.

O catálogo será compartilhado: avaliações de diferentes usuários deverão apontar para o mesmo registro canônico de produto.

Antes de criar um produto, a API deverá procurar duplicidade:

1. pelo código de barras, quando informado;
2. pela combinação normalizada de nome, marca, variante, quantidade e unidade.

Se identificar um produto já existente, a API deverá rejeitar a duplicação e indicar conflito com o registro canônico.

Qualquer usuário autenticado poderá cadastrar um produto que ainda não exista no catálogo.

O usuário que cadastrou o produto poderá corrigir seus dados enquanto nenhuma avaliação de outro usuário estiver associada a ele. Depois que outro usuário avaliar o produto, seus dados de identificação ficarão bloqueados para edições comuns. Um fluxo administrativo de correção ou mesclagem de duplicatas fica fora do MVP.

## Estrutura da avaliação

Não haverá uma nota geral escolhida manualmente pelo usuário. A avaliação será estruturada para reduzir respostas impulsivas e tornar o motivo da experiência mais claro.

O principal resumo será a **intenção de recompra**, com três respostas:

- compraria novamente;
- talvez comprasse novamente;
- não compraria novamente.

A avaliação também conterá três critérios universais, aplicáveis a qualquer categoria de produto:

- qualidade percebida;
- atendimento às expectativas;
- custo-benefício.

Cada critério terá três respostas semânticas:

| Critério | Respostas |
|---|---|
| Qualidade percebida | baixa, adequada ou alta |
| Atendimento às expectativas | não atendeu, atendeu ou superou |
| Custo-benefício | ruim, justo ou bom |

A API trabalhará com valores controlados e documentados, evitando números sem significado explícito.

Toda avaliação deverá possuir pelo menos um motivo predefinido. Essa exigência dá contexto à decisão e reduz o risco de avaliações acidentais ou vazias.

Cada motivo será estruturado pela combinação de:

- um aspecto do produto, como embalagem ou sabor;
- uma percepção positiva ou negativa.

Uma avaliação poderá conter vários aspectos. O mesmo aspecto não poderá ser repetido dentro da mesma avaliação com percepções iguais ou conflitantes.

A lista de aspectos deverá ser abrangente o suficiente para diferentes categorias. Nem todo aspecto será aplicável a todo produto; o usuário selecionará somente os relevantes para aquela experiência.

Os aspectos disponíveis no MVP serão:

- sabor;
- cheiro ou fragrância;
- textura ou consistência;
- eficácia ou desempenho;
- quantidade ou rendimento;
- facilidade de uso ou preparo;
- embalagem;
- durabilidade ou conservação;
- composição ou ingredientes;
- segurança ou tolerância;
- preço;
- outro.

Quando o aspecto **outro** for selecionado, o comentário explicativo será obrigatório.

A avaliação poderá conter também um comentário opcional. Os motivos exatos ainda serão definidos. Critérios específicos por categoria ficam fora do MVP.

Para a comunidade, a aplicação poderá apresentar a proporção de usuários em cada intenção de recompra e os indicadores agregados de cada critério definido.

Cada usuário terá no máximo uma avaliação atual para cada produto. A avaliação poderá ser editada, e a nova versão substituirá os valores anteriores. O usuário também poderá excluir a própria avaliação. O MVP não armazenará um histórico de avaliações.

As avaliações serão a fonte da verdade dos indicadores comunitários. No MVP, esses indicadores serão calculados sob demanda ao consultar cada produto. Ao editar ou excluir uma avaliação, não será necessário recalcular toda a plataforma: a consulta seguinte daquele produto já refletirá o conjunto atual de avaliações.

## Responsabilidades da API e da interface

A API não possui telas. Ela será responsável por:

- receber os dados enviados por uma interface;
- validar valores obrigatórios e formatos;
- aplicar as regras de negócio;
- salvar e consultar informações;
- devolver respostas e erros claros.

Uma futura interface web ou móvel poderá mostrar uma tela de confirmação antes de enviar a avaliação. Essa confirmação não faz parte da API.

Para reduzir o impacto de enganos, a API validará os valores recebidos e permitirá a edição da avaliação conforme a regra que ainda será definida.

## Pesquisa de produtos

No MVP, o catálogo poderá ser pesquisado por:

- nome;
- marca;
- código de barras.

A busca textual por nome e marca deverá aceitar correspondências parciais. A consulta por código de barras buscará uma correspondência exata. Filtros por variante e categoria ficam fora do escopo inicial e poderão ser adicionados posteriormente.

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
| Categorias de produtos | Alimentos, bebidas, limpeza, higiene, utilidades domésticas e outros itens de mercado |
| Escopo de usuários | Vários usuários |
| Autenticação | Cadastro e login no MVP |
| Visibilidade | Avaliações de outros usuários são visíveis |
| Apresentação das avaliações | Experiência pessoal e indicadores da comunidade separados |
| Peso da opinião pessoal | Destaque próprio, sem alterar os indicadores comunitários |
| Identificação do produto | Nome, marca, variante, quantidade, unidade e código de barras opcional |
| Variante | Opcional |
| Quantidade e unidade | Obrigatórias |
| Unicidade do código de barras | Único quando informado |
| Prevenção de duplicidade | Código de barras ou combinação normalizada dos dados de identificação |
| Catálogo | Um registro canônico compartilhado por todos os usuários |
| Cadastro de produtos | Permitido a qualquer usuário autenticado |
| Pesquisa de produtos | Por nome, marca ou código de barras |
| Filtros avançados | Variante e categoria fora do MVP |
| Edição de produtos | Criador pode editar até existir avaliação de outro usuário |
| Produto utilizado pela comunidade | Dados de identificação bloqueados |
| Correção administrativa e mesclagem | Fora do MVP |
| Nota geral manual | Não haverá |
| Principal resumo da avaliação | Intenção de recompra: sim, talvez ou não |
| Critérios universais | Qualidade percebida, atendimento às expectativas e custo-benefício |
| Critérios por categoria | Fora do MVP |
| Escala dos critérios | Três respostas semânticas específicas para cada critério |
| Motivo da avaliação | Pelo menos um motivo predefinido obrigatório |
| Formato dos motivos | Aspecto do produto combinado com percepção positiva ou negativa |
| Aspectos disponíveis | Lista abrangente para alimentos, bebidas, limpeza, higiene e outros produtos |
| Aspecto “outro” | Permitido, mas exige comentário |
| Tela de confirmação | Responsabilidade de uma futura interface, não da API |
| Avaliações por usuário e produto | Uma avaliação atual, editável |
| Histórico de avaliações | Fora do MVP |
| Exclusão de avaliação | O usuário pode excluir a própria avaliação |
| Atualização dos indicadores | Calculados sob demanda a partir das avaliações existentes |
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
