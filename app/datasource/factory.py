"""Config'e göre doğru DataSource implementasyonunu döndürür.

Veri kaynağını değiştirmek için tek yapılması gereken config.yaml'daki
`veri_kaynagi: mock` satırını `veri_kaynagi: serial` yapmaktır.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import ayarlari_al
from app.datasource.base import DataSource
from app.datasource.mock_source import MockDataSource
from app.datasource.serial_source import SerialDataSource


@lru_cache
def veri_kaynagi_al() -> DataSource:
    ayarlar = ayarlari_al()
    if ayarlar.veri_kaynagi == "serial":
        return SerialDataSource()
    if ayarlar.veri_kaynagi == "mock":
        return MockDataSource()
    raise ValueError(f"Bilinmeyen veri_kaynagi: {ayarlar.veri_kaynagi!r} (mock | serial olmalı)")
