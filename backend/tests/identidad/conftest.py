"""Fixtures compartidos de los tests del módulo identidad."""

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _secret_key_de_pruebas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita el warning de PyJWT por la clave default corta del proyecto."""
    monkeypatch.setattr(
        get_settings(),
        "secret_key",
        "clave-de-pruebas-de-identidad-con-mas-de-32-bytes",
    )
