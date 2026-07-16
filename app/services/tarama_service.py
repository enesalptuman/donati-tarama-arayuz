"""Tarama orkestrasyonu.

Router'ların konuştuğu tek katman budur. DataSource'un mock mu gerçek mi
olduğunu bilmez — sadece `app.datasource.factory.veri_kaynagi_al()` ile
aldığı soyut arayüzü kullanır. Arka plan görevlerini yönetir, ilerlemeyi
bellekte tutar, tamamlananları diske kalıcı kaydeder.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.config import ayarlari_al
from app.datasource.base import TaramaIptalEdildi
from app.datasource.factory import veri_kaynagi_al
from app import storage
from app.models.tarama import (
    DepolamaDurumu,
    ElemanTipi,
    TaramaBaslatYaniti,
    TaramaDurum,
    TaramaDurumBilgisi,
    TaramaOzet,
    TaramaParametreleri,
    TaramaSonucuZenginlestirilmis,
)
from app.services import analiz

logger = logging.getLogger("tarama_service")


class TaramaBulunamadi(Exception):
    pass


class TaramaDurumHatasi(Exception):
    """İstenen işlem, taramanın mevcut durumuyla uyumsuz olduğunda (örn. tamamlanmışı iptal etmek)."""


class TaramaService:
    def __init__(self) -> None:
        self._gorevler: dict[str, asyncio.Task] = {}
        self._ilerleme: dict[str, int] = {}

    def _yeni_id_uret(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    def _aktif_tarama_var_mi(self) -> bool:
        """Devam etmekte olan (henüz bitmemiş) bir arka plan taraması var mı?"""
        return any(not gorev.done() for gorev in self._gorevler.values())

    async def baslat(
        self,
        operator: str,
        konum_etiketi: str,
        eleman_tipi: ElemanTipi,
        gerekli_pas_payi_mm: float,
    ) -> TaramaBaslatYaniti:
        # Tek operatörlü el cihazı: aynı anda yalnızca bir tarama çalışabilir.
        if self._aktif_tarama_var_mi():
            raise TaramaDurumHatasi("Zaten devam eden bir tarama var. Bitmesini bekleyin veya iptal edin.")

        tarama_id = self._yeni_id_uret()
        while storage.tarama_var_mi(tarama_id):
            await asyncio.sleep(1)
            tarama_id = self._yeni_id_uret()

        self._ilerleme[tarama_id] = 0
        storage.parametreler_kaydet(
            tarama_id,
            TaramaParametreleri(eleman_tipi=eleman_tipi, gerekli_pas_payi_mm=gerekli_pas_payi_mm),
        )
        storage.durumu_kaydet(
            tarama_id, TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.BEKLIYOR, ilerleme=0)
        )

        gorev = asyncio.create_task(self._calistir(tarama_id, operator, konum_etiketi))
        self._gorevler[tarama_id] = gorev
        return TaramaBaslatYaniti(tarama_id=tarama_id)

    async def _ilerleme_guncelle(self, tarama_id: str, yuzde: int) -> None:
        self._ilerleme[tarama_id] = yuzde
        storage.durumu_kaydet(
            tarama_id, TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.ISLENIYOR, ilerleme=yuzde)
        )

    async def _calistir(self, tarama_id: str, operator: str, konum_etiketi: str) -> None:
        veri_kaynagi = veri_kaynagi_al()
        storage.durumu_kaydet(
            tarama_id, TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.ISLENIYOR, ilerleme=0)
        )
        try:
            ciktisi = await veri_kaynagi.tara(
                tarama_id,
                operator,
                konum_etiketi,
                ilerleme_cb=lambda yuzde: self._ilerleme_guncelle(tarama_id, yuzde),
            )
            storage.sonucu_kaydet(tarama_id, ciktisi.sonuc)
            storage.goruntuyu_kaydet(tarama_id, ciktisi.goruntu_png)
            self._ilerleme[tarama_id] = 100
            storage.durumu_kaydet(
                tarama_id, TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.TAMAMLANDI, ilerleme=100)
            )
            # Config'te limit tanımlıysa (maks_tarama_sayisi > 0) en eski
            # tamamlanmış taramaları buda. Varsayılan 0 = otomatik silme yok.
            budanan = storage.eski_taramalari_buda(ayarlari_al().maks_tarama_sayisi)
            if budanan:
                logger.info("Disk limiti: %d eski tarama budandı: %s", len(budanan), budanan)
        except (TaramaIptalEdildi, asyncio.CancelledError):
            storage.durumu_kaydet(
                tarama_id,
                TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.IPTAL_EDILDI, ilerleme=self._ilerleme.get(tarama_id, 0)),
            )
        except Exception as exc:  # taramanın kendisi başarısız oldu — arayüze hata olarak yansıt
            logger.exception("Tarama başarısız: %s", tarama_id)
            storage.durumu_kaydet(
                tarama_id,
                TaramaDurumBilgisi(
                    tarama_id=tarama_id,
                    durum=TaramaDurum.HATA,
                    ilerleme=self._ilerleme.get(tarama_id, 0),
                    hata_mesaji=str(exc),
                ),
            )
        finally:
            self._gorevler.pop(tarama_id, None)

    async def durum_al(self, tarama_id: str) -> TaramaDurumBilgisi:
        durum_bilgisi = storage.durumu_oku(tarama_id)
        if durum_bilgisi is None:
            raise TaramaBulunamadi(tarama_id)
        return durum_bilgisi

    async def sonuc_al(self, tarama_id: str) -> TaramaSonucuZenginlestirilmis:
        sonuc = storage.sonucu_oku(tarama_id)
        if sonuc is None:
            raise TaramaBulunamadi(tarama_id)
        parametreler = storage.parametreler_oku(tarama_id) or analiz.varsayilan_parametreler()
        return analiz.sonucu_zenginlestir(sonuc, parametreler)

    async def iptal_et(self, tarama_id: str) -> None:
        if not storage.tarama_var_mi(tarama_id):
            raise TaramaBulunamadi(tarama_id)
        veri_kaynagi = veri_kaynagi_al()
        await veri_kaynagi.iptal_et(tarama_id)
        gorev = self._gorevler.get(tarama_id)
        if gorev is not None:
            gorev.cancel()

    async def sil(self, tarama_id: str) -> None:
        if not storage.tarama_var_mi(tarama_id):
            raise TaramaBulunamadi(tarama_id)
        if tarama_id in self._gorevler:
            raise TaramaDurumHatasi("Devam eden bir tarama silinemez, önce iptal edin.")
        storage.taramayi_sil(tarama_id)

    async def listele(self) -> list[TaramaOzet]:
        return storage.taramalari_listele()

    async def depolama_durumu(self) -> DepolamaDurumu:
        ayarlar = ayarlari_al()
        sayi = storage.tamamlanan_tarama_sayisi()
        uyari_var = ayarlar.uyari_tarama_sayisi > 0 and sayi >= ayarlar.uyari_tarama_sayisi
        return DepolamaDurumu(
            tarama_sayisi=sayi,
            uyari_esigi=ayarlar.uyari_tarama_sayisi,
            maks_tarama_sayisi=ayarlar.maks_tarama_sayisi,
            uyari_var_mi=uyari_var,
        )

    def baslangicta_kesilmisleri_isaretle(self) -> None:
        """Pi yeniden başladığında: 'isleniyor'/'bekliyor' görünen ama artık aktif
        görevi olmayan taramaları 'hata' (kesildi) olarak işaretler."""
        for ozet in storage.taramalari_listele():
            if ozet.durum in (TaramaDurum.ISLENIYOR, TaramaDurum.BEKLIYOR) and ozet.tarama_id not in self._gorevler:
                storage.durumu_kaydet(
                    ozet.tarama_id,
                    TaramaDurumBilgisi(
                        tarama_id=ozet.tarama_id,
                        durum=TaramaDurum.HATA,
                        ilerleme=0,
                        hata_mesaji="Cihaz yeniden başlatıldığı için tarama yarıda kesildi.",
                    ),
                )


tarama_servisi = TaramaService()
