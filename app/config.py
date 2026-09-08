"""Configuração local/ambiente, sem segredos embutidos no código."""

from typing import Literal

from pydantic import PostgresDsn, SecretStr, ValidationError, field_validator
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
    jwt_secret: SecretStr

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        # A URL contém credenciais; nunca reproduzir a entrada no erro.
        try:
            parsed = PostgresDsn(value.get_secret_value())
        except ValidationError:
            raise ValueError("Informe uma URL PostgreSQL válida.") from None
        if parsed.scheme != "postgresql+psycopg" or not parsed.path or parsed.path == "/":
            raise ValueError("Use postgresql+psycopg e informe o nome do banco.")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("Gere uma chave aleatória com pelo menos 32 bytes.")
        return value


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        raise RuntimeError(
            "Configuração ausente ou inválida: " + ", ".join(fields)
            + ". Confira o .env e o README."
        ) from None
