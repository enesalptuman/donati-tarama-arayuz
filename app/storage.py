"""Kalıcı katman — meta veri PostgreSQL'de, görüntü PNG'leri dosya sisteminde.

Faz 3'te dosya-tabanlı JSON depolamadan veritabanına geçildi. Servis katmanı
bu modülün fonksiyonlarını çağırır; DB olduğunu bilmesi gerekmez (fonksiyonlar
artık async). Görüntüler büyük ikili veri olduğu için DB yerine diskte tutulur
(taramalar/{id}/harita.png) ve statik olarak servis edilir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import func, select

from app import db
from app.config import TARAMALAR_DIZINI
from app.db_models import TaramaKaydi
from app.models.tarama import (
    ElemanTipi,
    PasPayiDurumu,
    TaramaDurum,
    TaramaDurumBilgisi,
    TaramaOzet,
    TaramaParametreleri,
    TaramaSonucu,
)
from app.services import analiz

# ---------------------------------------------------------------------------
# Görüntü (dosya sistemi) — DB'de tutulmaz
# ---------------------------------------------------------------------------


def tarama_dizini(tarama_id: str) -> Path:
    dizin = TARAMALAR_DIZINI / tarama_id
    dizin.mkdir(parents=True, exist_ok=True)
    return dizin


def goruntuyu_kaydet(tarama_id: str, png_bayt: bytes) -> None:
    (tarama_dizini(tarama_id) / "harita.png").write_bytes(png_bayt)


def goruntu_yolu(tarama_id: str) -> Path | None:
    dosya = TARAMALAR_DIZINI / tarama_id / "harita.png"
    return dosya if dosya.exists() else None


# ---------------------------------------------------------------------------
# Meta veri (PostgreSQL)
# ---------------------------------------------------------------------------


async def tarama_olustur(
    tarama_id: str,
    operator: str,
    konum_etiketi: str,
    eleman_tipi: ElemanTipi,
    gerekli_pas_payi_mm: float,
) -> None:
    """Yeni tarama satırını BEKLIYOR durumuyla ekler (INSERT)."""
    async with db.oturum_ac() as s:
        s.add(
            TaramaKaydi(
                tarama_id=tarama_id,
                operator=operator,
                konum_etiketi=konum_etiketi,
                eleman_tipi=eleman_tipi.value,
                gerekli_pas_payi_mm=gerekli_pas_payi_mm,
                durum=TaramaDurum.BEKLIYOR.value,
                ilerleme=0,
            )
        )
        await s.commit()


async def durum_guncelle(
    tarama_id: str,
    durum: TaramaDurum,
    ilerleme: int,
    hata_mesaji: str | None = None,
) -> None:
    """Taramanın durum/ilerleme alanlarını günceller (UPDATE)."""
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is None:
            return
        kayit.durum = durum.value
        kayit.ilerleme = ilerleme
        if hata_mesaji is not None:
            kayit.hata_mesaji = hata_mesaji
        await s.commit()


async def sonuc_guncelle(tarama_id: str, sonuc: TaramaSonucu) -> None:
    """Tamamlanan taramanın sonuç JSON'unu ve tarihini yazar (UPDATE)."""
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is None:
            return
        kayit.sonuc_json = sonuc.model_dump_json()
        kayit.tarih = sonuc.tarih
        await s.commit()


async def durumu_oku(tarama_id: str) -> TaramaDurumBilgisi | None:
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is None:
            return None
        return TaramaDurumBilgisi(
            tarama_id=kayit.tarama_id,
            durum=TaramaDurum(kayit.durum),
            ilerleme=kayit.ilerleme,
            hata_mesaji=kayit.hata_mesaji,
        )


async def sonucu_oku(tarama_id: str) -> TaramaSonucu | None:
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is None or kayit.sonuc_json is None:
            return None
        return TaramaSonucu.model_validate_json(kayit.sonuc_json)


async def parametreler_oku(tarama_id: str) -> TaramaParametreleri | None:
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is None:
            return None
        return TaramaParametreleri(
            eleman_tipi=ElemanTipi(kayit.eleman_tipi),
            gerekli_pas_payi_mm=kayit.gerekli_pas_payi_mm,
        )


async def tarama_var_mi(tarama_id: str) -> bool:
    async with db.oturum_ac() as s:
        return await s.get(TaramaKaydi, tarama_id) is not None


async def taramayi_sil(tarama_id: str) -> None:
    """DB satırını ve varsa görüntü dizinini siler."""
    async with db.oturum_ac() as s:
        kayit = await s.get(TaramaKaydi, tarama_id)
        if kayit is not None:
            await s.delete(kayit)
            await s.commit()
    dizin = TARAMALAR_DIZINI / tarama_id
    if dizin.exists():
        shutil.rmtree(dizin)


async def taramalari_listele() -> list[TaramaOzet]:
    """Tüm taramaları en yeniden eskiye özet olarak döner."""
    async with db.oturum_ac() as s:
        satirlar = (
            (await s.execute(select(TaramaKaydi).order_by(TaramaKaydi.olusturma_zamani.desc())))
            .scalars()
            .all()
        )

    ozetler: list[TaramaOzet] = []
    for k in satirlar:
        donati_sayisi = 0
        kritik_uyari_var = False
        if k.sonuc_json is not None:
            sonuc = TaramaSonucu.model_validate_json(k.sonuc_json)
            donati_sayisi = sonuc.donati_sayisi
            # Kritik uyarı hesabı tek kaynaktan (analiz.py); eşik operatör girdisi
            uyari = analiz.kritik_uyari_belirle(sonuc, k.gerekli_pas_payi_mm)
            kritik_uyari_var = uyari.seviye != PasPayiDurumu.UYGUN
        ozetler.append(
            TaramaOzet(
                tarama_id=k.tarama_id,
                tarih=k.tarih or k.olusturma_zamani,
                operator=k.operator,
                konum_etiketi=k.konum_etiketi,
                donati_sayisi=donati_sayisi,
                kritik_uyari_var_mi=kritik_uyari_var,
                durum=TaramaDurum(k.durum),
            )
        )
    return ozetler


async def tamamlanan_tarama_sayisi() -> int:
    async with db.oturum_ac() as s:
        return (
            await s.execute(
                select(func.count())
                .select_from(TaramaKaydi)
                .where(TaramaKaydi.durum == TaramaDurum.TAMAMLANDI.value)
            )
        ).scalar_one()


async def eski_taramalari_buda(maks_sayi: int) -> list[str]:
    """En yeni `maks_sayi` tamamlanmış taramayı tutar, daha eskilerini siler.

    maks_sayi <= 0 ise hiçbir şey silmez (sınırsız = otomatik silme kapalı).
    """
    if maks_sayi <= 0:
        return []
    ozetler = await taramalari_listele()  # en yeniden eskiye sıralı
    tamamlananlar = [o for o in ozetler if o.durum == TaramaDurum.TAMAMLANDI]
    silinecekler = tamamlananlar[maks_sayi:]
    silinen_idler: list[str] = []
    for ozet in silinecekler:
        await taramayi_sil(ozet.tarama_id)
        silinen_idler.append(ozet.tarama_id)
    return silinen_idler
