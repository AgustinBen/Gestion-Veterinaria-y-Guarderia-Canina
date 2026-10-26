"""Tests de la matriz de permisos rol × recurso (función pura)."""

import pytest

from app.modules.identidad.permisos import MATRIZ, Nivel, Recurso, Rol, nivel_de, puede

MATRIZ_ESPERADA: dict[tuple[Rol, Recurso], Nivel] = {
    (Rol.DUENIO, Recurso.USUARIOS_CONFIG): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.USUARIOS_CONFIG): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.USUARIOS_CONFIG): Nivel.NINGUNO,
    (Rol.DUENIO, Recurso.FINANZAS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.FINANZAS): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.FINANZAS): Nivel.NINGUNO,
    (Rol.DUENIO, Recurso.DEUDAS_COBROS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.DEUDAS_COBROS): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.DEUDAS_COBROS): Nivel.NINGUNO,
    (Rol.DUENIO, Recurso.PADRON): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.PADRON): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.PADRON): Nivel.LECTURA,
    (Rol.DUENIO, Recurso.RESERVAS_CUPO): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.RESERVAS_CUPO): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.RESERVAS_CUPO): Nivel.LECTURA,
    (Rol.DUENIO, Recurso.EMERGENCIA): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.EMERGENCIA): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.EMERGENCIA): Nivel.NINGUNO,
    (Rol.DUENIO, Recurso.TURNOS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.TURNOS): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.TURNOS): Nivel.ESCRITURA,
    (Rol.DUENIO, Recurso.HISTORIA_CLINICA): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.HISTORIA_CLINICA): Nivel.LECTURA,
    (Rol.VETERINARIO, Recurso.HISTORIA_CLINICA): Nivel.ESCRITURA,
}


def test_matriz_completa() -> None:
    assert MATRIZ == MATRIZ_ESPERADA


def test_matriz_tiene_las_24_combinaciones() -> None:
    combinaciones = {(rol, recurso) for rol in Rol for recurso in Recurso}

    assert set(MATRIZ) == combinaciones
    assert len(MATRIZ) == len(Rol) * len(Recurso)


def test_duenio_tiene_escritura_en_todos_los_recursos() -> None:
    for recurso in Recurso:
        assert nivel_de(Rol.DUENIO, recurso) == Nivel.ESCRITURA
        assert puede(Rol.DUENIO, recurso, Nivel.ESCRITURA)


@pytest.mark.parametrize(
    ("rol", "recurso", "nivel"),
    [
        (Rol.PERSONAL, Recurso.USUARIOS_CONFIG, Nivel.NINGUNO),
        (Rol.PERSONAL, Recurso.FINANZAS, Nivel.NINGUNO),
        (Rol.PERSONAL, Recurso.DEUDAS_COBROS, Nivel.ESCRITURA),
        (Rol.PERSONAL, Recurso.PADRON, Nivel.ESCRITURA),
        (Rol.PERSONAL, Recurso.RESERVAS_CUPO, Nivel.ESCRITURA),
        (Rol.PERSONAL, Recurso.EMERGENCIA, Nivel.NINGUNO),
        (Rol.PERSONAL, Recurso.TURNOS, Nivel.ESCRITURA),
        (Rol.PERSONAL, Recurso.HISTORIA_CLINICA, Nivel.LECTURA),
        (Rol.VETERINARIO, Recurso.USUARIOS_CONFIG, Nivel.NINGUNO),
        (Rol.VETERINARIO, Recurso.FINANZAS, Nivel.NINGUNO),
        (Rol.VETERINARIO, Recurso.DEUDAS_COBROS, Nivel.NINGUNO),
        (Rol.VETERINARIO, Recurso.PADRON, Nivel.LECTURA),
        (Rol.VETERINARIO, Recurso.RESERVAS_CUPO, Nivel.LECTURA),
        (Rol.VETERINARIO, Recurso.EMERGENCIA, Nivel.NINGUNO),
        (Rol.VETERINARIO, Recurso.TURNOS, Nivel.ESCRITURA),
        (Rol.VETERINARIO, Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA),
    ],
)
def test_nivel_por_rol_y_recurso(rol: Rol, recurso: Recurso, nivel: Nivel) -> None:
    assert nivel_de(rol, recurso) == nivel


@pytest.mark.parametrize(
    ("rol", "recurso", "requerido", "esperado"),
    [
        (Rol.VETERINARIO, Recurso.PADRON, Nivel.LECTURA, True),
        (Rol.VETERINARIO, Recurso.PADRON, Nivel.ESCRITURA, False),
        (Rol.PERSONAL, Recurso.HISTORIA_CLINICA, Nivel.LECTURA, True),
        (Rol.PERSONAL, Recurso.HISTORIA_CLINICA, Nivel.ESCRITURA, False),
        (Rol.PERSONAL, Recurso.EMERGENCIA, Nivel.LECTURA, False),
        (Rol.VETERINARIO, Recurso.DEUDAS_COBROS, Nivel.LECTURA, False),
        (Rol.PERSONAL, Recurso.TURNOS, Nivel.ESCRITURA, True),
    ],
)
def test_jerarquia_de_niveles(
    rol: Rol, recurso: Recurso, requerido: Nivel, esperado: bool
) -> None:
    assert puede(rol, recurso, requerido) is esperado


def test_puede_usa_lectura_por_defecto() -> None:
    assert puede(Rol.VETERINARIO, Recurso.PADRON) is True
    assert puede(Rol.VETERINARIO, Recurso.EMERGENCIA) is False


def test_ninguno_no_alcanza_ningun_nivel() -> None:
    assert nivel_de(Rol.PERSONAL, Recurso.EMERGENCIA) == Nivel.NINGUNO
    assert puede(Rol.PERSONAL, Recurso.EMERGENCIA, Nivel.NINGUNO) is True
    assert puede(Rol.PERSONAL, Recurso.EMERGENCIA, Nivel.LECTURA) is False
