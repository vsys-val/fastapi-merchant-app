# ADR-0011 — Confirmação de conta e recuperação de senha por código

- Status: aceita
- Data: 2026-09-24
- Origem: pedido de produto para impedir contas criadas em massa por bots e oferecer recuperação de senha
- Complementa: [ADR-0010](0010-autenticacao-propria.md), que deixou recuperação de senha como consequência pendente

## Contexto

Qualquer pessoa, ou script, podia criar contas ilimitadas com e-mails inventados. Como o catálogo é comunitário ([ADR-0004](0004-catalogo-canonico-comunitario.md)) e os indicadores dependem de "uma pessoa, uma avaliação" ([ADR-0007](0007-avaliacao-unica-sem-historico.md)), contas falsas em massa poderiam poluir o catálogo e distorcer os indicadores. Também não existia recuperação de senha: quem esquecia a senha perdia a própria memória de compras.

O MVP roda no plano gratuito do Render, que bloqueia portas SMTP, e ainda **não há provedor de e-mail escolhido**.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Formato da prova de posse do e-mail | Link mágico · **código de 6 dígitos** | Código: funciona no PWA instalado sem trocar de aplicativo, é fácil de digitar no celular e não depende de roteamento de URL |
| O que a conta pendente pode fazer | Entrar e só ler · **não entrar até confirmar** | Não entrar: contas de bot nunca obtêm token e não escrevem nada |
| Anti-bot adicional | CAPTCHA (Turnstile) · **limite por IP** | Limite por IP: sem dependência externa, reaproveita o mecanismo atômico do login. CAPTCHA fica como evolução |
| Revogar sessões na troca de senha | Lista de tokens revogados · instante de corte por `iat` · **versão de sessão no token** | Versão: exata (o `iat` tem resolução de segundos, e um token do mesmo segundo escaparia) e sem tabela extra |
| Sem provedor de e-mail | Bloquear o deploy · **desligar a confirmação por configuração** | Desligar: o merge não quebra o cadastro em produção |

## Decisão

- **Códigos:** 6 dígitos gerados com `secrets`, de uso único, válidos por 15 min, invalidados após 5 erros e reenviáveis após 60 s. Só o HMAC (usuário + finalidade + código) é armazenado.
- **Conta pendente:** não obtém token. O `403 email_not_verified` só aparece depois que a senha confere. O e-mail fica reservado por 24 h; depois disso, um novo cadastro substitui a conta pendente, que não pode ter dados.
- **Recuperação de senha:** código enviado ao e-mail. A troca também confirma o e-mail e incrementa a versão de sessão, derrubando todos os tokens anteriores.
- **Anti-enumeração:** reenvio e pedido de recuperação sempre respondem `202`. O e-mail é enviado em segundo plano, depois da resposta.
- **Limites por IP:** 10 cadastros, 30 tentativas de código e 10 pedidos de e-mail por hora.
- **Entrega plugável:** `EMAIL_DELIVERY=disabled | log`. Com `disabled`, as contas nascem confirmadas e a recuperação responde `503`. `log` é só para desenvolvimento e é recusado em produção. Um provedor HTTP real entra como nova implementação de `EmailSender`.

## Consequências

- ➕ Em produção com provedor configurado, cada conta exige um e-mail real.
- ➕ Pré-sequestro neutralizado: se alguém cadastra o e-mail de outra pessoa, a dona recupera a conta pela recuperação de senha e a senha do invasor deixa de valer.
- ➕ Contas existentes foram marcadas como confirmadas na migração `0006`, sem impacto para quem já usa.
- ➖ **Até existir provedor de e-mail, a produção continua sem confirmação** (só com o limite por IP) e sem recuperação de senha. Configurar o provedor é o primeiro item do [roadmap](../roadmap.md).
- ➖ Uma etapa a mais no cadastro. Mitigação: confirmar já autentica, sem pedir a senha de novo.
- ➖ Limite por IP pode atingir redes compartilhadas (NAT). Os valores foram escolhidos com folga e podem ser ajustados.

## Rastreabilidade

RF16–RF18 · RN29–RN34 · RNF07 · UC15, UC16 · T34–T40 · `app/verification.py`, `app/email.py`, `app/auth.py`, migração `0006`
