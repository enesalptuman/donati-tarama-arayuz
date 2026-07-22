"""Veritabanı tablo modelleri (SQLAlchemy 2.0 ORM).

Tek tablo: taramalar. Yapısal alanlar ayrı sütunlarda (sorgulanabilir),
tam sonuç nesnesi `sonuc_json` metin sütununda (Pydantic ile serileşir).
Görüntü PNG'leri DB'de DEĞİL — dosya sisteminde tutulur (bkz. storage.py).

Not: sonuc_json için PostgreSQL'de JSONB kullanılabilirdi (indeksleme avantajı),
ama sonucun içinde DB düzeyinde sorgu yapmadığımız ve testleri SQLite'ta hızlı
koşmak istediğimiz için taşınabilir Text tipini seçtik.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _simdi() -> datetime:
    return datetime.now(UTC)


class TaramaKaydi(Base):
    __tablename__ = "taramalar"

    # Zaman damgalı kimlik (örn. "2026-07-21T13-56-31")
    tarama_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Başlangıçta bilinen alanlar (operatör girdisi)
    operator: Mapped[str] = mapped_column(String(200))
    konum_etiketi: Mapped[str] = mapped_column(String(300))
    eleman_tipi: Mapped[str] = mapped_column(String(20))
    gerekli_pas_payi_mm: Mapped[float] = mapped_column(Float)

    # Yaşam döngüsü (işlem sırasında güncellenir)
    durum: Mapped[str] = mapped_column(String(20))
    ilerleme: Mapped[int] = mapped_column(Integer, default=0)
    hata_mesaji: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tamamlanınca doldurulur
    tarih: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sonuc_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # TaramaSonucu (JSON)

    # Sıralama/denetim için — her zaman dolu
    olusturma_zamani: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_simdi)
