"""Verificação agendada de alertas da API publicada.

Roda no GitHub Actions a cada hora. Consulta GET /api/v1/internal/alerts
com o segredo ALERTS_TOKEN e mantém uma única issue com o rótulo
``alerta-producao``: abre quando algum guarda-corpo é violado (ou a API
não responde), atualiza enquanto continua e fecha quando normaliza. Só
usa a biblioteca padrão, como o smoke test.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get("API_URL", "https://fastapi-merchant-app.onrender.com")
LABEL = "alerta-producao"
TITLE = "🚨 Alerta de produção"


def fetch_alerts(token: str, attempts: int = 4, wait_seconds: int = 20) -> dict[str, Any]:
    """Consulta os alertas, esperando o Render acordar o serviço se preciso."""

    last_error = "sem resposta"
    for attempt in range(attempts):
        request = Request(f"{API_URL}/api/v1/internal/alerts", headers={"X-Alerts-Token": token})
        try:
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            if exc.code in (401, 404):
                raise SystemExit(
                    f"::error::A API recusou o token de alertas (HTTP {exc.code}). "
                    "Confira se ALERTS_TOKEN é igual no Render e nos secrets do GitHub."
                )
            last_error = f"HTTP {exc.code}"
        except (URLError, TimeoutError) as exc:
            last_error = str(getattr(exc, "reason", exc))
        if attempt < attempts - 1:
            time.sleep(wait_seconds)
    return {
        "status": "alert",
        "checks": [
            {"key": "api", "label": "API", "ok": False, "value": None, "threshold": "respondendo",
             "detail": f"A API não respondeu após {attempts} tentativas ({last_error})."},
        ],
    }


def render_body(result: dict[str, Any]) -> str:
    lines = [
        "Verificação automática da API em produção (última hora).",
        "",
        "| Verificação | Estado | Limite | Detalhe |",
        "|---|---|---|---|",
    ]
    for check in result["checks"]:
        state = "✅ ok" if check["ok"] else "❌ violado"
        lines.append(f"| {check['label']} | {state} | {check['threshold']} | {check['detail']} |")
    lines += [
        "",
        f"Avaliado em {result.get('evaluated_at', 'agora')}. Detalhes no painel `/admin` e nos logs do Render.",
        "Esta issue é atualizada a cada hora e fechada automaticamente quando tudo normalizar.",
    ]
    return "\n".join(lines)


def decide(result: dict[str, Any], open_issue: dict[str, Any] | None) -> str:
    """Ação sobre a issue: create, update, close ou none."""

    alerting = result["status"] != "ok"
    if alerting:
        return "update" if open_issue else "create"
    return "close" if open_issue else "none"


class GitHub:
    def __init__(self, repository: str, token: str) -> None:
        self.base = f"https://api.github.com/repos/{repository}"
        self.token = token

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode()
        request = Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def open_alert_issue(self) -> dict[str, Any] | None:
        issues = self.call("GET", f"/issues?state=open&labels={LABEL}&per_page=1")
        return issues[0] if issues else None


def main() -> int:
    token = os.environ.get("ALERTS_TOKEN", "")
    if not token:
        print("::warning::ALERTS_TOKEN não está configurado nos secrets do repositório; alertas desligados.")
        return 0
    result = fetch_alerts(token)
    body = render_body(result)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(body + "\n")
    print(body)

    repository = os.environ.get("GITHUB_REPOSITORY")
    github_token = os.environ.get("GITHUB_TOKEN")
    if not repository or not github_token:
        return 0 if result["status"] == "ok" else 1

    github = GitHub(repository, github_token)
    issue = github.open_alert_issue()
    action = decide(result, issue)
    if action == "create":
        github.call("POST", "/issues", {"title": TITLE, "body": body, "labels": [LABEL]})
    elif action == "update":
        github.call("PATCH", f"/issues/{issue['number']}", {"body": body})
    elif action == "close":
        github.call("POST", f"/issues/{issue['number']}/comments", {"body": "✅ Tudo normalizado.\n\n" + body})
        github.call("PATCH", f"/issues/{issue['number']}", {"state": "closed", "state_reason": "completed"})
    print(f"Ação na issue de alerta: {action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
