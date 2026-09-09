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

Enquanto não houver frontend, `CORS_ALLOWED_ORIGINS` permanece vazio. Quando a interface for publicada, informe sua origem exata, sem caminho ou barra final. Múltiplas origens são separadas por vírgula e curingas não são aceitos.

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
