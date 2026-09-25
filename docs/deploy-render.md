# Implantação no Render

O arquivo `render.yaml` cria um Web Service gratuito na região de Virgínia,
conectado à branch `main`. Novos deploys automáticos só começam depois que as
verificações do GitHub forem aprovadas.

## Segredos solicitados na primeira implantação

O Blueprint solicita duas URLs do projeto Supabase. Os valores nunca devem ser
incluídos neste repositório.

- `DATABASE_URL`: URL do Session pooler para o login restrito da aplicação,
  membro de `merchant_app_runtime`, com driver `postgresql+psycopg` e
  `sslmode=require`.
- `MIGRATION_DATABASE_URL`: URL de conexão direta do Supabase. Se o Render não
  conseguir alcançar a conexão direta, use também a URL do Session pooler.

Formato esperado:

```text
postgresql+psycopg://USUARIO:SENHA@HOST:5432/postgres?sslmode=require
```

O Render gera `JWT_SECRET` automaticamente. As demais variáveis públicas ficam
declaradas no Blueprint.

`MIGRATION_DATABASE_URL` pode continuar usando `postgres`, pois o Alembic precisa alterar a estrutura. O uso cotidiano da API deve ser feito pela credencial restrita em `DATABASE_URL`; as duas variáveis não devem permanecer iguais após a configuração do papel de produção.

## CORS

`CORS_ALLOWED_ORIGINS` deve conter a origem exata do frontend publicado, sem caminho ou barra final:

```text
CORS_ALLOWED_ORIGINS=https://merchant-app-web.onrender.com
```

A variável não é declarada no `render.yaml`; configure-a em **Environment** no painel do serviço. Sem ela, o navegador bloqueia as chamadas do frontend. Múltiplas origens são separadas por vírgula e curingas não são aceitos.

## E-mail

`EMAIL_DELIVERY` é declarada no `render.yaml` como `disabled`. Nesse modo, contas nascem confirmadas e a recuperação de senha responde `503`. `log` é recusado em produção, e a aplicação não inicia com ele.

Quando um provedor HTTP for implementado, troque o valor **no `render.yaml`**: variáveis com `value` no Blueprint sobrescrevem as do painel a cada sincronização. A chave de API do provedor deve entrar com `sync: false`, como as URLs de banco. Ver [ADR-0011](decisoes/0011-confirmacao-de-conta-por-codigo.md).

## Painel administrativo

`ADMIN_EMAILS` é declarada no `render.yaml` com `sync: false`. Configure-a em **Environment** com os e-mails que podem abrir `/admin`, separados por vírgula (maiúsculas e espaços são ignorados). Vazia, ninguém acessa o painel. A troca exige reiniciar o serviço, o que o Render faz ao salvar a variável.

O commit exibido no painel vem de `RENDER_GIT_COMMIT`, que o Render define sozinho. Ver [ADR-0012](decisoes/0012-painel-e-instrumentacao-propria.md).

## Alertas

O workflow **Production alerts** consulta a API a cada hora e abre uma issue `alerta-producao` quando algum guarda-corpo é violado ([ADR-0015](decisoes/0015-alertas-com-github-actions.md)). Para ativar:

1. Gere um segredo: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. No Render, em **Environment** do serviço da API, crie `ALERTS_TOKEN` com esse valor (declarada no `render.yaml` com `sync: false`).
3. No GitHub, em **Settings → Secrets and variables → Actions** deste repositório, crie o secret `ALERTS_TOKEN` com **o mesmo valor**.
4. Rode o workflow uma vez em **Actions → Production alerts → Run workflow** e confira o resumo.

Sem o secret no GitHub, o workflow só registra um aviso. Com valores diferentes, ele falha avisando do token recusado. Para receber as notificações, acompanhe o repositório (**Watch**) ou mantenha as notificações de issues ativas.

## Inicialização e saúde

Ao iniciar cada deploy, o serviço executa `alembic upgrade head` e somente então
inicia o Uvicorn. O plano usa uma única instância, evitando execuções paralelas
da migração durante o MVP. O Render verifica `GET /health`, que só retorna `200` quando a API e o PostgreSQL
estão disponíveis.

O serviço publicado está disponível em:

```text
GET https://fastapi-merchant-app.onrender.com/health
GET https://fastapi-merchant-app.onrender.com/docs
```

O plano gratuito pode suspender o serviço após inatividade. O primeiro acesso
seguinte pode levar cerca de um minuto, sem perda de dados porque a persistência
está no Supabase.

O workflow `Production smoke test` repete diariamente uma validação somente de leitura e autenticação negativa. Ele nunca cria conta, produto ou avaliação no banco de produção.
