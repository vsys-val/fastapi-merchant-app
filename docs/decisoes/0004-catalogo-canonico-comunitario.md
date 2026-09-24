# ADR-0004 — Catálogo canônico comunitário com deduplicação

- Status: aceita
- Data: 2026-08-17
- Origem: `130ca5c` (permite cadastro comunitário de produtos), `ee263a2` (fortalece identidade e deduplicação de produtos), `7b7dc8c` (define identificação dos produtos)

## Contexto

Não existe base pública e gratuita de produtos de mercado brasileiros que seja confiável e completa o bastante para o MVP. Se cada usuário tivesse seus próprios produtos, as avaliações não se somariam e o valor para a comunidade (persona Bruno) não existiria. Se qualquer usuário cadastrar livremente, o catálogo se enche de duplicatas: "Café Pilão 500g", "cafe pilao 500 g", "Café Pilão 0,5 kg".

## Alternativas consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| Catálogo curado por administradores | Qualidade alta | Não escala; exige operação; o MVP não tem equipe |
| Produtos privados por usuário | Simples | Sem indicadores comunitários |
| Integração com base externa de GTIN | Dados ricos | Custo, licenciamento, cobertura incerta de itens sem código |
| **Catálogo comunitário com deduplicação automática** | Escala com os usuários; um registro por item | Exige regras de identidade robustas |

## Decisão

- Qualquer usuário autenticado pode cadastrar um produto que ainda não exista.
- Existe **um registro canônico** por item. Todas as avaliações apontam para ele.
- Duplicidade é detectada por:
  1. **GTIN** (código de barras), quando informado: único e com dígito verificador validado;
  2. **chave de identidade normalizada**: nome + marca + variante + quantidade + unidade, com caixa, acentos e espaços normalizados e medidas convertidas para unidade-base (`1,5 L` = `1500 ml`).
- A **categoria não participa da identidade**: classificações divergentes não criam produtos diferentes.
- Uma duplicata ativa retorna `409 product_conflict` com `existing_product_id`, e a interface pode levar o usuário ao registro existente.

## Consequências

- ➕ Avaliações de pessoas diferentes se acumulam no mesmo item.
- ➕ A unicidade é garantida pelo **banco** (UNIQUE), não só por consulta prévia, e vale inclusive sob concorrência (testado em PostgreSQL real).
- ➖ Erros de digitação ("Pilao" vs. "Pilão" é resolvido; "Pilãoo" não) ainda geram duplicatas. Mesclagem administrativa ficou fora do MVP.
- ➖ Quem cadastra primeiro define os dados do produto. Mitigado pelo [ADR-0005](0005-bloqueio-de-edicao-apos-avaliacao.md).

## Rastreabilidade

RF06 · RN09–RN12 · UC06 · T08–T11, T17 · `app/validation.py::build_identity_key`, `validate_gtin` · `app/products.py::create_product` · constraints `produtos_codigo_barras_key`, `produtos_chave_identidade_key`
