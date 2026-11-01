from pathlib import Path

import pytest

from app.core.config import Settings
from app.modules.clinica import router as clinica_router
from app.modules.identidad.permisos import Rol

PNG_CHICO = b"\x89PNG\r\n\x1a\ncontenido png"


def _crear_estudio(client, clinica_context, headers) -> int:
    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/estudios",
        json={
            "tipo": "RADIOGRAFIA",
            "fecha": "2026-11-01",
            "descripcion": "Placa",
            "realizado_por_empleado_id": clinica_context["veterinario_id"],
        },
        headers=headers,
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _configurar_uploads(monkeypatch, directorio: Path, max_bytes: int) -> None:
    settings = Settings(
        uploads_dir=str(directorio),
        upload_max_bytes=max_bytes,
        upload_allowed_mime_types=["image/jpeg", "image/png", "image/webp", "application/pdf"],
    )
    monkeypatch.setattr(clinica_router, "get_settings", lambda: settings)


def test_archivo_mayor_al_maximo_se_rechaza_y_no_persiste(
    client,
    clinica_context,
    crear_usuario_clinica,
    tmp_path,
    monkeypatch,
) -> None:
    directorio = tmp_path / "uploads"
    _configurar_uploads(monkeypatch, directorio, len(PNG_CHICO))
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    estudio_id = _crear_estudio(client, clinica_context, headers)

    respuesta = client.post(
        f"/api/estudios/{estudio_id}/adjuntos",
        files={"archivo": ("grande.png", PNG_CHICO + b"x", "image/png")},
        headers=headers,
    )

    assert respuesta.status_code == 413
    assert not list(directorio.glob("*"))
    listado = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/estudios",
        headers=headers,
    )
    assert listado.json()[0]["adjuntos"] == []


@pytest.mark.parametrize(
    ("nombre", "contenido"),
    [
        ("texto.png", b"texto plano"),
        ("ejecutable.png", b"MZ\x90\x00ejecutable"),
        ("ejecutable.pdf", b"MZ\x90\x00ejecutable"),
    ],
)
def test_firma_invalida_se_rechaza_aunque_la_extension_sea_permitida(
    client,
    clinica_context,
    crear_usuario_clinica,
    tmp_path,
    monkeypatch,
    nombre: str,
    contenido: bytes,
) -> None:
    directorio = tmp_path / "uploads"
    _configurar_uploads(monkeypatch, directorio, 1024)
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    estudio_id = _crear_estudio(client, clinica_context, headers)

    respuesta = client.post(
        f"/api/estudios/{estudio_id}/adjuntos",
        files={"archivo": (nombre, contenido, "image/png")},
        headers=headers,
    )

    assert respuesta.status_code == 422
    assert not directorio.exists()


def test_nombre_del_cliente_nunca_se_usa_como_ruta(
    client,
    clinica_context,
    crear_usuario_clinica,
    tmp_path,
    monkeypatch,
) -> None:
    directorio = tmp_path / "uploads"
    _configurar_uploads(monkeypatch, directorio, 1024)
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    estudio_id = _crear_estudio(client, clinica_context, headers)

    respuesta = client.post(
        f"/api/estudios/{estudio_id}/adjuntos",
        files={
            "archivo": (
                "../../etc/passwd.png",
                PNG_CHICO,
                "application/octet-stream",
            )
        },
        headers=headers,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre_original"] == "../../etc/passwd.png"
    archivos = list(directorio.iterdir())
    assert len(archivos) == 1
    assert archivos[0].parent == directorio
    assert archivos[0].name != "../../etc/passwd.png"
    assert archivos[0].read_bytes() == PNG_CHICO


def test_fallo_al_guardar_en_base_borra_el_archivo(
    client,
    clinica_context,
    crear_usuario_clinica,
    db_session,
    tmp_path,
    monkeypatch,
) -> None:
    directorio = tmp_path / "uploads"
    _configurar_uploads(monkeypatch, directorio, 1024)
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    estudio_id = _crear_estudio(client, clinica_context, headers)

    def fallar_commit() -> None:
        raise RuntimeError("fallo de base de datos")

    monkeypatch.setattr(db_session, "commit", fallar_commit)
    with pytest.raises(RuntimeError, match="fallo de base de datos"):
        client.post(
            f"/api/estudios/{estudio_id}/adjuntos",
            files={"archivo": ("placa.png", PNG_CHICO, "image/png")},
            headers=headers,
        )

    assert not list(directorio.glob("*"))
    monkeypatch.undo()
    listado = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/estudios",
        headers=headers,
    )
    assert listado.status_code == 200
    assert listado.json()[0]["adjuntos"] == []


def test_estudio_inexistente_no_guarda_archivo(
    client, crear_usuario_clinica, tmp_path, monkeypatch
) -> None:
    directorio = tmp_path / "uploads"
    _configurar_uploads(monkeypatch, directorio, 1024)
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    respuesta = client.post(
        "/api/estudios/99999/adjuntos",
        files={"archivo": ("placa.png", PNG_CHICO, "image/png")},
        headers=headers,
    )

    assert respuesta.status_code == 404
    assert not directorio.exists()
