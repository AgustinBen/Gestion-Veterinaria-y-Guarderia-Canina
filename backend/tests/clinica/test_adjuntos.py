import hashlib
from pathlib import Path

from app.core.config import Settings
from app.modules.clinica import router as clinica_router
from app.modules.identidad.permisos import Rol

PNG_CHICO = b"\x89PNG\r\n\x1a\ncontenido png"


def test_subir_png_y_descargarlo_con_metadatos_y_permisos(
    client, clinica_context, crear_usuario_clinica, tmp_path, monkeypatch
) -> None:
    directorio = tmp_path / "uploads"
    settings = Settings(
        uploads_dir=str(directorio),
        upload_max_bytes=1024,
        upload_allowed_mime_types=["image/jpeg", "image/png", "image/webp", "application/pdf"],
    )
    monkeypatch.setattr(clinica_router, "get_settings", lambda: settings)
    _, headers_duenio = crear_usuario_clinica(Rol.DUENIO)
    _, headers_personal = crear_usuario_clinica(Rol.PERSONAL)
    paciente_id = clinica_context["paciente_id"]

    estudio = client.post(
        f"/api/pacientes/{paciente_id}/estudios",
        json={
            "tipo": "RADIOGRAFIA",
            "fecha": "2026-11-01",
            "descripcion": "Radiografía",
            "realizado_por_empleado_id": clinica_context["veterinario_id"],
        },
        headers=headers_duenio,
    )
    assert estudio.status_code == 201

    subida = client.post(
        f"/api/estudios/{estudio.json()['id']}/adjuntos",
        files={"archivo": ("placa.png", PNG_CHICO, "image/png")},
        headers=headers_duenio,
    )

    assert subida.status_code == 201
    adjunto = subida.json()
    assert adjunto["tipo_mime"] == "image/png"
    assert adjunto["tamano_bytes"] == len(PNG_CHICO)
    assert adjunto["sha256"] == hashlib.sha256(PNG_CHICO).hexdigest()
    archivos = list(directorio.iterdir())
    assert len(archivos) == 1
    assert archivos[0].name == Path(archivos[0].name).name
    assert archivos[0].name != "placa.png"
    assert archivos[0].read_bytes() == PNG_CHICO

    listado = client.get(
        f"/api/pacientes/{paciente_id}/estudios",
        headers=headers_personal,
    )
    assert listado.status_code == 200
    assert listado.json()[0]["adjuntos"][0]["id"] == adjunto["id"]
    assert "contenido" not in listado.json()[0]["adjuntos"][0]

    descarga = client.get(
        f"/api/adjuntos/{adjunto['id']}/archivo",
        headers=headers_personal,
    )
    assert descarga.status_code == 200
    assert descarga.content == PNG_CHICO
    assert descarga.headers["content-type"] == "image/png"
    assert descarga.headers["x-content-type-options"] == "nosniff"
    assert "filename*=UTF-8''placa.png" in descarga.headers["content-disposition"]
    assert client.get(f"/api/adjuntos/{adjunto['id']}/archivo").status_code == 401
    ruta_subida = f"/api/estudios/{estudio.json()['id']}/adjuntos"
    assert (
        client.post(
            ruta_subida,
            files={"archivo": ("placa.png", PNG_CHICO, "image/png")},
            headers=headers_personal,
        ).status_code
        == 403
    )
    assert (
        client.post(
            ruta_subida,
            files={"archivo": ("placa.png", PNG_CHICO, "image/png")},
        ).status_code
        == 401
    )


def test_pdf_real_es_aceptado_y_adjunto_inexistente_responde_404(
    client, clinica_context, crear_usuario_clinica, tmp_path, monkeypatch
) -> None:
    directorio = tmp_path / "uploads"
    settings = Settings(
        uploads_dir=str(directorio),
        upload_max_bytes=1024,
        upload_allowed_mime_types=["image/jpeg", "image/png", "image/webp", "application/pdf"],
    )
    monkeypatch.setattr(clinica_router, "get_settings", lambda: settings)
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO, empleado_id=clinica_context["veterinario_id"]
    )
    estudio = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/estudios",
        json={
            "tipo": "ANALISIS",
            "fecha": "2026-11-01",
            "descripcion": "Informe",
            "realizado_por_empleado_id": clinica_context["veterinario_id"],
        },
        headers=headers,
    )
    objetos = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n",
    ]
    pdf_real = b"%PDF-1.4\n"
    offsets = [0]
    for objeto in objetos:
        offsets.append(len(pdf_real))
        pdf_real += objeto
    inicio_xref = len(pdf_real)
    pdf_real += b"xref\n0 3\n0000000000 65535 f \n"
    pdf_real += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    pdf_real += (f"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n").encode()

    subida = client.post(
        f"/api/estudios/{estudio.json()['id']}/adjuntos",
        files={"archivo": ("informe.pdf", pdf_real, "application/pdf")},
        headers=headers,
    )

    assert subida.status_code == 201
    assert subida.json()["tipo_mime"] == "application/pdf"
    assert client.get("/api/adjuntos/99999/archivo", headers=headers).status_code == 404


def test_no_hay_endpoints_para_borrar_estudios_ni_adjuntos(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    assert (
        client.delete(
            "/api/estudios/1",
            headers=headers,
        ).status_code
        == 404
    )
    assert client.delete("/api/adjuntos/1", headers=headers).status_code == 404
