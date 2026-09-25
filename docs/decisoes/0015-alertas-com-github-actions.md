# ADR-0015 — Alertas de produção com GitHub Actions e issue automática

- Status: aceita
- Data: 2026-09-25
- Origem: item do [roadmap](../roadmap.md): o painel ([ADR-0012](0012-painel-e-instrumentacao-propria.md)) só mostra problemas quando alguém o abre

## Contexto

O painel mostra erros e latência, mas ninguém é avisado quando um guarda-corpo é violado. O canal óbvio, e-mail, está bloqueado até existir um provedor ([ADR-0011](0011-confirmacao-de-conta-por-codigo.md)). O plano gratuito do Render não oferece alertas por métrica, e o processo hiberna sem tráfego, o que torna um agendador dentro da API pouco confiável.

## Alternativas consideradas

| Tema | Alternativas | Escolha |
|---|---|---|
| Quem dispara a verificação | Agendador dentro da API · serviço externo de uptime · **workflow agendado no GitHub Actions** | Actions: roda mesmo com a API hibernando (e a acorda), é gratuito e já é usado pelo smoke test diário |
| Canal de aviso | E-mail próprio · Slack/Telegram · falhar o workflow · **issue com rótulo `alerta-producao`** | Issue: o GitHub notifica por e-mail e no app sem nenhuma integração nova; fica um registro com início, evolução e fim do incidente. Falhar o job a cada hora geraria um e-mail por hora |
| Autenticação do endpoint | Conta de administração · **segredo compartilhado (`ALERTS_TOKEN`)** | Segredo: o workflow não tem conta nem sessão; comparação em tempo constante; sem o segredo configurado o endpoint responde 404 |
| O que alarmar | Todos os indicadores · **guarda-corpos operacionais com volume mínimo** | Banco, erros 5xx, p95 da busca e erros no navegador. Indicadores de produto (ativação, North Star) variam devagar e ficam no painel |

## Decisão

- `evaluate_alerts` avalia a **última hora**:
  - banco respondendo;
  - erros 5xx abaixo de 5%;
  - p95 da busca ≤ 800 ms (guarda-corpo da [visão](../visao-produto.md#7-métricas-de-sucesso));
  - menos de 5 sessões com erro no navegador.
- As verificações de 5xx e p95 só alarmam com **pelo menos 20 requisições** na janela; abaixo disso aparecem como "volume insuficiente".
- O resultado aparece no painel ("Saúde agora") e em `GET /api/v1/internal/alerts`, fora do OpenAPI e protegido por `X-Alerts-Token`.
- `.github/workflows/alerts.yml` roda a cada hora (`43 * * * *`). O script `scripts/check_alerts.py` espera o Render acordar e mantém **uma única issue aberta**:
  - cria a issue quando algo é violado, o que gera a notificação;
  - enquanto o problema dura, só atualiza o corpo, sem novas notificações;
  - comenta e fecha a issue quando tudo normaliza.
- API sem resposta após 4 tentativas também abre a issue. Token recusado falha o workflow (configuração errada). Sem o secret no GitHub, o workflow só registra um aviso.

## Consequências

- ➕ Problemas chegam ao responsável sem abrir o painel e sem provedor de e-mail.
- ➕ Cada incidente vira uma issue com histórico; fechamento automático mostra quanto durou.
- ➕ A verificação horária mantém a API acordada por alguns minutos, sem custo no plano gratuito.
- ➖ Resolução de até uma hora: um pico curto entre duas verificações pode não ser visto (o painel continua mostrando).
- ➖ O agendamento do GitHub Actions pode atrasar em horários de pico e é pausado após 60 dias sem commits no repositório.
- ➖ O segredo precisa ser igual em dois lugares (Render e GitHub).

## Rastreabilidade

RF21 · RN44, RN45 · UC18 · US17 · T50 · `app/alerts.py`, `scripts/check_alerts.py`, `.github/workflows/alerts.yml`
