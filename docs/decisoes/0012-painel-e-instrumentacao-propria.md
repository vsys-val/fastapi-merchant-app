# ADR-0012 — Painel administrativo com instrumentação própria

- Status: aceita
- Data: 2026-09-24
- Origem: pedido de produto por um painel que mostre o estado geral da aplicação (frontend e backend) com dados, e não só impressão
- Relaciona-se com: [visão de produto §7](../visao-produto.md#7-métricas-de-sucesso), que definia as métricas sem nenhuma coleta

## Contexto

A [visão de produto](../visao-produto.md#7-métricas-de-sucesso) define uma North Star, métricas de entrada e guarda-corpos com metas, mas **nenhuma era medida**. Os logs do Render (plano gratuito) guardam poucos dias e não respondem perguntas como "quantas buscas acham algo?" ou "qual rota ficou lenta ontem?". Também não havia como saber qual versão do frontend as pessoas estavam usando, nem quais erros aconteciam no navegador.

Restrições: plano gratuito do Render (sem shell, processo único que hiberna), Supabase como único banco, nenhum orçamento para ferramentas pagas, e a promessa de privacidade de um app pessoal de compras.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Onde medir o uso | Ferramenta de terceiros (GA, PostHog, Plausible) · **eventos próprios no Postgres** | Próprios: sem script externo (a CSP continua estrita), sem enviar dados a terceiros, e as métricas cruzam com as tabelas de negócio numa só consulta |
| Métricas técnicas | Log por requisição · APM externo · **agregado em memória por minuto, gravado a cada 30 s** | Agregado: uma escrita a cada 30 s, e não uma por requisição; latência em faixas fixas permite p95 somável entre minutos e rotas |
| Quem é administrador | Coluna/papel no banco · **lista em `ADMIN_EMAILS`** | Variável: no plano gratuito não há shell para promover alguém, e não existe tela que possa se autopromover |
| Onde fica o painel | App separado · **rota `/admin` do mesmo frontend** | Mesma rota: reaproveita autenticação, deploy e CSP; quem não administra nem dispara a consulta |
| Cálculo dos números | Tabelas pré-agregadas · **SQL sob demanda** | Sob demanda: o volume atual responde 90 dias em ~65 ms (medido); pré-agregar fica para quando a latência medida pedir |

## Decisão

- **Eventos de uso** (`POST /events`): lista fechada de 11 nomes, até 8 propriedades escalares, lotes de até 20 eventos e 120 lotes por IP por hora. A interface nunca envia texto digitado, e-mail ou query string. Os eventos ficam desligados fora do build de produção, em navegadores automatizados e com *Do Not Track*. A sessão é um UUID anônimo por aba; o usuário só é associado quando o token é válido.
- **Métricas de requisição:** middleware que registra método, template da rota (nunca o caminho com IDs), classe de status e faixa de latência. Ignora `/health` e `OPTIONS`. Falha ao gravar só gera log e devolve os dados ao buffer.
- **Retenção:** 90 dias para métricas e 180 dias para eventos, aplicada pelo próprio processo no máximo uma vez por hora.
- **Painel** (`GET /admin/overview`): um único endpoint devolve saúde atual, métricas de produto com meta e estado, crescimento diário, catálogo, operação da API e frontend. Os dias seguem o fuso de São Paulo.
- **Versões:** a API informa `RENDER_GIT_COMMIT` e o frontend envia o commit do build no `app_loaded`, para comparar o que está no ar com o que as pessoas usam.

## Consequências

- ➕ Todas as métricas da visão de produto passam a ter número e meta visível, e as hipóteses H1 e H2 podem ser verificadas.
- ➕ Nenhum dado pessoal sai da infraestrutura do produto; a CSP não ganhou nenhuma origem.
- ➕ Erros do navegador, antes invisíveis, aparecem agrupados por mensagem.
- ➖ Com *Do Not Track* ou bloqueadores, o uso fica subestimado. Os totais de negócio (contas, produtos, avaliações) vêm das tabelas e não sofrem esse efeito.
- ➖ Um processo que cai perde até 30 s de métricas técnicas. Aceitável para tendências; não serve para auditoria.
- ➖ O p95 é aproximado pelo limite superior da faixa (ex.: "≤ 400 ms"), não pelo valor exato.
- ➖ Trocar administradores exige alterar uma variável e reiniciar o serviço.

## Rastreabilidade

RF19, RF20 · RN35–RN40 · RNF08, RNF09 · UC17 · US16 · T41–T46 · `app/admin.py`, `app/events.py`, `app/observability.py`, migração `0007`
