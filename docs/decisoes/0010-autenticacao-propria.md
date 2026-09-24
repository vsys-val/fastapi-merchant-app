# ADR-0010 — Autenticação própria na API, sem Supabase Auth

- Status: aceita
- Data: 2026-09-08
- Origem: implementação do MVP (PR #2) e seção "Usar Supabase" do README

## Contexto

O banco de dados é hospedado no Supabase, que oferece autenticação pronta (Supabase Auth) e acesso direto do navegador ao banco (Data API com RLS). Usar esses recursos levaria parte das regras de negócio para políticas do banco e acoplaria o produto ao fornecedor.

## Alternativas consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| Supabase Auth + Data API | Menos código; recuperação de senha pronta | Regras espalhadas entre API e políticas RLS; acoplamento ao fornecedor |
| Provedor OAuth (Google etc.) | Sem senha para gerenciar | Dependência externa; excede o escopo do MVP |
| **Autenticação própria (Argon2id + JWT)** | Todas as regras em um lugar; portável para qualquer PostgreSQL | Mais código e responsabilidade de segurança |

## Decisão

- A API emite e valida seu próprio JWT (HS256, 24h). As senhas usam **Argon2id**, com política de 15 a 128 caracteres e bloqueio de senhas comuns.
- O **rate limiting** de login é atômico e persistido no PostgreSQL (5 falhas por conta a cada 15 min; 20 tentativas por IP por minuto), para funcionar com múltiplos workers.
- O Supabase é usado **apenas como PostgreSQL gerenciado**. O RLS fica ativo sem políticas públicas, e a aplicação usa um papel de mínimo privilégio (`merchant_app_runtime`).

## Consequências

- ➕ Regras de autorização concentradas e testadas em um só lugar (T04–T07).
- ➕ Trocar de provedor de banco não afeta a autenticação.
- ➖ Recuperação de senha, refresh e revogação de token precisam ser construídos ([roadmap](../roadmap.md)).
- ➖ O frontend guarda o token em `localStorage` por simplicidade. A evolução prevista é cookie HttpOnly.

## Rastreabilidade

RF02 · RNF01, RNF02 · UC02 · T03–T06 · `app/security.py`, `app/auth.py`, `app/rate_limit.py`, migrações `0004`, `0005`
