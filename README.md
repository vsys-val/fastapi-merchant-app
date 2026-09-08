# FastAPI Merchant App

API planejada para catálogo compartilhado de produtos e avaliações de consumidores.

## Estado

Planejamento consolidado na branch `docs/casos-de-uso`. Estrutura inicial em `feat/estrutura-inicial`: fábrica da aplicação FastAPI e configuração por ambiente. Os testes de inicialização foram preparados localmente e passaram; a publicação do arquivo de testes foi bloqueada pelo limite automático de uso da conexão GitHub. Banco definido: PostgreSQL; conexão e migrações ainda não implementadas.

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

## Executar esta primeira etapa

Use Python 3.12. Execute os comandos na raiz do repositório, na branch `feat/estrutura-inicial`.

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

Acesse http://127.0.0.1:8000/docs. Nesta etapa, a documentação abre sem operações de negócio. A raiz e `/health` ainda não possuem endpoints. A URL do banco é validada sintaticamente. Para criar ou atualizar as tabelas, com o PostgreSQL em execução, use: `./.venv/bin/python -m alembic upgrade head` (PowerShell: `.\\.venv\\Scripts\\python.exe -m alembic upgrade head`). Para conferir a revisão sem conectar: `./.venv/bin/python -m alembic heads`.

O exemplo de DATABASE_URL é somente para desenvolvimento e será ajustado à instância PostgreSQL na próxima entrega. A chave JWT já é exigida para preparar a configuração, mas login e emissão de tokens ainda não existem. Uma chave longa deve ser gerada aleatoriamente: comprimento sozinho não garante segurança.

### Usar Supabase

O Supabase fornece o PostgreSQL hospedado; a aplicação continua acessando o banco com SQLAlchemy e Psycopg, sem usar o cliente Supabase ou o Supabase Auth.

1. Crie um projeto exclusivo de desenvolvimento no Supabase.
2. No botão **Connect**, copie a URL do **Session pooler** para `DATABASE_URL`. Ela funciona em redes IPv4 e usa a porta 5432.
3. Copie a **Direct connection** para `MIGRATION_DATABASE_URL`. Ela é a opção preferida para Alembic, mas exige IPv6 no plano sem o adicional IPv4. Se sua rede não alcançar IPv6, use a URL do Session pooler também para migrações.
4. Nas duas URLs, troque o início `postgresql://` por `postgresql+psycopg://` e acrescente `?sslmode=require`.
5. Guarde as URLs apenas no `.env` ou em segredos do ambiente. Não envie a senha pelo chat nem faça commit do arquivo.
6. Execute `.\\.venv\\Scripts\\python.exe -m alembic upgrade head` no PowerShell.

A migração ativa RLS nas quatro tabelas e não cria políticas para os papéis públicos do Supabase. O acesso de usuários continuará passando pelos endpoints e pelo JWT da nossa API.

### Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Em Linux/macOS: `.venv/bin/python -m pytest -q`.

Quando publicado, o arquivo de testes cobrirá inicialização, ausência e validade de configuração, prioridade das variáveis de ambiente e ausência de segredos na mensagem de erro/representação. A execução local atual passou em 7 cenários; o arquivo ainda precisa ser adicionado à branch. Usam valores fictícios, diretório temporário e nenhum banco.

### Validação desta entrega

Sintaxe Python e TOML conferida. As dependências foram instaladas no ambiente local e os 9 testes de inicialização e configuração passaram. O arquivo de testes ainda não foi publicado na branch porque a conexão GitHub recusou essa operação por limite automático de uso. As faixas de dependências são iniciais, sem lock de versões. Concluir instalação e testes antes de considerar a entrega 1 aprovada.

## Como os arquivos se conectam

| Arquivo | Função |
|---|---|
| app/main.py | Cria a aplicação que o servidor Uvicorn recebe |
| app/config.py | Lê e valida a configuração local/ambiente; protege a exibição de segredos |
| app/database.py | Cria engine e sessões PostgreSQL sob demanda |
| app/models.py | Mapeia as quatro tabelas e suas restrições |
| alembic/ | Mantém a migração inicial do banco |
| .env.example | Documenta as variáveis necessárias; copiar para .env |
| requirements.txt | Dependências da aplicação |
| requirements-dev.txt | Inclui também as ferramentas de teste |
| tests/test_bootstrap.py | Verifica a inicialização e a configuração |
| pyproject.toml | Metadados e configuração do pytest |

Fluxo de inicialização: Uvicorn chama `create_app`, a configuração é validada e a instância FastAPI é criada. Configuração inválida interrompe esse fluxo com os nomes dos campos a corrigir.

Referências técnicas: [primeiros passos do FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [execução com Uvicorn](https://fastapi.tiangolo.com/deployment/manually/) e [configuração com Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

Banco Supabase de desenvolvimento migrado até `0002_product_owner_index` e validado com teste transacional revertido. Próximo passo: conectar os repositórios e endpoints aos modelos, começando pelo cadastro e autenticação.

