"""analiz.py birim testleri — saf iş kuralları (DB/HTTP/dosya yok).

Öğretilen teknikler:
  - AAA deseni (Arrange–Act–Assert): her testin üç fazı
  - @pytest.mark.parametrize: tek testi çok girdiyle çalıştırma
  - "aynı veri / farklı eşik" testi: kararın operatör girdisine bağlı olduğunu kanıtlar
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.tarama import (
    Donati,
    ElemanTipi,
    Goruntu,
    PasPayiDurumu,
    TaramaAlani,
    TaramaParametreleri,
    TaramaSonucu,
    Yon,
)
from app.services import analiz


def _sonuc_yap(pas_paylari: list[float]) -> TaramaSonucu:
    """Test yardımcı fonksiyonu: verilen pas payı listesinden bir TaramaSonucu kurar.

    Testte tekrar eden nesne kurulumunu tek yere toplar (DRY). Sadece testin
    umursadığı alanları (pas payları) parametre alır, gerisini sabit doldurur.
    """
    donatilar = [
        Donati(id=i + 1, x_cm=5.0 * i + 2, y_cm=10.0, cap_mm=12, pas_payi_mm=pp,
               katman=1, yon=Yon.DUSEY, guven=0.9)
        for i, pp in enumerate(pas_paylari)
    ]
    return TaramaSonucu(
        tarama_id="t", tarih=datetime.now(UTC), operator="op", konum_etiketi="k",
        tarama_alani=TaramaAlani(genislik_cm=40, yukseklik_cm=40),
        goruntu=Goruntu(dosya="harita.png", piksel_boyut_mm=2.0),
        donati_var_mi=len(donatilar) > 0,
        donati_sayisi=len(donatilar),
        donatilar=donatilar,
        bosluklar=[],
        katman_sayisi=1,
        ortalama_pas_payi_mm=(sum(pas_paylari) / len(pas_paylari)) if pas_paylari else None,
        min_pas_payi_mm=min(pas_paylari) if pas_paylari else None,
    )


# ---------------------------------------------------------------------------
# 1) pas_payi_durumu — eşik mantığı. parametrize ile 7 sınır durumu tek testte.
#    min=25, pay=10 → yetersiz < 25, sınırda 25..35, uygun > 35
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "deger, beklenen",
    [
        (20.0, PasPayiDurumu.YETERSIZ),  # eşiğin çok altı
        (24.9, PasPayiDurumu.YETERSIZ),  # eşiğin hemen altı
        (25.0, PasPayiDurumu.SINIRDA),   # tam eşik → sınırda başlar
        (30.0, PasPayiDurumu.SINIRDA),   # sınırda bölgesinin ortası
        (35.0, PasPayiDurumu.SINIRDA),   # min+pay tam sınırı → hâlâ sınırda
        (35.1, PasPayiDurumu.UYGUN),     # sınırın hemen üstü → uygun
        (50.0, PasPayiDurumu.UYGUN),     # rahatça uygun
    ],
)
def test_pas_payi_durumu_esikleri(deger, beklenen):
    # Act + Assert (Arrange yok — girdiler parametrize'dan geliyor)
    sonuc = analiz.pas_payi_durumu(deger, min_mm=25.0, sinirda_pay_mm=10.0)
    assert sonuc == beklenen


# ---------------------------------------------------------------------------
# 2) kritik_uyari_belirle — dört senaryo, her biri AAA deseniyle
# ---------------------------------------------------------------------------
def test_kritik_uyari_donati_bulunamadi():
    # Arrange: hiç donatı olmayan sonuç
    sonuc = _sonuc_yap([])
    # Act
    uyari = analiz.kritik_uyari_belirle(sonuc, min_mm=25.0, sinirda_pay_mm=10.0)
    # Assert: en kötü haber — donatı yok
    assert uyari.seviye == PasPayiDurumu.YETERSIZ
    assert "TESPİT EDİLEMEDİ" in uyari.mesaj


def test_kritik_uyari_yetersiz():
    # Arrange: en düşük pas payı 20 mm, gereken 25 mm
    sonuc = _sonuc_yap([20.0, 40.0, 55.0])
    # Act
    uyari = analiz.kritik_uyari_belirle(sonuc, min_mm=25.0, sinirda_pay_mm=10.0)
    # Assert: minimum eşiğin altında → yetersiz, mesajda gereken değer görünür
    assert uyari.seviye == PasPayiDurumu.YETERSIZ
    assert "20 mm" in uyari.mesaj
    assert "min. 25 mm" in uyari.mesaj


def test_kritik_uyari_sinirda():
    # Arrange: en düşük 30 mm; 25 <= 30 <= 35 → sınırda
    sonuc = _sonuc_yap([30.0, 45.0])
    uyari = analiz.kritik_uyari_belirle(sonuc, min_mm=25.0, sinirda_pay_mm=10.0)
    assert uyari.seviye == PasPayiDurumu.SINIRDA


def test_kritik_uyari_uygun():
    # Arrange: hepsi rahatça eşiğin üstünde
    sonuc = _sonuc_yap([40.0, 50.0, 60.0])
    uyari = analiz.kritik_uyari_belirle(sonuc, min_mm=25.0, sinirda_pay_mm=10.0)
    assert uyari.seviye == PasPayiDurumu.UYGUN
    assert uyari.mesaj == "DONATI DÜZENİ UYGUN"


# ---------------------------------------------------------------------------
# 3) AYNI VERİ / FARKLI EŞİK — projenin en kritik kararının testi.
#    Kararın yazılımın sabitine değil, operatörün girdiği eşiğe bağlı olduğunu
#    kanıtlar. Aynı ölçüm (min 40 mm) farklı eşiklerde farklı sonuç verir.
# ---------------------------------------------------------------------------
def test_ayni_veri_farkli_esik_farkli_karar():
    sonuc = _sonuc_yap([40.0, 48.0])  # ölçülen minimum: 40 mm (sabit)

    # Kolon eşiği (25 mm) → 40 rahatça yeterli
    kolon = analiz.kritik_uyari_belirle(sonuc, min_mm=25.0, sinirda_pay_mm=10.0)
    assert kolon.seviye == PasPayiDurumu.UYGUN

    # Temel eşiği (45 mm) → AYNI 40 mm artık yetersiz
    temel = analiz.kritik_uyari_belirle(sonuc, min_mm=45.0, sinirda_pay_mm=10.0)
    assert temel.seviye == PasPayiDurumu.YETERSIZ


# ---------------------------------------------------------------------------
# 4) sonucu_zenginlestir — API'nin döndüğü zenginleştirilmiş sonuç
# ---------------------------------------------------------------------------
def test_sonucu_zenginlestir_alanlari_doldurur():
    # Arrange
    sonuc = _sonuc_yap([20.0, 50.0])
    parametreler = TaramaParametreleri(eleman_tipi=ElemanTipi.KOLON, gerekli_pas_payi_mm=25.0)

    # Act
    zengin = analiz.sonucu_zenginlestir(sonuc, parametreler)

    # Assert: her donatıya durum eklendi
    assert all(d.durum is not None for d in zengin.donatilar)
    assert zengin.donatilar[0].durum == PasPayiDurumu.YETERSIZ  # 20 < 25
    assert zengin.donatilar[1].durum == PasPayiDurumu.UYGUN     # 50 > 35
    # Genel kritik uyarı ve parametreler yansıtıldı
    assert zengin.kritik_uyari.seviye == PasPayiDurumu.YETERSIZ
    assert zengin.parametreler.gerekli_pas_payi_mm == 25.0
    # sınırda eşiği = gerekli + pay (frontend bu sabiti bilmek zorunda değil)
    assert zengin.sinirda_pas_payi_mm == 25.0 + analiz._sinirda_pay_mm()


# ---------------------------------------------------------------------------
# 5) eleman_tipleri_listele — dropdown'ı besleyen liste
# ---------------------------------------------------------------------------
def test_eleman_tipleri_listele():
    liste = analiz.eleman_tipleri_listele()
    assert len(liste) == 6
    # sözlüğe çevirip birkaç varsayımı doğrula
    varsayilanlar = {b.deger: b.varsayilan_mm for b in liste}
    assert varsayilanlar[ElemanTipi.KOLON] == 25.0
    assert varsayilanlar[ElemanTipi.TEMEL] == 50.0  # temel toprakla temasta → yüksek


def test_varsayilan_parametreler_diger_25():
    p = analiz.varsayilan_parametreler()
    assert p.eleman_tipi == ElemanTipi.DIGER
    assert p.gerekli_pas_payi_mm == 25.0
