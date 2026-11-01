from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.modules.clinica import models as clinica_models  # noqa: F401
from app.modules.clinica.router import router as clinica_router
from app.modules.clinica.seed import sembrar_parametros as sembrar_parametros_clinica
from app.modules.cobros.router import router as cobros_router
from app.modules.guarderia import models as guarderia_models  # noqa: F401
from app.modules.guarderia.router import router as guarderia_router
from app.modules.guarderia.seed import sembrar_parametros
from app.modules.identidad.router import router as identidad_router
from app.modules.padron.router import router as padron_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as db:
        sembrar_parametros(db)
        sembrar_parametros_clinica(db)
    yield


app = FastAPI(title="Huellitas", version="0.1.0", lifespan=lifespan)
app.include_router(identidad_router)
app.include_router(padron_router)
app.include_router(cobros_router)
app.include_router(guarderia_router)
app.include_router(clinica_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)) -> dict[str, str]:
    return {"status": "ok"}
