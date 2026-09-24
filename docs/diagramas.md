# Diagramas

Versões em Mermaid dos modelos do sistema, renderizadas diretamente pelo GitHub. As fontes PlantUML originais continuam em [`uml-casos-de-uso.puml`](uml-casos-de-uso.puml), [`uml-classes.puml`](uml-classes.puml) e [`diagrama-er.puml`](diagrama-er.puml).

## 1. Contexto do sistema

```mermaid
flowchart LR
  V([Visitante]) -->|consulta| WEB
  U([Usuário autenticado]) -->|consulta, cadastra, avalia| WEB
  subgraph Render
    WEB["merchant-app-web<br/>React + PWA (estático)"]
    API["fastapi-merchant-app<br/>FastAPI · JWT · Argon2id"]
  end
  subgraph Supabase
    DB[("PostgreSQL gerenciado<br/>RLS + papel de mínimo privilégio")]
  end
  WEB -->|HTTPS + CORS explícito| API
  API -->|SQLAlchemy / psycopg| DB
  GH[GitHub Actions] -.->|testes, deploy após checks,<br/>smoke test diário| API
  GH -.->|E2E em produção após deploy| WEB
```

## 2. Casos de uso

```mermaid
flowchart LR
  V([Visitante])
  U([Usuário autenticado])
  subgraph API de avaliações de produtos
    UC01([UC01 Cadastrar conta])
    UC02([UC02 Realizar login])
    UC04([UC04 Pesquisar produto])
    UC05([UC05 Consultar detalhes])
    UC06([UC06 Cadastrar produto])
    UC07([UC07 Editar produto])
    UC11([UC11 Excluir produto])
    UC08([UC08 Cadastrar avaliação])
    UC09([UC09 Editar avaliação])
    UC10([UC10 Excluir avaliação])
    UC12([UC12 Consultar própria conta])
    UC13([UC13 Consultar próprias avaliações])
    UC14([UC14 Consultar próprios produtos])
    UC15([UC15 Confirmar e-mail])
    UC16([UC16 Recuperar senha])
  end
  V --- UC01 & UC02 & UC04 & UC05
  V --- UC15 & UC16
  U --- UC04 & UC05 & UC06 & UC07 & UC11
  U --- UC08 & UC09 & UC10
  U --- UC12 & UC13 & UC14
```

## 3. Modelo de dados

```mermaid
erDiagram
  USUARIOS ||--o{ PRODUTOS : "é responsável por"
  USUARIOS ||--o{ AVALIACOES : escreve
  PRODUTOS ||--o{ AVALIACOES : recebe
  AVALIACOES ||--|{ MOTIVOS_AVALIACAO : contém
  USUARIOS ||--o{ CODIGOS_VERIFICACAO : recebe

  USUARIOS {
    int id PK
    varchar nome_publico
    varchar email UK
    text senha_hash
    timestamptz criado_em
    timestamptz email_verificado_em "null = pendente"
    int versao_sessao "troca de senha incrementa"
  }
  CODIGOS_VERIFICACAO {
    int usuario_id PK, FK "ON DELETE CASCADE"
    varchar finalidade PK "email_verification | password_reset"
    char codigo_hash "HMAC, nunca o código"
    timestamptz expira_em "15 min"
    int tentativas "máx. 5"
    timestamptz enviado_em "reenvio após 60 s"
  }
  PRODUTOS {
    int id PK
    int criador_id FK
    varchar nome
    varchar marca
    varchar variante "opcional"
    numeric quantidade "> 0, decimal exato"
    varchar unidade "g | ml | un"
    varchar categoria "6 valores"
    varchar codigo_barras UK "GTIN opcional"
    text chave_identidade UK
    timestamptz criado_em
    timestamptz atualizado_em
    timestamptz excluido_em "exclusão lógica"
  }
  AVALIACOES {
    int id PK
    int usuario_id FK "UK com produto_id"
    int produto_id FK
    varchar intencao_recompra
    varchar qualidade
    varchar expectativa
    varchar custo_beneficio
    varchar comentario "até 1000"
    timestamptz criado_em
    timestamptz atualizado_em
  }
  MOTIVOS_AVALIACAO {
    int id PK
    int avaliacao_id FK "ON DELETE CASCADE"
    varchar aspecto "UK com avaliacao_id"
    varchar percepcao
  }
  LIMITES_LOGIN {
    varchar escopo PK "account | ip | register | code | email"
    varchar chave_hash PK "HMAC-SHA256"
    int tentativas
    timestamptz janela_iniciada_em
  }
```

