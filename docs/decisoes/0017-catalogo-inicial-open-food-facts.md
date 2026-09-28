# ADR-0017 — Catálogo inicial a partir do Open Food Facts

- Status: aceita
- Data: 2026-09-28
- Origem: pedido do responsável pelo produto: "deixar o app pré-populado"; relaciona-se à [ADR-0004](0004-catalogo-canonico-comunitario.md) (catálogo canônico comunitário)

## Contexto

O catálogo nasce vazio. A primeira pessoa que busca "arroz" não encontra nada, precisa cadastrar o produto antes de avaliar e tende a desistir. Isso ataca justamente a hipótese H1 da [visão](../visao-produto.md) ("encontrar e registrar leva menos de um minuto"). Um catálogo com os itens mais comprados resolve o problema de início frio sem mudar o modelo comunitário: qualquer pessoa continua podendo cadastrar o que faltar.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Fonte dos dados | Lista curada à mão (sem código de barras) · raspagem de sites de mercado · **Open Food Facts e bases irmãs** | Open Food Facts: produtos reais vendidos no Brasil, com GTIN, marca e quantidade, sob licença aberta. Raspagem violaria termos de uso; lista à mão não teria códigos de barras, e o leitor pela câmera ([ADR-0014](0014-leitura-de-codigo-de-barras-pela-camera.md)) ficaria sem uso |
| Quantidade | Todos os produtos brasileiros (dezenas de milhares) · ~150 · **~500 mais escaneados, por categoria** | ~500: cobre o que as pessoas de fato compram sem encher a busca de itens obscuros ou com dados ruins |
| Dono dos produtos | Conta de administração · **conta própria "Catálogo Merchant"** | Conta própria: separa o catálogo inicial das contribuições de pessoas e deixa as métricas limpas. Ninguém conhece a senha |
| Como chega ao banco | Script manual com a URL do banco · chamadas à API em produção · **migração de dados versionada** | Migração: roda sozinha no deploy, fica revisada no PR e reproduzível em qualquer ambiente, sem segredo novo |
| Quando buscar os dados | Durante a migração · **antes, num workflow, gerando um arquivo versionado** | Arquivo versionado: o deploy não depende da internet nem da disponibilidade do Open Food Facts, e o PR mostra exatamente o que entra |

## Decisão

- `scripts/build_catalog_seed.py`, no workflow **Catalog seed**, consulta as bases:
  - Open Food Facts, para alimentos e bebidas;
  - Open Beauty Facts, para higiene pessoal;
  - Open Products Facts, para limpeza e utilidades.

  Em cada uma, pega os produtos vendidos no Brasil, ordenados pelos mais escaneados.
- Cada produto passa pelas regras de entrada da API (`ProductCreate`): nome, marca, quantidade canônica e GTIN com dígito verificador. São descartados:
  - embalagens múltiplas ("6 x 200 ml");
  - itens sem quantidade;
  - nome igual à marca;
  - repetidos pela identidade (RN08) ou pelo código.
- Nomes que vêm TODOS EM MAIÚSCULAS passam para iniciais maiúsculas. A quantidade no fim do nome sai, porque já está no campo próprio.
- Metas por categoria:

  | Categoria | Produtos |
  |---|---|
  | Alimentos | 260 |
  | Bebidas | 110 |
  | Higiene | 70 |
  | Limpeza | 45 |
  | Utilidades | 15 |

  O que faltar numa categoria é completado com alimentos.
- O resultado vai para `data/catalogo-inicial.json`. A migração `0010_catalog_seed`:
  - cria a conta `Catálogo Merchant` (e-mail `catalogo@merchant-app.invalid`, senha aleatória descartada);
  - insere os produtos com `ON CONFLICT DO NOTHING`, de modo que produto já cadastrado por alguém, inclusive excluído, fica como está;
  - no `downgrade`, remove só os produtos sem avaliação.
- O painel administrativo:
  - não conta essa conta nem os produtos dela como crescimento (usuários, produtos por dia e coorte de ativação);
  - inclui os produtos no tamanho e na saúde do catálogo;
  - mostra `products_seeded` à parte.

## Consequências

- ➕ A primeira busca já encontra os produtos mais comuns, e o leitor de código de barras funciona desde o primeiro dia.
- ➕ O PR que traz os dados mostra cada produto; um produto ruim se corrige no arquivo ou pela API.
- ➖ **Licença ODbL**: exige atribuição visível no app e que a base derivada continue aberta. O arquivo fica público no repositório, sob ODbL, e o site cita o Open Food Facts.
- ➖ Dados colaborativos têm erros (nome genérico, marca grafada de outro jeito). As regras de entrada filtram o grosso; o resto se corrige como qualquer produto.
- ➖ A conta "Catálogo Merchant" não tem senha conhecida, então correções nos produtos dela ainda não são possíveis pela interface. Enquanto não houver moderação ([roadmap](../roadmap.md)), a correção é por nova versão do arquivo ou direto no banco.
- ➖ "Produtos sem avaliação" no painel sobe bastante no início, porque os ~500 itens nascem sem avaliação. É o retrato real do catálogo, e o indicador de crescimento continua limpo.

## Rastreabilidade

RN49 · T53 · `scripts/build_catalog_seed.py`, `.github/workflows/catalog-seed.yml`, `data/catalogo-inicial.json`, `alembic/versions/0010_catalog_seed.py`, `app/admin.py`
