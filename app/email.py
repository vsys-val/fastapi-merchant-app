"""Entrega de e-mails transacionais com códigos de verificação.

A aplicação depende apenas do protocolo ``EmailSender``. Um provedor HTTP
real entra como nova implementação, sem alterar os casos de uso.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

from app.config import Settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class LogEmailSender:
    """Somente desenvolvimento: registra a mensagem em vez de enviá-la."""

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "E-mail de desenvolvimento para %s | %s\n%s",
            message.to,
            message.subject,
            message.body,
        )


def build_email_sender(settings: Settings) -> EmailSender | None:
    if settings.email_delivery == "log":
        return LogEmailSender()
    return None


def deliver(sender: EmailSender, message: EmailMessage) -> None:
    """Executado em segundo plano; falhas não revelam nada ao cliente."""

    try:
        sender.send(message)
    except Exception:
        logger.exception("Falha ao entregar e-mail transacional.")


def verification_email(to: str, name: str, code: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        subject=f"{code} é o seu código de confirmação do Merchant",
        body=(
            f"Olá, {name}.\n\n"
            f"Use o código {code} para confirmar sua conta no Merchant.\n"
            "Ele expira em 15 minutos.\n\n"
            "Se você não criou esta conta, ignore este e-mail."
        ),
    )


def password_reset_email(to: str, name: str, code: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        subject=f"{code} é o seu código para redefinir a senha do Merchant",
        body=(
            f"Olá, {name}.\n\n"
            f"Use o código {code} para criar uma nova senha no Merchant.\n"
            "Ele expira em 15 minutos. Depois da troca, as sessões abertas são encerradas.\n\n"
            "Se você não pediu a troca, ignore este e-mail: sua senha atual continua valendo."
        ),
    )
