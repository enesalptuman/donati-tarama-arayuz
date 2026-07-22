"""Uçtan uca tarama akışı testleri (async, servis katmanı üzerinden).

pyproject.toml'daki `asyncio_mode = "auto"` sayesinde `async def test_...`
fonksiyonları otomatik async çalışır (ayrı marker gerekmez).

Not: Determinizm için arka plan görevine `_gorevler` üzerinden erişip
doğrudan `await` ediyoruz — bu, testin görev bitene kadar beklemesini garanti
eder (uykuya/polling'e göre daha güvenilir) ve öksüz görev bırakmaz.
"""

from __future__ import annotations

import asyncio

import pytest

from app.models.tarama import ElemanTipi, TaramaDurum
from app.services.tarama_service import TaramaDurumHatasi, tarama_servisi


async def test_tam_akis_tamamlanir(hizli_mock):
    # Başlat → arka plan görevini bekle → tamamlandı ve okunabilir olmalı
    yanit = await tarama_servisi.baslat("Operator", "B Blok K1", ElemanTipi.KOLON, 25.0)

    gorev = tarama_servisi._gorevler[yanit.tarama_id]
    await gorev  # arka plan taramasının bitmesini bekle (deterministik)

    durum = await tarama_servisi.durum_al(yanit.tarama_id)
    assert durum.durum == TaramaDurum.TAMAMLANDI
    assert durum.ilerleme == 100

    sonuc = await tarama_servisi.sonuc_al(yanit.tarama_id)
    assert sonuc.tarama_id == yanit.tarama_id
    assert sonuc.kritik_uyari is not None
    assert sonuc.parametreler.gerekli_pas_payi_mm == 25.0


async def test_tek_tarama_kilidi(hizli_mock):
    # İlk tarama devam ederken ikinciyi başlatmak 409 (TaramaDurumHatasi) vermeli
    yanit = await tarama_servisi.baslat("Operator", "K1", ElemanTipi.KOLON, 25.0)

    with pytest.raises(TaramaDurumHatasi):
        await tarama_servisi.baslat("Operator", "K2", ElemanTipi.KOLON, 25.0)

    # Temizlik: ilk görevi tamamlanana kadar bekle (öksüz görev bırakma)
    await tarama_servisi._gorevler[yanit.tarama_id]


async def test_iptal_edilen_tarama(hizli_mock):
    yanit = await tarama_servisi.baslat("Operator", "K1", ElemanTipi.KOLON, 25.0)

    # Görevin çalışmaya başlayıp uyku noktasına gelmesi için kontrolü bir kez devret.
    # (Aksi halde cancel(), görev hiç başlamadan en başa CancelledError fırlatır.)
    await asyncio.sleep(0)

    await tarama_servisi.iptal_et(yanit.tarama_id)

    gorev = tarama_servisi._gorevler.get(yanit.tarama_id)
    if gorev is not None:
        await gorev  # _calistir CancelledError'ı yutup durumu IPTAL_EDILDI yapar

    durum = await tarama_servisi.durum_al(yanit.tarama_id)
    assert durum.durum == TaramaDurum.IPTAL_EDILDI
