# ADR-0003 — Motivos obrigatórios no formato aspecto + percepção

- Status: aceita
- Data: 2026-08-17
- Origem: `6ba94d0` (exige motivo em cada avaliação), `6c928c8` (estrutura motivos por aspecto e percepção), `b447d7c` (define aspectos disponíveis)

## Contexto

Critérios semânticos dizem **quanto** a pessoa gostou, mas não **do quê**. Comentários livres dizem o porquê, mas são opcionais, difíceis de agregar e raros em avaliações feitas pelo celular. Também existe o risco de avaliações acidentais ou vazias, feitas com poucos toques.

## Alternativas consideradas

| Alternativa | Problema |
|---|---|
| Comentário obrigatório | Alta fricção; textos vazios como "ok" |
| Tags livres | Não agregam: "cheiro", "aroma" e "fragrância" viram coisas diferentes |
| Lista de motivos só positivos ou só negativos | Duplica a lista e não modela "embalagem ruim, sabor ótimo" |
| **Aspecto controlado + percepção positiva/negativa** | Agregável, universal e rápido de marcar |

## Decisão

- Toda avaliação tem **pelo menos um motivo**. Cada motivo é um par (aspecto, percepção).
- São 12 aspectos universais: sabor, cheiro/fragrância, textura/consistência, eficácia/desempenho, quantidade/rendimento, facilidade de uso/preparo, embalagem, durabilidade/conservação, composição/ingredientes, segurança/tolerância, preço e outro.
- Um aspecto não se repete dentro da mesma avaliação, nem com percepções conflitantes.
- O aspecto **outro** exige comentário explicativo.

## Consequências

- ➕ A exigência de motivo funciona como "trava" contra avaliação acidental.
- ➕ Os dados permitem, no futuro, indicadores como "o que a comunidade mais elogia neste produto".
- ➕ Nem todo aspecto se aplica a todo produto; a pessoa escolhe só os relevantes.
- ➖ A lista é um compromisso entre abrangência e simplicidade. O uso de `other` será o termômetro ([hipótese H3](../visao-produto.md#8-hipóteses-e-riscos)).
- ➖ Os motivos ainda não aparecem agregados nos indicadores. Isso está no [roadmap](../roadmap.md).

## Rastreabilidade

RN21–RN24 · UC08, UC09 · T19, T20, T21 · `app/validation.py::validate_review_reasons`, constraint `uq_motivos_avaliacao_aspecto` · frontend: etapa 2 do `ReviewForm`
