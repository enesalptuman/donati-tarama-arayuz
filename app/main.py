"""FastAPI uygulaması — API uçları + statik operatör arayüzü."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import PROJE_KOKU, TARAMALAR_DIZINI
from app.routers.tarama import router as tarama_router
from app.services.tarama_service import tarama_servisi

STATIK_DIZIN = PROJE_KOKU / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    TARAMALAR_DIZINI.mkdir(parents=True, exist_ok=True)
    tarama_servisi.baslangicta_kesilmisleri_isaretle()
    yield


app = FastAPI(title="Donatı Tarama Cihazı — Operatör Arayüzü", lifespan=lifespan)
app.include_router(tarama_router)
app.mount("/", StaticFiles(directory=STATIK_DIZIN, html=True), name="static")
