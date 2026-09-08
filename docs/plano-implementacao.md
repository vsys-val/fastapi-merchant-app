# Plano de implementação do MVP

## Situação

Planejamento consolidado. Entregas 1 e 2 implementadas e publicadas na branch `feat/estrutura-inicial`: fábrica FastAPI, configuração protegida, SQLAlchemy, sessões e migrações Alembic. O Supabase de desenvolvimento está em `0003_secure_alembic`; as cinco tabelas do schema público têm RLS, e `anon`/`authenticated` não possuem privilégios sobre `alembic_version`. O teste de escrita da conexão de migração passou com rollback. A base da entrega 3 também foi publicada: normalizadores, validação de GTIN, schemas de criação/PATCH e envelope de erros. A suíte atual possui 36 testes aprovados. Antes de implantação pública, a aplicação ainda deverá receber um papel PostgreSQL próprio com privilégios mínimos. Entregas 4–8 ainda não foram implementadas.

Referências: [requisitos](requisitos.md), [casos de uso](casos-de-uso.md), [contrato](contrato-api.md), [modelo](modelo-banco.md) e [testes](matriz-testes.md). Ideação é histórico; mudanças posteriores estão refletidas nesses documentos.

## Sequência de entregas

| Ordem | Entrega | Dependência | Critério de conclusão |
|---|---|---|---|
| 1 | Estrutura FastAPI, configuração por ambiente e instruções locais | — | Aplicação inicia; segredos ausentes geram falha clara sem vazamento |
| 2 | PostgreSQL, modelos e migração inicial | 1 | Migração sobe em banco vazio; FKs, CHECKs, unicidades e timestamps verificados |
| 3 | Normalizadores, validadores, schemas e envelope de erro | 1 | Testes de limites, decimal, GTIN e PATCH aprovados |
| 4 | Cadastro, hash, login, JWT, limites de tentativa e /users/me | 2–3 | Testes de autenticação, privacidade e limitação aprovados |
| 5 | Criar, editar, excluir e reativar produtos | 2–4 | Unicidade, autorização e corridas entre operações testadas |
| 6 | Criar, editar e excluir avaliações e motivos | 5 | Atomicidade, autoria e unicidade testadas |
| 7 | Pesquisa, detalhe, comunidade e listas pessoais | 5–6 | Paginação, filtros e exclusão da própria avaliação conferidos |
| 8 | /health, documentação OpenAPI, revisão integrada e execução automatizada dos testes | 1–7 | Matriz mínima aprovada em PostgreSQL e README com execução reproduzível |

## Diretrizes técnicas para execução

- Usar uma aplicação monolítica simples. Como base de implementação, SQLAlchemy, Alembic e pytest são escolhas propostas; versões e APIs serão verificadas no início da implementação.
- Usar PostgreSQL também nos testes de integração, com banco isolado e nunca dados de produção.
- Separar schemas públicos das entidades persistidas e manter regras de negócio testáveis, sem criar camadas sem necessidade.
- Aplicar migrações somente em ambiente explicitamente destinado ao desenvolvimento/teste. Implantação pública fica fora desta entrega.
- Rate limiting precisa de contadores atômicos e prazo de expiração. Não presumir que memória de um processo proteja múltiplos workers; documentar o modo de execução e testar seus limites antes de ampliar.
- Senhas e tokens não entram em logs nem nos detalhes retornados por validadores. Usar HTTPS quando houver implantação.
- Unicidade deve ser protegida pelo banco, não apenas por consulta prévia. Verificações de estado e gravação compartilham transação e bloqueio do produto.
- Não adicionar fila, cache de indicadores, microserviços ou interface neste MVP.

## Precisões adotadas na consolidação

Não são funcionalidades novas: o recadastro troca o responsável atual e preserva a data original; datas empatadas usam ID para ordenar; GTIN e identidade que apontam a registros diferentes produzem conflito sem mesclar; senhas não sofrem trim; variante vazia equivale a null. O contrato registra essas convenções.

## Critério de encerramento

Cada entrega inclui implementação e testes pertinentes, sem postergar toda a validação para o fim. O MVP só estará concluído após aprovação da matriz mínima, documentação executável e demonstração do fluxo cadastro → login → produto → avaliação → consulta. Este documento organiza o trabalho; não afirma que esses testes já foram executados.
