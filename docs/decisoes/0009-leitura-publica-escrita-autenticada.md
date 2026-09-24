# ADR-0009 — Leitura pública, escrita autenticada

- Status: aceita
- Data: 2026-08-18
- Origem: `1cd8c32` (define acesso público e operações protegidas), `4db5bd3` (define login por e-mail e senha), `b8c2deb` (separa nome público e id do usuário)

## Contexto

No corredor, exigir login antes de mostrar qualquer coisa mata a primeira experiência e a descoberta pelo Bruno. Por outro lado, cadastrar produtos e avaliar exige identidade, para garantir uma avaliação por pessoa, autoria e permissão de edição.

## Decisão

- **Públicos:** busca, detalhe, indicadores e lista de avaliações comunitárias.
- **Autenticados:** cadastrar, editar e excluir produto; criar, editar e excluir a própria avaliação; área pessoal.
- A autoria aparece pelo **nome público**, que pode se repetir. O e-mail e o ID do autor nunca são expostos.
- Leituras públicas aceitam token **opcional**. Com token, a resposta é personalizada. Um token **inválido** é rejeitado com `401`, e não tratado silenciosamente como visitante.

## Consequências

- ➕ Valor imediato para quem não tem conta, o que funciona como funil de aquisição.
- ➕ A privacidade é preservada por padrão (RNF02, T29).
- ➖ Um token expirado em leitura pública gera `401` e o cliente precisa limpar a sessão. O frontend faz isso em `AuthContext`.

## Rastreabilidade

RN01–RN04 · RNF02 · UC01, UC02, UC05 · T07, T29 · `app/auth.py::get_optional_user`, `get_current_user`
