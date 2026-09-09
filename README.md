# FastAPI Merchant App

API planejada para catálogo compartilhado de produtos e avaliações de consumidores.

## Estado

As entregas 1–8 do backend do MVP estão consolidadas na branch `main`: estrutura/configuração, persistência PostgreSQL, validação, autenticação própria, produtos, avaliações, consultas, observabilidade básica e automação de testes. A API está publicada no Render e usa PostgreSQL hospedado no Supabase.

- API: https://fastapi-merchant-app.onrender.com
- Swagger: https://fastapi-merchant-app.onrender.com/docs
- Saúde: https://fastapi-merchant-app.onrender.com/health

## Documentação

- [Requisitos](docs/requisitos.md)
- [Casos de uso](docs/casos-de-uso.md)
- [Contrato da API](docs/contrato-api.md)
- [Modelo de banco](docs/modelo-banco.md)
- [Diagrama ER](docs/diagrama-er.puml)
- [Classes](docs/uml-classes.puml)
- [Diagrama de casos de uso](docs/uml-casos-de-uso.puml)
- [Matriz mínima de testes](docs/matriz-testes.md)
- [Plano de implementação](docs/plano-implementacao.md)

## Executar o MVP

Use Python 3.12 e execute os comandos na raiz do repositório, na branch `main`.

### Windows (PowerShell)

```powershell
git fetch origin
git switch feat/estrutura-inicial
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie a chave gerada para `JWT_SECRET` no arquivo `.env`. O arquivo é local e ignorado pelo Git. Se já tiver um `.env`, preserve-o e apenas confira os campos do exemplo.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload
```

### Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp -n .env.example .env
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Preencha `JWT_SECRET` antes de iniciar:

```bash
.venv/bin/python -m uvicorn app.main:create_app --factory --reload
```

Acesse http://127.0.0.1:8000/docs. A documentação interativa expõe o contrato completo e a autenticação Bearer. `GET /health` verifica a aplicação e a conexão com o banco; a raiz não possui endpoint. A URL do banco é validada sintaticamente. Para criar ou atualizar as tabelas, com o PostgreSQL em execução, use: `./.venv/bin/python -m alembic upgrade head` (PowerShell: `.\\.venv\\Scripts\\python.exe -m alembic upgrade head`). Para conferir a revisão sem conectar: `./.venv/bin/python -m alembic heads`.

As URLs de banco destinam-se ao ambiente de desenvolvimento. A chave JWT é obrigatória para login e emissão de tokens e deve ser gerada aleatoriamente; comprimento sozinho não garante segurança.

### Usar Supabase

O Supabase fornece o PostgreSQL hospedado; a aplicação continua acessando o banco com SQLAlchemy e Psycopg, sem usar o cliente Supabase ou o Supabase Auth.

1. Crie um projeto exclusivo de desenvolvimento no Supabase.
2. No botão **Connect**, copie a URL do **Session pooler** para `DATABASE_URL`. Ela funciona em redes IPv4 e usa a porta 5432.
3. Copie a **Direct connection** para `MIGRATION_DATABASE_URL`. Ela é a opção preferida para Alembic, mas exige IPv6 no plano sem o adicional IPv4. Se sua rede não alcançar IPv6, use a URL do Session pooler também para migrações.
4. Nas duas URLs, troque o início `postgresql://` por `postgresql+psycopg://` e acrescente `?sslmode=require`.
5. Guarde as URLs apenas no `.env` ou em segredos do ambiente. Não envie a senha pelo chat nem faça commit do arquivo.
6. Execute `.\\.venv\\Scripts\\python.exe -m alembic upgrade head` no PowerShell.

As migrações ativam RLS nas quatro tabelas de negócio, na tabela interna `limites_login` e na tabela técnica `alembic_version`. Não existem políticas para os papéis públicos do Supabase; `anon` e `authenticated` também não possuem privilégios sobre as duas tabelas internas. O acesso de usuários passa pelos endpoints e pelo JWT da nossa API.

