# ADR-0016 — Sessão do navegador em cookie HttpOnly, com a API na mesma origem do site

- Status: aceita
- Data: 2026-09-28
- Origem: item do [roadmap](../roadmap.md) "Sessão em cookie HttpOnly"; evolução prevista na [ADR-0010](0010-autenticacao-propria.md)

## Contexto

O site guardava o JWT no `localStorage` e o enviava como `Authorization: Bearer`. Qualquer script que rodasse na página (uma dependência comprometida, um XSS que escapasse da CSP) conseguiria ler o token e usá-lo de outro lugar por até 24 horas. A CSP e a ausência de HTML arbitrário reduziam o risco, mas não o eliminavam.

Um cookie `HttpOnly` resolve a leitura, mas traz duas dificuldades:

1. **Origens diferentes.** O site (`merchant-app-web.onrender.com`) e a API (`fastapi-merchant-app.onrender.com`) são subdomínios de `onrender.com`, que está na Public Suffix List. Para o navegador, são sites diferentes: um cookie emitido pela API seria de terceiros e bloqueado por Safari e, cada vez mais, pelo Chrome.
2. **CSRF.** Um cookie vai junto automaticamente, inclusive em requisições disparadas por outros sites.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Onde guardar a sessão | `localStorage` · `sessionStorage` · token só em memória (perde a sessão ao recarregar) · **cookie `HttpOnly`** | Cookie: o JavaScript não lê, e a sessão sobrevive a recarregar a página |
| Como tornar o cookie primário | Domínio próprio para site e API · `SameSite=None` com cookie de terceiros · **rewrite `/api/*` do site estático para a API** | Rewrite: gratuito, sem domínio novo, e o cookie passa a ser da mesma origem. Um domínio próprio continua compatível com a decisão |
| Proteção contra CSRF | Token CSRF sincronizado · *double submit cookie* · só `SameSite` · **`SameSite=Lax` + cabeçalho próprio obrigatório** | `SameSite=Lax` barra o envio em requisições de outros sites que não sejam navegação; o cabeçalho `X-Merchant-Client` cobre o resto, porque formulários não enviam cabeçalhos e `fetch` de outra origem com cabeçalho próprio exige preflight que o CORS recusa. Sem estado extra no servidor |
| Clientes de API | Só cookie · **cookie e Bearer** | Bearer continua valendo e tem precedência. Scripts, testes e o smoke test não mudam |
| Migração de quem já está conectado | Pedir login de novo · **trocar o token salvo pelo cookie** | `POST /auth/session` com o Bearer antigo grava o cookie; o site apaga o token logo em seguida. Ninguém precisa digitar a senha |
| Logout | Só apagar no cliente · lista de tokens revogados · **endpoint que apaga o cookie** | O cookie só pode ser apagado pelo servidor. Revogação continua sendo a troca de senha (RN32) |

## Decisão

- Login e confirmação de e-mail gravam o cookie `merchant_session`: `HttpOnly`, `SameSite=Lax`, `Path=/api`, `Max-Age` igual à validade do token e `Secure` em produção. O corpo da resposta continua com o token, para clientes de API.
- A autenticação lê primeiro `Authorization: Bearer`; na ausência dele, o cookie.
- Métodos que alteram dados, autenticados pelo cookie, exigem `X-Merchant-Client`. Sem o cabeçalho: `403 csrf_header_required`.
- Cookie inválido ou expirado não bloqueia leituras públicas (a requisição segue anônima); rotas que exigem conta respondem `401`.
- Novos endpoints: `POST /auth/session` (troca Bearer por cookie) e `POST /auth/logout` (apaga o cookie).
- O site estático repassa `/api/*` e `/health` para a API. O frontend usa caminhos relativos, não guarda token e restringe a CSP a `connect-src 'self'`. Em desenvolvimento, o Vite faz o mesmo repasse.

## Consequências

- ➕ Um script injetado na página não consegue ler nem exportar o token.
- ➕ A CSP fica mais estreita: o navegador só conversa com a própria origem.
- ➕ Clientes de API, testes e o smoke test continuam usando Bearer sem mudança.
- ➖ Um salto a mais: cada chamada do navegador passa pelo proxy do site estático. A latência extra é pequena em relação ao tempo da própria API, e o painel continua medindo o p95 do lado da API.
- ➖ O proxy muda o endereço de origem visto pela API. Os limites por IP (RN33 e login) precisam ler o IP do cliente do cabeçalho certo; ver **Endereço IP do cliente**.
- ➖ Um script injetado ainda consegue fazer requisições **a partir da própria página** enquanto ela está aberta. O cookie reduz o estrago (sem exportar o token), mas não substitui evitar XSS.

## Endereço IP do cliente

Antes de mudar o caminho do tráfego, o workflow **Network check** (`scripts/network_check.py`) chamou a API direto e pelo site a partir de um runner do GitHub, em 2026-09-28. O `X-Forwarded-For` que chega à API:

| Caminho | Cadeia (esquerda → direita) |
|---|---|
| Direto | cliente · borda Cloudflare (`162.158.x`) · balanceador do Render (`10.x`) |
| Pelo site | cliente · borda Cloudflare do site (`108.162.x`, duas vezes) · saída do site estático no Render (`74.220.48.207`) · borda Cloudflare da API · balanceador |

A medição revelou um problema que **já existia**: a API usava `request.client.host`, que o uvicorn preenche com o **primeiro** item do `X-Forwarded-For`. Esse item é escrito por quem faz a requisição. Bastava enviar um `X-Forwarded-For` inventado a cada tentativa para escapar dos limites de login, cadastro, códigos e eventos. `CF-Connecting-IP` também não serve: pelo site, ele traz a saída do site estático, igual para todos os usuários.

Regra adotada (`app/client_ip.py`): ler a cadeia **da direita para a esquerda** e pular apenas saltos conhecidos (endereços privados, faixas publicadas da Cloudflare e as redes de `TRUSTED_PROXY_NETWORKS`, que por padrão é a saída medida do site, `74.220.48.0/24`). O primeiro endereço que sobra é o cliente. Tudo o que está à esquerda dele, onde um cliente consegue escrever, é ignorado.

Se o Render mudar a saída do site, o novo salto aparece como "cliente" e todo o tráfego do site divide o mesmo limite. A falha é para o lado seguro (mais restritiva, nunca contornável) e se corrige ajustando `TRUSTED_PROXY_NETWORKS`. O endpoint de diagnóstico continua fora do OpenAPI e agora mostra também `resolved_client_ip`, o endereço que os limites usam, para repetir a medição quando necessário.

## Rastreabilidade

RN33, RN46, RN47, RN48 · RNF10 · T51, T52 · `app/session_cookie.py`, `app/client_ip.py`, `app/auth.py`, `app/routes.py` · frontend: `src/lib/api.ts`, `src/features/auth/AuthContext.tsx`, `render.yaml`, `vite.config.ts`
