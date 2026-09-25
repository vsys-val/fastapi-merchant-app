"""Configuração local/ambiente, sem segredos embutidos no código."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import PostgresDsn, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    jwt_secret: SecretStr
    access_token_expires_seconds: int = 86400
    cors_allowed_origins: str = ""
    # "disabled" mantém contas ativas desde o cadastro e desliga recuperação de
    # senha; "log" grava os códigos no log e serve apenas para desenvolvimento.
    email_delivery: Literal["disabled", "log"] = "disabled"
    # E-mails com acesso ao painel administrativo, separados por vírgula.
    admin_emails: str = ""
    # Definido automaticamente pelo Render em cada deploy.
    render_git_commit: str | None = None
    # Segredo compartilhado com o workflow de alertas; sem ele, o endpoint não existe.
    alerts_token: SecretStr | None = None

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        # A URL contém credenciais; nunca reproduzir a entrada no erro.
        try:
            parsed = PostgresDsn(value.get_secret_value())
        except ValidationError:
            raise ValueError("Informe uma URL PostgreSQL válida.") from None
        if parsed.scheme != "postgresql+psycopg" or not parsed.path or parsed.path == "/":
            raise ValueError("Use postgresql+psycopg e informe o nome do banco.")
        return value

    @property
    def alembic_database_url(self) -> SecretStr:
        """Conexão direta para migrações, com fallback para a URL da aplicação."""

        return self.migration_database_url or self.database_url

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("Gere uma chave aleatória com pelo menos 32 bytes.")
        return value

    @field_validator("alerts_token")
    @classmethod
    def validate_alerts_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("ALERTS_TOKEN deve ter pelo menos 32 bytes.")
        return value

    @field_validator("access_token_expires_seconds")
    @classmethod
    def validate_access_token_expiration(cls, value: int) -> int:
        if value != 86400:
            raise ValueError("O token do MVP deve expirar em 86400 segundos.")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        normalized: list[str] = []
        for item in value.split(","):
            origin = item.strip().rstrip("/")
            if not origin:
                continue
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "Informe origens HTTP/HTTPS separadas por vírgula, sem caminhos."
                )
            normalized.append(origin)
        return ",".join(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_email_delivery(self) -> "Settings":
        if self.environment == "production" and self.email_delivery == "log":
            raise ValueError("EMAIL_DELIVERY=log não pode ser usado em produção.")
        return self

    @property
    def email_verification_enabled(self) -> bool:
        """Confirmação de conta só é exigida quando há como entregar o código."""

        return self.email_delivery != "disabled"

    @field_validator("admin_emails")
    @classmethod
    def normalize_admin_emails(cls, value: str) -> str:
        emails = [item.strip().casefold() for item in value.split(",") if item.strip()]
        return ",".join(dict.fromkeys(emails))

    @property
    def admin_email_set(self) -> frozenset[str]:
        return frozenset(filter(None, self.admin_emails.split(",")))

    @property
    def cors_origins(self) -> list[str]:
        """Origens exatas autorizadas a chamar a API pelo navegador."""

        if not self.cors_allowed_origins:
            return []
        return self.cors_allowed_origins.split(",")


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        # O único validador de modelo trata EMAIL_DELIVERY e não possui "loc".
        fields = sorted(
            {
                str(error["loc"][0]).upper() if error["loc"] else "EMAIL_DELIVERY"
                for error in exc.errors()
            }
        )
        raise RuntimeError(
            "Configuração ausente ou inválida: " + ", ".join(fields)
            + ". Confira o .env e o README."
        ) from None
