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
    # Görüntülerin yazılacağı dizin (meta veri artık DB'de)
    TARAMALAR_DIZINI.mkdir(parents=True, exist_ok=True)
    # Yarıda kesilmiş taramaları "hata" işaretle (artık DB'ye async yazar)
    await tarama_servisi.baslangicta_kesilmisleri_isaretle()
    yield


app = FastAPI(title="Donatı Tarama Cihazı — Operatör Arayüzü", lifespan=lifespan)
app.include_router(tarama_router)


@app.get("/health", tags=["altyapi"])
async def health() -> dict[str, str]:
    """Canlılık kontrolü (liveness). Deploy sonrası ve health check için:
    süreç ayakta ve istek işleyebiliyorsa 200 döner. Bağımlılık (DB vb.)
    kontrolü içermez — o "readiness" olur ve PostgreSQL gelince eklenir.
    Kök seviyededir çünkü Nginx/Jenkins/Docker health check burayı bekler.
    """
    return {"durum": "saglikli"}


# StaticFiles mount'u EN SONA — kök yolu ("/") kapattığı için tüm API ve
# /health route'ları ondan ÖNCE kayıtlı olmalı, yoksa buraya düşerler.
app.mount("/", StaticFiles(directory=STATIK_DIZIN, html=True), name="static")
