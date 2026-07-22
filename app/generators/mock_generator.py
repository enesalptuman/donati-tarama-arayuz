"""Gerçekçi sahte (mock) tarama sonucu üreteci.

Betonarme elemanlarda donatı genelde düzenli bir ızgara halinde dizilir
(boyuna donatı + etriye/enine donatı iki katman olarak). Bu üreteç bu
düzeni küçük rastgele sapmalarla taklit eder; ayrıca ara sıra boşluk
(segregasyon) ve "donatı bulunamadı" senaryoları üretir.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.models.tarama import Bosluk, Donati, Goruntu, TaramaAlani, TaramaSonucu, Yon

# TS 500 / piyasada yaygın donatı çapları (mm)
STANDART_CAPLAR = [8, 10, 12, 14, 16, 18, 20, 22, 26]

TR_SAAT_DILIMI = timezone(timedelta(hours=3))


def _tarama_alani_uret() -> TaramaAlani:
    genislik = random.choice([30, 40, 40, 50, 60])
    yukseklik = random.choice([30, 40, 40, 50, 60])
    return TaramaAlani(genislik_cm=genislik, yukseklik_cm=yukseklik)


def _izgara_konumlari(uzunluk_cm: float, araliknar: tuple[float, float], kenar_bosluk_cm: float) -> list[float]:
    """Belirtilen uzunluk boyunca, ortalama aralıkla düzenli konumlar üretir (küçük sapmalı)."""
    aralik = random.uniform(*araliknar)
    konumlar: list[float] = []
    konum = kenar_bosluk_cm
    while konum <= uzunluk_cm - kenar_bosluk_cm + 1e-6:
        sapma = random.uniform(-0.15, 0.15) * aralik
        konumlar.append(round(max(kenar_bosluk_cm * 0.5, konum + sapma), 1))
        konum += aralik
    return konumlar or [uzunluk_cm / 2]


def _pas_payi_uret(katman: int) -> float:
    # Dış katman (etriye, katman 1) genelde daha az pas payına sahiptir.
    if katman == 1:
        return round(random.uniform(15, 40), 1)
    return round(random.uniform(20, 60), 1)


def _donatilari_uret(alan: TaramaAlani) -> tuple[list[Donati], int]:
    katman_sayisi = random.choices([1, 2], weights=[0.35, 0.65])[0]
    donatilar: list[Donati] = []
    donati_id = 1

    # Düşey doğrultuda donatı sırası (katman 1)
    x_konumlari = _izgara_konumlari(alan.genislik_cm, (12, 20), kenar_bosluk_cm=4)
    cap_1 = random.choice(STANDART_CAPLAR)
    for x in x_konumlari:
        donatilar.append(
            Donati(
                id=donati_id,
                x_cm=x,
                y_cm=round(random.uniform(2, alan.yukseklik_cm - 2), 1),
                cap_mm=cap_1,
                pas_payi_mm=_pas_payi_uret(1),
                katman=1,
                yon=Yon.DUSEY,
                guven=round(random.uniform(0.6, 0.99), 2),
            )
        )
        donati_id += 1

    if katman_sayisi == 2:
        # Yatay doğrultuda ikinci katman (boyuna donatı)
        y_konumlari = _izgara_konumlari(alan.yukseklik_cm, (12, 20), kenar_bosluk_cm=4)
        cap_2 = random.choice(STANDART_CAPLAR)
        for y in y_konumlari:
            donatilar.append(
                Donati(
                    id=donati_id,
                    x_cm=round(random.uniform(2, alan.genislik_cm - 2), 1),
                    y_cm=y,
                    cap_mm=cap_2,
                    pas_payi_mm=_pas_payi_uret(2),
                    katman=2,
                    yon=Yon.YATAY,
                    guven=round(random.uniform(0.6, 0.99), 2),
                )
            )
            donati_id += 1

    return donatilar, katman_sayisi


def _bosluklari_uret(alan: TaramaAlani) -> list[Bosluk]:
    if random.random() > 0.3:
        return []
    adet = random.randint(1, 2)
    bosluklar: list[Bosluk] = []
    for i in range(adet):
        bosluklar.append(
            Bosluk(
                id=i + 1,
                x_cm=round(random.uniform(4, alan.genislik_cm - 4), 1),
                y_cm=round(random.uniform(4, alan.yukseklik_cm - 4), 1),
                boyut_mm=round(random.uniform(10, 30), 1),
                derinlik_mm=round(random.uniform(20, 60), 1),
                guven=round(random.uniform(0.55, 0.95), 2),
            )
        )
    return bosluklar


def sahte_sonuc_uret(tarama_id: str, operator: str, konum_etiketi: str) -> TaramaSonucu:
    """Rastgele ama gerçekçi bir TaramaSonucu üretir."""
    alan = _tarama_alani_uret()
    piksel_boyut_mm = 2.0

    # %10 ihtimalle "donatı bulunamadı" senaryosu (örn. yalıtım/dolgu bölgesi)
    donati_bulunamadi = random.random() < 0.10

    if donati_bulunamadi:
        donatilar: list[Donati] = []
        katman_sayisi = 0
        bosluklar = _bosluklari_uret(alan)
    else:
        donatilar, katman_sayisi = _donatilari_uret(alan)
        bosluklar = _bosluklari_uret(alan)

    pas_paylari = [d.pas_payi_mm for d in donatilar]
    ortalama_pas_payi = round(sum(pas_paylari) / len(pas_paylari), 1) if pas_paylari else None
    min_pas_payi = round(min(pas_paylari), 1) if pas_paylari else None

    return TaramaSonucu(
        tarama_id=tarama_id,
        tarih=datetime.now(TR_SAAT_DILIMI),
        operator=operator,
        konum_etiketi=konum_etiketi,
        tarama_alani=alan,
        goruntu=Goruntu(dosya="harita.png", piksel_boyut_mm=piksel_boyut_mm),
        donati_var_mi=len(donatilar) > 0,
        donati_sayisi=len(donatilar),
        donatilar=donatilar,
        bosluklar=bosluklar,
        katman_sayisi=katman_sayisi,
        ortalama_pas_payi_mm=ortalama_pas_payi,
        min_pas_payi_mm=min_pas_payi,
    )
