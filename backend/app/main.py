from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identidad.router import router as identidad_router

app = FastAPI(title="Huellitas", version="0.1.0")
app.include_router(identidad_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)) -> dict[str, str]:
    return {"status": "ok"}