Em produção, `MIGRATION_DATABASE_URL` permanece com o papel administrativo usado pelo Alembic. `DATABASE_URL` deve usar um login próprio que seja membro de `merchant_app_runtime`. Esse papel coletivo recebe somente operações de dados nas cinco tabelas operacionais e não acessa `alembic_version` nem altera a estrutura do banco.

### CORS

`CORS_ALLOWED_ORIGINS` contém as origens exatas autorizadas a chamar a API a partir de um navegador, separadas por vírgula. Enquanto não houver frontend, o valor deve permanecer vazio. Não use `*`.

```text
CORS_ALLOWED_ORIGINS=https://app.exemplo.com,http://localhost:5173
```

### Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Em Linux/macOS: `.venv/bin/python -m pytest -q`.

A suíte cobre cadastro, autenticação, privacidade, limites de tentativa, mutações, consultas, saúde, OpenAPI e uma jornada integrada completa. Dois testes adicionais executam transações realmente concorrentes no PostgreSQL 17 efêmero do GitHub Actions. Os testes usam valores fictícios e não gravam dados permanentes.

O workflow `Production smoke test` executa diariamente uma verificação não destrutiva da API publicada. Ele confere saúde, banco, OpenAPI, catálogo e bloqueio de mutações sem autenticação, sem criar usuários ou produtos.

### Validação desta entrega

Sintaxe Python conferida, dependências diretas fixadas, `pip check` sem conflitos e 125 testes locais aprovados; dois testes PostgreSQL adicionais são executados no CI, totalizando 127. Os fluxos foram validados no Supabase com transações revertidas e a jornada HTTP completa foi automatizada. Nenhum dado de teste permaneceu.

## Como os arquivos se conectam

| Arquivo | Função |
|---|---|
| app/main.py | Cria a aplicação que o servidor Uvicorn recebe |
| app/config.py | Lê e valida a configuração local/ambiente; protege a exibição de segredos |
| app/database.py | Cria engine e sessões PostgreSQL sob demanda |
| app/models.py | Mapeia as quatro tabelas e suas restrições |
| app/validation.py | Normaliza textos, medidas, GTIN e chaves de identidade |
| app/schemas.py | Define e valida os corpos de criação e PATCH |
| app/errors.py | Padroniza o envelope público de erros |
| app/security.py | Aplica política e hash Argon2id de senha e assina/valida JWT |
| app/auth.py | Implementa cadastro, login e resolução do usuário autenticado |
| app/rate_limit.py | Mantém limites atômicos de login no PostgreSQL |
| app/catalog.py | Implementa pesquisa, paginação, detalhes, indicadores e listas pessoais |
| app/products.py | Implementa criação, edição, exclusão lógica e reativação de produtos |
| app/reviews.py | Implementa criação, edição e exclusão transacional de avaliações e motivos |
| app/routes.py | Expõe as rotas funcionais sob `/api/v1` |
| app/health.py | Verifica a aplicação e a conexão com o banco em `/health` |
| .github/workflows/tests.yml | Executa a suíte com PostgreSQL 17 efêmero no GitHub Actions |
| .github/workflows/smoke-test.yml | Valida diariamente a API publicada sem gravar dados |
| scripts/smoke_test.py | Implementa o smoke test não destrutivo de produção |
| alembic/ | Mantém as migrações versionadas do banco |
| .env.example | Documenta as variáveis necessárias; copiar para .env |
| requirements.txt | Dependências diretas fixadas da aplicação |
| requirements-dev.txt | Dependências de teste fixadas |
| tests/test_bootstrap.py | Verifica a inicialização e a configuração |
| pyproject.toml | Metadados e configuração do pytest |

Fluxo de inicialização: Uvicorn chama `create_app`, a configuração é validada e a instância FastAPI é criada. Configuração inválida interrompe esse fluxo com os nomes dos campos a corrigir.

Referências técnicas: [primeiros passos do FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [execução com Uvicorn](https://fastapi.tiangolo.com/deployment/manually/) e [configuração com Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

O backend do MVP está publicado com HTTPS, segredos de ambiente e persistência no Supabase. A migração `0005_runtime_role` prepara o papel de mínimo privilégio da aplicação; a troca da credencial no Render é uma etapa operacional separada para que nenhuma senha seja registrada no repositório.
