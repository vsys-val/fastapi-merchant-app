# ADR-0014 — Leitura de código de barras pela câmera

- Status: aceita
- Data: 2026-09-25
- Origem: item do [roadmap](../roadmap.md) ligado ao JTBD da persona Ana: decidir no corredor do mercado

## Contexto

A busca por código de barras exigia digitar 8 a 14 dígitos no celular, em pé, com o produto na mão. É o caminho mais preciso para achar um produto (o GTIN é único no catálogo), mas também o mais lento de usar. A interface é um PWA sem app nativo. A política `Permissions-Policy: camera=()` bloqueava a câmera e a CSP proíbe `eval` e scripts de terceiros.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Decodificador | Só `BarcodeDetector` nativo · polyfill em WebAssembly (`barcode-detector`/`zxing-wasm`) · **nativo quando existe, ZXing em JavaScript como reserva** | Nativo no Android/Chrome e ZXing no resto (iOS, desktop). O polyfill em WASM exigiria `wasm-unsafe-eval` na CSP e servir o binário; o ZXing em JS não exige nenhuma mudança na CSP |
| Custo no carregamento | Incluir no bundle principal · **carregar sob demanda** | Sob demanda: o ZXing só é baixado quando a pessoa abre o leitor, então quem não usa a câmera não paga por ela |
| Formatos | Todos · **EAN-13, EAN-8 e UPC-A** | São os GTIN dos produtos de varejo. UPC-E não é um GTIN-8 e é raro no Brasil; QR e códigos internos não identificam o produto |
| Leituras erradas | Exigir duas leituras iguais · **validar o dígito verificador** | O dígito verificador (a mesma regra da API) descarta quase todas as leituras parciais e não atrasa a leitura boa |
| Onde oferecer | Só na busca · **na busca e no cadastro de produto** | No cadastro a câmera também evita erro de digitação no GTIN, o que protege a deduplicação ([ADR-0004](0004-catalogo-canonico-comunitario.md)) |

## Decisão

- Botão "Ler com a câmera" no modo "Código de barras" da busca e no campo GTIN do cadastro.
- O leitor abre em tela cheia com a câmera traseira. Com o primeiro GTIN válido lido, ele vibra, fecha, preenche o campo e, na busca, já pesquisa.
- Permissão negada, aparelho sem câmera, navegador sem suporte ou falha têm mensagens próprias. A opção "Digitar o código" está sempre disponível, e há "Tentar de novo" quando faz sentido.
- `Permissions-Policy: camera=(self)`: a câmera fica liberada só para a própria origem.
- O evento `barcode_scan` registra o resultado (lido, cancelado, sem permissão…), o decodificador e a tela. O painel mostra aberturas, taxa de leitura e a parcela sem câmera disponível.

## Consequências

- ➕ Buscar por código deixa de exigir digitação, e o cadastro recebe GTIN sem erro de digitação.
- ➕ Nada muda na CSP; o bundle inicial não cresce com o ZXing.
- ➕ Testável de ponta a ponta: o E2E usa a câmera falsa do Chromium "filmando" um EAN-13 gerado pelo próprio teste, e o ZXing o decodifica de verdade.
- ➖ No iOS e no desktop o ZXing é mais lento que o leitor nativo e sofre mais com pouca luz e foco.
- ➖ A câmera exige HTTPS (o Render já serve assim) e a permissão do navegador. Se a pessoa negar a permissão, só as configurações do navegador revertem a decisão.
- ➖ Uma dependência a mais no frontend (`@zxing/browser` e `@zxing/library`).

## Rastreabilidade

RF04 · RN43 · US03, US06 · T49 · frontend: `src/features/barcode/`, `render.yaml` (Permissions-Policy)
