"""config.yaml okuyucu.

Veri kaynağı seçimi (mock/serial) ve "sınırda" görsel uyarı payı gibi
ayarlar buradan tek yerden okunur. Gerekli minimum pas payı artık burada
DEĞİL — her taramada operatör/denetçi tarafından girilir (bkz. analiz.py).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

PROJE_KOKU = Path(__file__).resolve().parent.parent
CONFIG_DOSYASI = PROJE_KOKU / "config.yaml"
TARAMALAR_DIZINI = PROJE_KOKU / "taramalar"


class Ayarlar(BaseModel):
    veri_kaynagi: str = "mock"
    sinirda_pay_mm: float = 10.0
    maks_tarama_sayisi: int = 0  # 0 = sınırsız (otomatik silme yok)
    uyari_tarama_sayisi: int = 50  # 0 = uyarı kapalı
    seri_port: str = "/dev/ttyACM0"
    seri_baud: int = 921600


@lru_cache
def ayarlari_al() -> Ayarlar:
    if not CONFIG_DOSYASI.exists():
        return Ayarlar()
    with CONFIG_DOSYASI.open("r", encoding="utf-8") as f:
        veri = yaml.safe_load(f) or {}
    return Ayarlar(**veri)
