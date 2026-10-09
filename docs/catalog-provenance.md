# Proveniência do catálogo

O snapshot `data/catalogo-inicial.json` é entrada publicada da migração 0010 e
fica congelado. O gerador e o workflow agora produzem `catalogo-candidate-v2.json`;
regenerar um candidato não modifica instalações existentes nem reinstalações.
Cada futura importação exige snapshot versionado novo e migração nova revisada.
A migração 0011 verifica SHA-256 do snapshot histórico antes de criar as colunas.

A API adiciona cinco campos opcionais em produtos, busca, detalhe e listas pessoais:
`source`, `source_url`, `image_source`, `image_license`, `image_license_url`.
São somente leitura pela API pública. Produtos manuais continuam com valores nulos.
A fonte da imagem identifica o projeto fornecedor, não o fotógrafo.

O backfill só preenche metadados inteiramente ausentes quando dono curador,
identidade, código e URL da imagem correspondem exatamente ao snapshot original.
Não altera dono, identidade, imagem, datas, exclusão ou avaliações. Registros
ambíguos/modificados e metadados já existentes ficam intactos. É idempotente.
O downgrade remove apenas as cinco colunas de proveniência (perde os metadados).

## Evidências e limites

Consultadas em 2026-10-08:

- [Guia oficial de licença do Product Opener](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/): base ODbL, conteúdos individuais DbCL e fotos CC BY-SA.
- [Apresentação oficial Open Beauty Facts](https://wiki.openfoodfacts.org/images/e/ed/OpenBeautyFacts.pdf): dados ODbL e fotos CC BY-SA.

As fontes consultadas confirmam a família da licença das imagens OFF/OBF;
não confirmam uma versão específica. Por isso `image_license = CC-BY-SA` e
`image_license_url = null`. Os termos Open Products Facts não puderam ser
consultados: sua licença de imagem permanece nula. Não inferir licença pelo
host nem confundir ODbL do banco com licença de fotos. Autor original não foi
coletado. Esta implementação melhora rastreabilidade, mas não atesta revisão
jurídica nem conclusão de todas as obrigações para exploração comercial.

Antes de publicar: verificar versões/URLs e requisitos de atribuição das três
bases, revisar backup e executar migrações/testes num PostgreSQL isolado. Aplicar
0011 antes de iniciar a nova API, pois o ORM passa a consultar essas colunas.
Nenhuma migração remota foi executada durante o desenvolvimento.
