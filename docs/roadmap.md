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

- Busca combinando nome, marca e categoria na interface, com os filtros na URL (RF04).
- Correção de produto pelo responsável, com o bloqueio de RN13 avisado antes do formulário (RF07).
- Atalho para o produto já cadastrado quando o cadastro é duplicado ([ADR-0004](decisoes/0004-catalogo-canonico-comunitario.md)).
- Confirmação de conta por código, recuperação de senha, encerramento de sessões na troca de senha e limite de cadastros por IP ([ADR-0011](decisoes/0011-confirmacao-de-conta-por-codigo.md)). A confirmação fica **inativa em produção** até o provedor de e-mail ser configurado.
- Painel administrativo `/admin` com eventos de uso próprios e métricas técnicas da API: North Star, funil da avaliação, catálogo, latência por rota e erros do navegador ([ADR-0012](decisoes/0012-painel-e-instrumentacao-propria.md)).
- Leitura de código de barras pela câmera na busca e no cadastro, com leitor nativo ou ZXing sob demanda ([ADR-0014](decisoes/0014-leitura-de-codigo-de-barras-pela-camera.md)).
- Busca no banco com índices de trigramas: ~970 ms → ~10 ms com 50 mil produtos, e sugestões para erros de digitação ([ADR-0013](decisoes/0013-busca-no-banco-com-trigramas.md)).
- "O que a comunidade destaca" no detalhe: aspectos mais elogiados e mais criticados, e os motivos de cada avaliação visíveis na lista ([ADR-0003](decisoes/0003-motivos-estruturados-obrigatorios.md)).

## 🟢 Agora — medir e fechar o ciclo

| Item | Problema | Move | Origem | Impacto / Esforço |
|---|---|---|---|---|
| Escolher e configurar o provedor de e-mail (ex.: Brevo ou Resend) e implementar o `EmailSender` HTTP | Sem provedor, a produção não exige confirmação de conta e não oferece recuperação de senha | RNF07; risco R2 | [ADR-0011](decisoes/0011-confirmacao-de-conta-por-codigo.md) | Alto / P |
| Ler o painel por 2–4 semanas e recalibrar as metas da visão | As metas são hipóteses; agora existem dados | Todas as métricas; valida H1 e H2 | [ADR-0012](decisoes/0012-painel-e-instrumentacao-propria.md) | Alto / P |
| Alertas: aviso quando a taxa de 5xx ou o p95 passar do guarda-corpo | O painel só mostra problemas quando alguém abre | Latência p95; disponibilidade | [ADR-0012](decisoes/0012-painel-e-instrumentacao-propria.md) | Médio / P |

## 🔵 Próximo — escala e confiança

| Item | Problema | Move | Origem | Impacto / Esforço |
|---|---|---|---|---|
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
