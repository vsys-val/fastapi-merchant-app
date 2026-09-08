import pytest
from pydantic import ValidationError

from app.schemas import LoginInput, UserCreate


def test_user_create_normalizes_email_and_name_without_changing_password():
    payload = UserCreate(
        email="  VALERIO@Example.COM ",
        name="  Valério   Silva  ",
        password=" senha longa com espaços ",
    )
    assert str(payload.email) == "valerio@example.com"
    assert payload.name == "Valério Silva"
    assert payload.password == " senha longa com espaços "


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "valerio@"},
        {"name": "x"},
        {"password": "curta"},
        {"password": "senha123456789"},
    ],
)
def test_user_create_rejects_invalid_fields(changes):
    values = {
        "email": "valerio@example.com",
        "name": "Valério",
        "password": "uma frase secreta longa",
    }
    values.update(changes)
    with pytest.raises(ValidationError):
        UserCreate(**values)


def test_login_normalizes_email_but_does_not_apply_signup_password_policy():
    payload = LoginInput(email=" USER@EXAMPLE.COM ", password="old")
    assert str(payload.email) == "user@example.com"
    assert payload.password == "old"
