"""Veri kaynağı soyutlaması.

Arayüz ve API katmanı, taramanın gerçek algoritmadan mı yoksa mock
üreteçten mi geldiğini bilmez — sadece bu arayüzle (DataSource) konuşur.
Hangi implementasyonun kullanılacağı config.yaml'daki `veri_kaynagi`
alanıyla seçilir (bkz. factory.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.models.tarama import TaramaSonucu

# İlerleme geri çağrısı: 0-100 arası yüzde alır.
IlerlemeCallback = Callable[[int], Awaitable[None]]


@dataclass
class TaramaCiktisi:
    """Bir taramanın tamamlanmasıyla üretilen çıktı."""

    sonuc: TaramaSonucu
    goruntu_png: bytes


class TaramaIptalEdildi(Exception):
    """Tarama, tamamlanmadan önce iptal edildiğinde fırlatılır."""


class DataSource(ABC):
    """Tarama verisi sağlayan kaynakların ortak arayüzü."""

    @abstractmethod
    async def tara(
        self,
        tarama_id: str,
        operator: str,
        konum_etiketi: str,
        ilerleme_cb: IlerlemeCallback,
    ) -> TaramaCiktisi:
        """Taramayı yürütür, ilerleme_cb ile periyodik yüzde bildirir, sonucu döner.

        İptal edilirse TaramaIptalEdildi fırlatılmalı ya da asyncio.CancelledError
        yukarı yayılmalıdır.
        """

    @abstractmethod
    async def iptal_et(self, tarama_id: str) -> None:
        """Devam etmekte olan bir taramayı iptal etmeye çalışır (destekleniyorsa)."""
