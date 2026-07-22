"""SQLAlchemy 2.0 async motor + oturum (session) yönetimi.

Motor (engine) uygulama boyunca tek örnektir; oturumlar kısa ömürlüdür
(her işlem için `async with db.oturum_ac() as s:`). Motor yeniden
kurulabilir olduğu için testler farklı bir veritabanına (SQLite)
yönlendirebilir — bkz. tests/conftest.py.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import ayarlari_al


class Base(DeclarativeBase):
    """Tüm ORM tablolarının ortak taban sınıfı. Alembic şemayı buradan okur."""


_motor: AsyncEngine | None = None
_Oturum: async_sessionmaker[AsyncSession] | None = None


def motor_kur(db_url: str | None = None) -> None:
    """Async motoru ve oturum fabrikasını (yeniden) kurar.

    db_url verilmezse config'ten (DONATI_DB_URL) okunur. Testler bu fonksiyonu
    SQLite adresiyle çağırarak üretim veritabanına dokunmadan çalışır.
    """
    global _motor, _Oturum
    url = db_url or ayarlari_al().db_url
    # pool_pre_ping: havuzdan alınan bağlantı ölmüşse (DB yeniden başladı vb.)
    # sessizce yenisiyle değiştirir — üretimde bağlantı kopmalarına dayanıklılık.
    _motor = create_async_engine(url, pool_pre_ping=True)
    # expire_on_commit=False: commit sonrası nesne alanları geçersizleşmesin
    # (async'te commit sonrası tembel yükleme sorun çıkarır).
    _Oturum = async_sessionmaker(_motor, expire_on_commit=False)


def motoru_al() -> AsyncEngine:
    if _motor is None:
        motor_kur()
    assert _motor is not None
    return _motor


def oturum_ac() -> AsyncSession:
    """Bir async DB oturumu döner. Kullanım: `async with db.oturum_ac() as s: ...`"""
    if _Oturum is None:
        motor_kur()
    assert _Oturum is not None
    return _Oturum()
