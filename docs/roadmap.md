# Roadmap

Formato **Agora / Próximo / Depois**: horizontes de prioridade, sem datas prometidas. Cada item diz qual problema resolve, qual métrica ou hipótese da [visão de produto](visao-produto.md) ele move e de onde vem (requisito, ADR ou lacuna da [rastreabilidade](rastreabilidade.md)).

## Critério de priorização

Os itens foram ordenados por **impacto no ciclo central** (buscar → decidir → avaliar → lembrar) dividido pelo **esforço estimado**, com prioridade para:

1. lacunas que impedem medir o valor (sem dados não há decisão de produto);
2. lacunas entre o que a API já garante e o que o usuário consegue fazer;
3. riscos que crescem com o uso (escala, abuso, segurança).

| Impacto | Esforço | Leitura |
|---|---|---|
| Alto | P | Fazer já |
| Alto | M/G | Planejar como aposta |
| Baixo | P | Encaixar quando houver folga |
| Baixo | G | Não fazer até haver evidência |

## ✅ Entregue — MVP

- API completa (RF01–RF15) com 127 testes, CI em PostgreSQL 17 e smoke test diário em produção.
- Web/PWA mobile-first com busca, detalhe, avaliação em três etapas, área pessoal e lembretes.
- Endurecimento de produção: rate limiting, RLS, papel de mínimo privilégio, CORS explícito e CSP.

## ✅ Entregue — pós-MVP

- Atalho para o produto já cadastrado quando o cadastro é duplicado ([ADR-0004](decisoes/0004-catalogo-canonico-comunitario.md)).
- Confirmação de conta por código, recuperação de senha, encerramento de sessões na troca de senha e limite de cadastros por IP ([ADR-0011](decisoes/0011-confirmacao-de-conta-por-codigo.md)). A confirmação fica **inativa em produção** até o provedor de e-mail ser configurado.

## 🟢 Agora — medir e fechar o ciclo

| Item | Problema | Move | Origem | Impacto / Esforço |
|---|---|---|---|---|
| Escolher e configurar o provedor de e-mail (ex.: Brevo ou Resend) e implementar o `EmailSender` HTTP | Sem provedor, a produção não exige confirmação de conta e não oferece recuperação de senha | RNF07; risco R2 | [ADR-0011](decisoes/0011-confirmacao-de-conta-por-codigo.md) | Alto / P |
| Instrumentação de eventos (busca, abertura de produto, etapas da avaliação, publicação) | Hoje não é possível calcular nenhuma métrica da visão | Todas as métricas; valida H1 e H2 | [Métricas](visao-produto.md#7-métricas-de-sucesso) | Alto / M |
| Busca combinada e filtro por categoria na interface | A API aceita nome + marca + categoria; a tela aceita um campo por vez | % de buscas com resultado | RF04 ◐ | Médio / P |
| Tela de correção de produto | Erros de cadastro não podem ser corrigidos pelo usuário | Qualidade do catálogo | RF07 ⚠️, [ADR-0005](decisoes/0005-bloqueio-de-edicao-apos-avaliacao.md) | Médio / P |

## 🔵 Próximo — escala e confiança

| Item | Problema | Move | Origem | Impacto / Esforço |
|---|---|---|---|---|
| Busca no banco com `pg_trgm` + `unaccent` | `search_products` carrega o catálogo ativo em memória | Latência p95 da busca; risco R3 | [Visão §8](visao-produto.md#8-hipóteses-e-riscos) | Alto / M |
| Motivos agregados no detalhe ("o que mais elogiam / criticam") | Os motivos existem nos dados, mas não aparecem para a comunidade | Valor para a persona Bruno; valida H3 | [ADR-0003](decisoes/0003-motivos-estruturados-obrigatorios.md) | Alto / M |
| Leitura de código de barras pela câmera | Digitar 13 dígitos no corredor é lento | Tempo até a decisão; buscas por GTIN | JTBD da persona Ana | Alto / M |
| Sessão em cookie HttpOnly | O token em `localStorage` fica exposto a XSS | Segurança | Arquitetura do frontend | Médio / M |
| Exclusão de produto pela interface | Cadastros indevidos só saem pela API | Qualidade do catálogo | RF13 ◐ | Baixo / P |

## 🟣 Depois — apostas que dependem de evidência

| Item | Hipótese que precisa ser confirmada antes |
|---|---|
| Critérios específicos por categoria (ex.: "espuma" para limpeza) | Uso alto de `other` e comentários recorrentes por categoria (H3) |
| Histórico da avaliação ("mudou depois da nova fórmula") | Usuários editam avaliações antigas com frequência |
| Denúncia e moderação de avaliações e de produtos duplicados | Volume de conteúdo abusivo ou de duplicatas deixa de ser tratável manualmente |
| Mesclagem administrativa de duplicatas | Taxa de duplicatas acima do guarda-corpo |
| Listas de compras a partir de "compraria de novo" | O ciclo de memória está validado e os usuários pedem planejamento |
| Imagens de produto | Existe fonte licenciada ou fluxo de moderação de fotos |
| Cache de indicadores | O cálculo sob demanda se torna gargalo medido |
| CAPTCHA invisível (ex.: Cloudflare Turnstile) no cadastro | Cadastros automatizados continuam passando pela confirmação de e-mail e pelo limite por IP |
| Limpeza periódica de contas pendentes expiradas | O volume de contas pendentes abandonadas passa a pesar no banco (hoje, elas só são substituídas quando o e-mail é recadastrado) |

## Fora do produto

Comparação de preços entre lojas, promoções e marketplace. É outro problema e outro produto ([anti-persona](visao-produto.md#anti-persona)).
