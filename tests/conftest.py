"""Paylaşılan pytest fixture'ları.

conftest.py pytest'in otomatik keşfettiği özel bir dosyadır; buradaki
fixture'lar hiçbir import gerektirmeden tüm test dosyalarında kullanılabilir.

Test veritabanı: her test için geçici bir SQLite dosyası (üretim PostgreSQL).
Tablolar senkron motorla kurulur (event loop derdi yok); uygulama aynı dosyaya
async (aiosqlite) erişir. ORM taşınabilir tiplerle yazıldığı için ikisi de aynı
şemayı kullanır.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def izole_ortam(tmp_path, monkeypatch):
    """HER testi izole eder (autouse=True → otomatik çalışır)."""
    # 1) Görüntüler için geçici dizin
    monkeypatch.setattr("app.storage.TARAMALAR_DIZINI", tmp_path)

    # 2) Geçici SQLite dosyası; tabloları SENKRON motorla oluştur
    db_dosyasi = tmp_path / "test.db"
    import app.db_models  # noqa: F401  (tabloyu Base.metadata'ya kaydetmek için import şart)
    from app.db import Base

    sync_engine = create_engine(f"sqlite:///{db_dosyasi.as_posix()}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    # 3) Uygulamanın async motorunu aynı dosyaya yönlendir
    monkeypatch.setenv("DONATI_DB_URL", f"sqlite+aiosqlite:///{db_dosyasi.as_posix()}")
    from app import db
    from app.config import ayarlari_al
    from app.datasource.factory import veri_kaynagi_al

    ayarlari_al.cache_clear()
    veri_kaynagi_al.cache_clear()
    db.motor_kur()  # yeni (SQLite) URL ile async motoru kur

    # 4) Global servis durumunu sıfırla (test izolasyonu)
    from app.services.tarama_service import tarama_servisi

    tarama_servisi._gorevler.clear()
    tarama_servisi._ilerleme.clear()

    yield

    for gorev in list(tarama_servisi._gorevler.values()):
        gorev.cancel()
    tarama_servisi._gorevler.clear()
    ayarlari_al.cache_clear()
    veri_kaynagi_al.cache_clear()


@pytest.fixture
def client():
    """FastAPI TestClient — gerçek sunucu başlatmadan HTTP isteği atar."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def hizli_mock(monkeypatch):
    """Mock tarama süresini ~0'a çeker; testler gerçek saniyelerce beklemesin."""
    monkeypatch.setenv("DONATI_MOCK_SURE_MIN_SN", "0.01")
    monkeypatch.setenv("DONATI_MOCK_SURE_MAKS_SN", "0.02")
    from app.config import ayarlari_al

    ayarlari_al.cache_clear()
    yield


@pytest.fixture
def ornek_tarama_kaydi(tmp_path):
    """Test DB'sine TAMAMLANMIŞ bir tarama satırı + görüntü yazar, id'sini döner.

    Arka plan görevi çalıştırmadan (deterministik) okuma/servis uçlarını test
    etmek için. DB satırını SENKRON motorla ekler (fixture sync olduğu için).
    """
    from app import storage
    from app.db_models import TaramaKaydi
    from app.generators.image_generator import yansima_haritasi_uret
    from app.generators.mock_generator import sahte_sonuc_uret

    random.seed(1234)  # deterministik sahte veri
    tid = "test-tarama-1"
    sonuc = sahte_sonuc_uret(tid, "Test Operator", "B Blok K1").model_copy(update={"tarama_id": tid})

    # Görüntü → dosya
    storage.goruntuyu_kaydet(tid, yansima_haritasi_uret(sonuc))

    # Meta veri → DB (senkron)
    db_dosyasi = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_dosyasi.as_posix()}")
    with Session(engine) as s:
        s.add(
            TaramaKaydi(
                tarama_id=tid,
                operator="Test Operator",
                konum_etiketi="B Blok K1",
                eleman_tipi="kolon",
                gerekli_pas_payi_mm=25.0,
                durum="tamamlandi",
                ilerleme=100,
                tarih=sonuc.tarih,
                sonuc_json=sonuc.model_dump_json(),
                olusturma_zamani=datetime.now(UTC),
            )
        )
        s.commit()
    engine.dispose()
    return tid
