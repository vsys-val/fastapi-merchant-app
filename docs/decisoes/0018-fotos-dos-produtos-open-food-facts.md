# ADR-0018 — Fotos dos produtos a partir do Open Food Facts

- Status: aceita
- Data: 2026-09-28
- Origem: pedido do responsável pelo produto: "desejo que tenhamos as imagens dos produtos", para facilitar a identificação na prateleira; complementa a [ADR-0017](0017-catalogo-inicial-open-food-facts.md)

## Contexto

O produto era só texto. No mercado, a pessoa reconhece a embalagem antes de ler o nome, e sem foto dois produtos parecidos da mesma marca se confundem na busca. As bases do Open Food Facts já têm a foto da frente da embalagem de boa parte do catálogo inicial.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Onde a foto fica | Copiar para um armazenamento próprio (Supabase Storage, S3) · **usar o endereço público do Open Food Facts** | Endereço público: não exige armazenamento, custo nem processamento de imagem. É o mais simples para ter fotos agora |
| Quem define a foto | Envio de foto por quem cadastra · **só o catálogo inicial** | Envio exige armazenamento, moderação e limites de tamanho. Fica para quando houver evidência de que faz falta |
| Tamanho | Original · **400 px da frente** | 400 px serve para a miniatura e para o detalhe, sem pesar no celular |
| Validação do endereço | Aceitar qualquer URL · **só os servidores de imagem das três bases** | Evita apontar para qualquer site e permite restringir a CSP a esses hosts |

## Decisão

- Produtos ganham `imagem_url` (migração `0009_product_image`), exposta na API como `image_url`, nula quando não há foto. O campo não entra em `ProductCreate` nem na edição.
- O gerador do catálogo guarda a `image_front_url` de 400 px quando ela vem de `images.openfoodfacts.org`, `images.openbeautyfacts.org` ou `images.openproductsfacts.org`. Qualquer outro endereço é descartado.
- O site mostra:
  - miniatura na lista da busca;
  - foto maior no detalhe;
  - um ícone da categoria quando não há foto;
  - carregamento sob demanda, `referrerpolicy="no-referrer"` e texto alternativo com nome e marca.
- A CSP do site libera em `img-src` só esses três hosts.
- As fotos do Open Food Facts são **CC BY-SA**. O crédito da busca passa a citar dados (ODbL) e fotos (CC BY-SA), e o detalhe mostra "Foto: Open Food Facts" sob a imagem.

## Consequências

- ➕ Os produtos ficam reconhecíveis na busca e no detalhe, sem custo de armazenamento.
- ➕ Produtos sem foto continuam iguais, com o ícone da categoria.
- ➖ **Privacidade:** o navegador de quem usa o site busca a foto direto no Open Food Facts, que fica sabendo o IP e o horário. Mitigado com `no-referrer`, que não envia a página de origem, e com fotos só de produtos públicos. Copiar as fotos para um armazenamento próprio elimina isso e fica registrado como evolução.
- ➖ A foto depende da disponibilidade do Open Food Facts. Se a imagem falhar, o site mostra o ícone da categoria.
- ➖ Quem cadastra produto ainda não envia foto; os produtos da comunidade ficam com o ícone.

## Rastreabilidade

RN50 · T54 · `alembic/versions/0009_product_image.py`, `app/models.py`, `app/schemas.py`, `scripts/build_catalog_seed.py` · frontend: `ProductImage`, `render.yaml` (CSP)