`LIMITES_LOGIN` é uma tabela técnica, sem relação com as entidades de negócio: guarda só o HMAC do e-mail ou do IP.

## 4. Ciclo de vida do produto

Este diagrama resume [RN12, RN13](requisitos.md) e os ADRs [0005](decisoes/0005-bloqueio-de-edicao-apos-avaliacao.md) e [0008](decisoes/0008-exclusao-logica-e-reativacao.md) em um único lugar.

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Editável: cadastro (201)
  Editável --> Bloqueado: avaliação de terceiro
  Bloqueado --> Editável: sem avaliações de terceiros
  Editável --> Excluído: DELETE (204)
  Excluído --> Editável: recadastro (200)
```

| Transição | Condição | Efeito |
|---|---|---|
| Editável → Editável | PATCH pelo responsável, ou o próprio responsável avalia | Dados corrigidos; o produto continua editável |
| Editável → Bloqueado | Primeira avaliação de **outro** usuário | PATCH → `409 product_locked_by_reviews` |
| Bloqueado → Editável | Todas as avaliações de terceiros foram excluídas | Edição volta a ser permitida |
| Editável → Excluído | DELETE pelo responsável, sem **nenhuma** avaliação | Some de busca, detalhe e listas; GTIN e chave de identidade continuam reservados |
| Excluído → Editável | Recadastro do mesmo item por qualquer usuário | Mesmo ID, novos dados, novo responsável |

Com qualquer avaliação, inclusive a do responsável, o DELETE retorna `409 product_has_reviews`.

## 5. Sequência — publicar uma avaliação

```mermaid
sequenceDiagram
  autonumber
  actor U as Usuária
  participant W as Web (ReviewForm)
  participant A as API
  participant D as PostgreSQL

  U->>W: Etapa 1 — recompra e 3 critérios
  W->>W: valida que os 4 foram respondidos
  U->>W: Etapa 2 — motivos (+ comentário se "Outro")
  W->>W: valida ≥ 1 motivo e comentário de "Outro"
  U->>W: Etapa 3 — confere e publica
  W->>A: POST /products/{id}/reviews (Bearer)
  A->>A: autentica o JWT e valida o schema (Literal, 1–12 motivos, sem repetição)
  A->>D: SELECT produto ativo FOR KEY SHARE
  alt produto inexistente ou excluído
    A-->>W: 404 product_not_found
  else já existe avaliação do usuário
    A-->>W: 409 review_already_exists {existing_review_id}
  else válido
    A->>D: INSERT avaliação + motivos (uma transação)
    D-->>A: commit (UNIQUE garante 1 por usuário mesmo em corrida)
    A-->>W: 201 avaliação
    W->>A: GET /products/{id} (recarrega)
    A-->>W: your_review + community_summary sem a própria avaliação
    W-->>U: "Sua experiência" atualizada
  end
```

## 6. Ciclo de vida da conta

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Pendente: cadastro (201)
  Pendente --> Confirmada: código de confirmação
  Pendente --> Confirmada: recuperação de senha
  Pendente --> Substituída: novo cadastro após 24 h
  Substituída --> [*]
  Confirmada --> Confirmada: recuperação de senha
```

| Estado | Pode obter token? | Observações |
|---|---|---|
| Pendente | Não: login com senha correta → `403 email_not_verified` | E-mail reservado por 24 h; reenvio de código a cada 60 s |
| Confirmada | Sim | Recuperar a senha incrementa `versao_sessao` e derruba os tokens anteriores |
| Substituída | — | A conta pendente é apagada; como nunca obteve token, não tem dados |

Sem entrega de e-mail configurada (`EMAIL_DELIVERY=disabled`), o cadastro vai direto para **Confirmada**.

## 7. Deploy e verificação contínua

```mermaid
flowchart LR
  PR[Pull request] --> CI{CI verde?}
  CI -- não --> FIX[Corrigir]
  CI -- sim --> MAIN[merge na main]
  MAIN --> RD[Render: build]
  RD --> MIG[alembic upgrade head]
  MIG --> UP[uvicorn + healthcheck /health]
  UP --> SMK[Smoke test diário<br/>somente leitura]
  MAIN --> WEBD[Render: build do web<br/>com SHA do commit]
  WEBD --> WAIT[CI aguarda build-info.json<br/>com o mesmo SHA]
  WAIT --> E2E[Playwright em produção<br/>desktop + Pixel 7]
```
