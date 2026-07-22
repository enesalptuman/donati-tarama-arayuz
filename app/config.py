"""Uygulama ayarları — öncelik: ortam değişkeni > config.yaml > varsayılan.

Container/CI-CD dünyasında yapılandırma ortam değişkenleriyle yapılır
(12-factor app, ilke III). Bu yüzden ayarlar üç katmandan okunur:

  1. Ortam değişkeni   (DONATI_ önekli)  — en yüksek öncelik
  2. config.yaml       (varsa)           — orta öncelik
  3. Alan varsayılanı  (aşağıdaki sınıf)  — en düşük öncelik

Gizli bilgiler (DB şifresi, SSH anahtarı vb.) asla config.yaml'a veya koda
yazılmaz; yalnızca ortam değişkeninden okunur. Bu katman onu mümkün kılar.

Not: Üretimde `pydantic-settings` (BaseSettings) kütüphanesi bu işi hazır
yapar; burada bağımlılık eklememek ve her satırı şeffaf tutmak için katmanı
elle yazdık. Mülakat notu: "manuel env-override yazdım, prod'da
pydantic-settings kullanırdım" iyi bir cümledir.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

PROJE_KOKU = Path(__file__).resolve().parent.parent
CONFIG_DOSYASI = PROJE_KOKU / "config.yaml"
TARAMALAR_DIZINI = PROJE_KOKU / "taramalar"

# Ortam değişkeni öneki: DONATI_VERI_KAYNAGI, DONATI_MOCK_SURE_MIN_SN, ...
ENV_ONEK = "DONATI_"


class Ayarlar(BaseModel):
    veri_kaynagi: str = "mock"
    sinirda_pay_mm: float = 10.0
    maks_tarama_sayisi: int = 0  # 0 = sınırsız (otomatik silme yok)
    uyari_tarama_sayisi: int = 50  # 0 = uyarı kapalı
    # Mock tarama süresi — artık kodda sabit değil, buradan/env'den gelir.
    # Üretim varsayılanı 60-120 sn (gerçek algoritma da bu kadar sürecek);
    # geliştirme/test için env ile küçültülür (örn. DONATI_MOCK_SURE_MIN_SN=3).
    mock_sure_min_sn: float = 60.0
    mock_sure_maks_sn: float = 120.0
    # Veritabanı bağlantısı. Şifre içerir → gerçek değer .env/ortam değişkeninden
    # gelir (DONATI_DB_URL). Varsayılan yerel geliştirme içindir.
    # Async sürücüler: postgresql+asyncpg://...  (üretim)  |  sqlite+aiosqlite://... (test)
    db_url: str = "postgresql+asyncpg://donati:donati@localhost:5432/donati"
    seri_port: str = "/dev/ttyACM0"
    seri_baud: int = 921600


def _yaml_oku() -> dict:
    """config.yaml'ı okur; dosya yoksa boş sözlük döner (varsayılanlar geçerli olur)."""
    if not CONFIG_DOSYASI.exists():
        return {}
    with CONFIG_DOSYASI.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _env_ile_ustune_yaz(veri: dict) -> dict:
    """DONATI_ önekli ortam değişkenlerini yaml verisinin üstüne yazar.

    Ayarlar sınıfındaki her alan için ilgili env değişkenine bakar; tanımlıysa
    yaml'dan gelen (veya eksik olan) değeri ezer. Değerler string gelir; tip
    dönüşümünü (str -> float/int) en sonda Pydantic yapar.
    """
    for alan_adi in Ayarlar.model_fields:
        env_anahtari = ENV_ONEK + alan_adi.upper()
        if env_anahtari in os.environ:
            veri[alan_adi] = os.environ[env_anahtari]
    return veri


@lru_cache
def ayarlari_al() -> Ayarlar:
    veri = _yaml_oku()  # katman 2
    veri = _env_ile_ustune_yaz(veri)  # katman 1 (yaml'ı ezer)
    return Ayarlar(**veri)  # katman 3: kalan alanlar varsayılana düşer + tip doğrulama
