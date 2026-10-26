"""Matriz de permisos rol × recurso del módulo identidad.

Una única estructura de datos define el acceso. Cualquier combinación que no
figure en la matriz se considera denegada (default deny).
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Rol(StrEnum):
    DUENIO = "DUENIO"
    PERSONAL = "PERSONAL"
    VETERINARIO = "VETERINARIO"


class Recurso(StrEnum):
    USUARIOS_CONFIG = "usuarios_config"
    FINANZAS = "finanzas"
    DEUDAS_COBROS = "deudas_cobros"
    PADRON = "padron"
    RESERVAS_CUPO = "reservas_cupo"
    EMERGENCIA = "emergencia"
    TURNOS = "turnos"
    HISTORIA_CLINICA = "historia_clinica"


class Nivel(IntEnum):
    NINGUNO = 0
    LECTURA = 1
    ESCRITURA = 2


# No mutar: es la fuente de verdad de permisos del sistema.
MATRIZ: dict[tuple[Rol, Recurso], Nivel] = {
    # Usuarios y configuración: solo el Dueño.
    (Rol.DUENIO, Recurso.USUARIOS_CONFIG): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.USUARIOS_CONFIG): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.USUARIOS_CONFIG): Nivel.NINGUNO,
    # Finanzas: solo el Dueño.
    (Rol.DUENIO, Recurso.FINANZAS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.FINANZAS): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.FINANZAS): Nivel.NINGUNO,
    # Deudas y cobros: Dueño y Personal.
    (Rol.DUENIO, Recurso.DEUDAS_COBROS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.DEUDAS_COBROS): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.DEUDAS_COBROS): Nivel.NINGUNO,
    # Padrón: Dueño y Personal escritura; Veterinario lectura.
    (Rol.DUENIO, Recurso.PADRON): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.PADRON): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.PADRON): Nivel.LECTURA,
    # Reservas y cupo: Dueño y Personal escritura; Veterinario lectura.
    (Rol.DUENIO, Recurso.RESERVAS_CUPO): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.RESERVAS_CUPO): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.RESERVAS_CUPO): Nivel.LECTURA,
    # Plaza de emergencia: solo el Dueño.
    (Rol.DUENIO, Recurso.EMERGENCIA): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.EMERGENCIA): Nivel.NINGUNO,
    (Rol.VETERINARIO, Recurso.EMERGENCIA): Nivel.NINGUNO,
    # Turnos: los tres roles.
    (Rol.DUENIO, Recurso.TURNOS): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.TURNOS): Nivel.ESCRITURA,
    (Rol.VETERINARIO, Recurso.TURNOS): Nivel.ESCRITURA,
    # Historia clínica: Dueño y Veterinario escritura; Personal lectura.
    (Rol.DUENIO, Recurso.HISTORIA_CLINICA): Nivel.ESCRITURA,
    (Rol.PERSONAL, Recurso.HISTORIA_CLINICA): Nivel.LECTURA,
    (Rol.VETERINARIO, Recurso.HISTORIA_CLINICA): Nivel.ESCRITURA,
}


def nivel_de(rol: Rol, recurso: Recurso) -> Nivel:
    """Nivel de acceso de un rol a un recurso. Default: denegar."""
    return MATRIZ.get((rol, recurso), Nivel.NINGUNO)


def puede(rol: Rol, recurso: Recurso, requerido: Nivel = Nivel.LECTURA) -> bool:
    """Indica si el rol alcanza el nivel requerido para el recurso."""
    return nivel_de(rol, recurso) >= requerido
