# Merchant — API

[![Tests](https://github.com/vsys-val/fastapi-merchant-app/actions/workflows/tests.yml/badge.svg)](https://github.com/vsys-val/fastapi-merchant-app/actions/workflows/tests.yml)
[![Production smoke test](https://github.com/vsys-val/fastapi-merchant-app/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/vsys-val/fastapi-merchant-app/actions/workflows/smoke-test.yml)

**A memória de compras de quem vai ao mercado.** O Merchant responde, no corredor, à pergunta *"eu compraria isto de novo?"* com a sua própria experiência em destaque e a da comunidade ao lado.

Este repositório contém a API (FastAPI + PostgreSQL) e **toda a documentação de produto e requisitos**. A interface web/PWA está em [vsys-val/merchant-app-web](https://github.com/vsys-val/merchant-app-web).

| | |
|---|---|
| 🛒 **Aplicação** | [merchant-app-web.onrender.com](https://merchant-app-web.onrender.com) |
| 📘 **API (Swagger)** | [fastapi-merchant-app.onrender.com/docs](https://fastapi-merchant-app.onrender.com/docs) |
| 💓 **Saúde** | [fastapi-merchant-app.onrender.com/health](https://fastapi-merchant-app.onrender.com/health) |

> O plano gratuito do Render hiberna após inatividade; o primeiro acesso pode levar cerca de um minuto.

## O problema e a abordagem

A experiência com um produto acontece em casa. A próxima decisão de compra acontece no corredor, dias depois e com pressa. Entre as duas, a memória falha, e notas de 1 a 5 estrelas não dizem **por que** algo foi bom ou ruim.

| Decisão de produto | Em vez de | Por quê |
|---|---|---|
| **"Compraria de novo?"** como resumo | Nota geral | É a própria decisão que o usuário precisa tomar ([ADR-0002](docs/decisoes/0002-intencao-de-recompra-como-resumo.md)) |
| **Critérios semânticos** (qualidade, expectativa, custo-benefício) | Escalas numéricas | Cada resposta tem significado explícito e vale para qualquer categoria ([ADR-0001](docs/decisoes/0001-avaliacao-estruturada-sem-nota.md)) |
| **Motivo obrigatório** (aspecto + positivo/negativo) | Comentário livre | Agregável, rápido de marcar e evita avaliações acidentais ([ADR-0003](docs/decisoes/0003-motivos-estruturados-obrigatorios.md)) |
| **Sua experiência separada** da comunidade | Uma média só | A opinião pessoal não é diluída nem contamina a estatística ([ADR-0006](docs/decisoes/0006-avaliacao-pessoal-separada.md)) |
| **Catálogo comunitário canônico** com deduplicação | Catálogo curado ou privado | Escala sem operação e soma avaliações no mesmo item ([ADR-0004](docs/decisoes/0004-catalogo-canonico-comunitario.md)) |

## Documentação

A documentação segue o caminho **problema → decisões → requisitos → especificação → testes → entrega**, com IDs rastreáveis entre os artefatos. Comece pelo [índice](docs/README.md).

| Produto | Requisitos e especificação | Qualidade e operação |
|---|---|---|
| [Visão de produto](docs/visao-produto.md): personas, JTBD, métricas, riscos | [Requisitos](docs/requisitos.md): 20 RF · 41 RN · 9 RNF | [Matriz de testes](docs/matriz-testes.md): T01–T47 |
| [Decisões (ADRs)](docs/decisoes/README.md): 11 trade-offs registrados | [Histórias de usuário](docs/historias-usuario.md) com critérios Gherkin | [Rastreabilidade](docs/rastreabilidade.md): requisito → teste → tela |
| [Roadmap](docs/roadmap.md): agora · próximo · depois | [Casos de uso](docs/casos-de-uso.md) · [Contrato da API](docs/contrato-api.md) | [Plano de implementação](docs/plano-implementacao.md) |
| [Glossário](docs/glossario.md) · [Ideação](docs/ideacao.md) | [Modelo de dados](docs/modelo-banco.md) · [Diagramas](docs/diagramas.md) | [Deploy no Render](docs/deploy-render.md) |

## Estado

MVP concluído e em produção (entregas 1–9 do [plano](docs/plano-implementacao.md)): configuração protegida, PostgreSQL com migrações, validação e normalização, autenticação própria, produtos, avaliações, consultas, observabilidade básica, CI e endurecimento de produção. Depois do MVP vieram a confirmação de conta por código, a recuperação de senha e o limite de cadastros por IP ([ADR-0011](docs/decisoes/0011-confirmacao-de-conta-por-codigo.md)), e depois o painel administrativo com métricas de uso e de operação ([ADR-0012](docs/decisoes/0012-painel-e-instrumentacao-propria.md)). Os 20 requisitos funcionais estão implementados e cobertos por 165 testes automatizados. As lacunas de interface estão na [rastreabilidade](docs/rastreabilidade.md) e priorizadas no [roadmap](docs/roadmap.md).

## Executar o MVP

Use Python 3.12 e execute os comandos na raiz do repositório, na branch `main`.

### Windows (PowerShell)

```powershell
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

Em produção, `MIGRATION_DATABASE_URL` permanece com o papel administrativo usado pelo Alembic. `DATABASE_URL` deve usar um login próprio que seja membro de `merchant_app_runtime`. Esse papel coletivo recebe somente operações de dados nas tabelas operacionais e não acessa `alembic_version` nem altera a estrutura do banco.

### CORS

`CORS_ALLOWED_ORIGINS` contém as origens exatas autorizadas a chamar a API a partir de um navegador, separadas por vírgula. Vazio desativa o CORS. Localmente, informe a origem do servidor de desenvolvimento do frontend; em produção, a origem publicada do [merchant-app-web](https://merchant-app-web.onrender.com). Não use `*`.

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

Sintaxe Python conferida, dependências diretas fixadas, `pip check` sem conflitos e 141 testes locais aprovados; 11 testes adicionais usam o PostgreSQL efêmero do CI, totalizando 152. Os fluxos foram validados no Supabase com transações revertidas e a jornada HTTP completa foi automatizada. Nenhum dado de teste permaneceu.

## Como os arquivos se conectam

| Arquivo | Função |
|---|---|
| app/main.py | Cria a aplicação que o servidor Uvicorn recebe |
| app/config.py | Lê e valida a configuração local/ambiente; protege a exibição de segredos |
| app/database.py | Cria engine e sessões PostgreSQL sob demanda |
| app/models.py | Mapeia as tabelas de negócio, as técnicas (`limites_login`, eventos e métricas) e suas restrições |
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
| app/observability.py | Agrega métricas de requisição em memória e as grava a cada 30 s |
| app/events.py | Valida e grava os eventos de uso enviados pela interface |
| app/admin.py | Controla o acesso de administração e calcula o painel `/admin/overview` |
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
