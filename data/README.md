# Dados

## `catalogo-inicial.json`

Catálogo inicial do Merchant: cerca de 500 produtos vendidos no Brasil, gerados por `scripts/build_catalog_seed.py` (workflow **Catalog seed**) e inseridos pela migração `0010_catalog_seed`. Decisão em [ADR-0017](../docs/decisoes/0017-catalogo-inicial-open-food-facts.md).

**Fonte e licença.** Os dados vêm do [Open Food Facts](https://openfoodfacts.org), do [Open Beauty Facts](https://openbeautyfacts.org) e do [Open Products Facts](https://openproductsfacts.org). Estão disponíveis sob a [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/), e este arquivo, que é uma base derivada, é distribuído sob a mesma licença. Cada produto com código de barras traz `source_url`, o endereço de origem.

**Campos.**

| Campo | Descrição |
|---|---|
| `name`, `brand`, `variant` | Nome, marca e variante já normalizados pelas regras da API |
| `quantity`, `unit` | Quantidade canônica (`g`, `ml` ou `un`) |
| `category` | Categoria do contrato da API |
| `barcode` | GTIN com dígito verificador válido, ou `null` |
| `identity_key`, `search_name`, `search_brand` | Campos derivados, calculados pelas funções da API na geração |
| `source`, `source_url` | Base e página de origem |
| `image_url` | Foto da frente da embalagem (400 px) nos servidores de imagem da base, sob **CC BY-SA**, ou `null` |

**Atualizar.** Altere `scripts/build_catalog_seed.py` numa branch de trabalho. O workflow gera o arquivo de novo e o grava na própria branch. Produtos novos entram por uma nova migração; a `0009` nunca é reexecutada em quem já a aplicou.
