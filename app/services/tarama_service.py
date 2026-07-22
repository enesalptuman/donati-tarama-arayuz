"""Tarama orkestrasyonu.

Router'ların konuştuğu tek katman budur. DataSource'un mock mu gerçek mi
olduğunu bilmez; storage'ın DB mi dosya mı olduğunu da bilmez — sadece soyut
arayüzlerle konuşur. Arka plan görevlerini yönetir, tamamlananları kalıcı
kaydeder (meta veri PostgreSQL'de, görüntü diskte).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app import storage
from app.config import ayarlari_al
from app.datasource.base import TaramaIptalEdildi
from app.datasource.factory import veri_kaynagi_al
from app.models.tarama import (
    DepolamaDurumu,
    ElemanTipi,
    TaramaBaslatYaniti,
    TaramaDurum,
    TaramaDurumBilgisi,
    TaramaOzet,
    TaramaSonucuZenginlestirilmis,
)
from app.services import analiz

logger = logging.getLogger("tarama_service")


class TaramaBulunamadi(Exception):
    pass


class TaramaDurumHatasi(Exception):
    """İstenen işlem, taramanın mevcut durumuyla uyumsuz olduğunda."""


class TaramaService:
    def __init__(self) -> None:
        self._gorevler: dict[str, asyncio.Task] = {}
        self._ilerleme: dict[str, int] = {}

    def _yeni_id_uret(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")

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
        while await storage.tarama_var_mi(tarama_id):
            await asyncio.sleep(1)
            tarama_id = self._yeni_id_uret()

        self._ilerleme[tarama_id] = 0
        # Tek INSERT: operatör girdisi + BEKLIYOR durumu tek satırda kaydedilir.
        await storage.tarama_olustur(tarama_id, operator, konum_etiketi, eleman_tipi, gerekli_pas_payi_mm)

        gorev = asyncio.create_task(self._calistir(tarama_id, operator, konum_etiketi))
        self._gorevler[tarama_id] = gorev
        return TaramaBaslatYaniti(tarama_id=tarama_id)

    async def _ilerleme_guncelle(self, tarama_id: str, yuzde: int) -> None:
        self._ilerleme[tarama_id] = yuzde
        await storage.durum_guncelle(tarama_id, TaramaDurum.ISLENIYOR, yuzde)

    async def _calistir(self, tarama_id: str, operator: str, konum_etiketi: str) -> None:
        veri_kaynagi = veri_kaynagi_al()
        await storage.durum_guncelle(tarama_id, TaramaDurum.ISLENIYOR, 0)
        try:
            ciktisi = await veri_kaynagi.tara(
                tarama_id,
                operator,
                konum_etiketi,
                ilerleme_cb=lambda yuzde: self._ilerleme_guncelle(tarama_id, yuzde),
            )
            await storage.sonuc_guncelle(tarama_id, ciktisi.sonuc)
            storage.goruntuyu_kaydet(tarama_id, ciktisi.goruntu_png)  # görüntü diske (sync)
            self._ilerleme[tarama_id] = 100
            await storage.durum_guncelle(tarama_id, TaramaDurum.TAMAMLANDI, 100)
            # Config'te limit tanımlıysa (maks_tarama_sayisi > 0) en eski
            # tamamlanmış taramaları buda. Varsayılan 0 = otomatik silme yok.
            budanan = await storage.eski_taramalari_buda(ayarlari_al().maks_tarama_sayisi)
            if budanan:
                logger.info("Disk limiti: %d eski tarama budandı: %s", len(budanan), budanan)
        except (TaramaIptalEdildi, asyncio.CancelledError):
            # Görev iptal edildiyse, temizlik DB yazmasının da iptal edilmemesi
            # için iptal sayacını sıfırla (Python 3.11+ uncancel deseni).
            gorev = asyncio.current_task()
            if gorev is not None:
                gorev.uncancel()
            await storage.durum_guncelle(
                tarama_id, TaramaDurum.IPTAL_EDILDI, self._ilerleme.get(tarama_id, 0)
            )
        except Exception as exc:  # taramanın kendisi başarısız oldu — arayüze hata olarak yansıt
            logger.exception("Tarama başarısız: %s", tarama_id)
            await storage.durum_guncelle(
                tarama_id, TaramaDurum.HATA, self._ilerleme.get(tarama_id, 0), hata_mesaji=str(exc)
            )
        finally:
            self._gorevler.pop(tarama_id, None)

    async def durum_al(self, tarama_id: str) -> TaramaDurumBilgisi:
        durum_bilgisi = await storage.durumu_oku(tarama_id)
        if durum_bilgisi is None:
            raise TaramaBulunamadi(tarama_id)
        return durum_bilgisi

    async def sonuc_al(self, tarama_id: str) -> TaramaSonucuZenginlestirilmis:
        sonuc = await storage.sonucu_oku(tarama_id)
        if sonuc is None:
            raise TaramaBulunamadi(tarama_id)
        parametreler = await storage.parametreler_oku(tarama_id) or analiz.varsayilan_parametreler()
        return analiz.sonucu_zenginlestir(sonuc, parametreler)

    async def iptal_et(self, tarama_id: str) -> None:
        if not await storage.tarama_var_mi(tarama_id):
            raise TaramaBulunamadi(tarama_id)
        # İşbirlikçi iptal: veri kaynağına iptal bayrağını set et. DataSource
        # bunu periyodik kontrol edip TaramaIptalEdildi fırlatır (mock her
        # ~0.3 sn'de kontrol eder). Sert görev iptali (task.cancel) bilinçli
        # KULLANILMIYOR — çünkü devam eden DB temizlik yazmasını da iptal edip
        # kaydı tutarsız bırakabilir; işbirlikçi iptal temiz sonlanmayı garanti eder.
        veri_kaynagi = veri_kaynagi_al()
        await veri_kaynagi.iptal_et(tarama_id)

    async def sil(self, tarama_id: str) -> None:
        if not await storage.tarama_var_mi(tarama_id):
            raise TaramaBulunamadi(tarama_id)
        if tarama_id in self._gorevler:
            raise TaramaDurumHatasi("Devam eden bir tarama silinemez, önce iptal edin.")
        await storage.taramayi_sil(tarama_id)

    async def listele(self) -> list[TaramaOzet]:
        return await storage.taramalari_listele()

    async def depolama_durumu(self) -> DepolamaDurumu:
        ayarlar = ayarlari_al()
        sayi = await storage.tamamlanan_tarama_sayisi()
        uyari_var = ayarlar.uyari_tarama_sayisi > 0 and sayi >= ayarlar.uyari_tarama_sayisi
        return DepolamaDurumu(
            tarama_sayisi=sayi,
            uyari_esigi=ayarlar.uyari_tarama_sayisi,
            maks_tarama_sayisi=ayarlar.maks_tarama_sayisi,
            uyari_var_mi=uyari_var,
        )

    async def baslangicta_kesilmisleri_isaretle(self) -> None:
        """Cihaz/uygulama yeniden başladığında: 'isleniyor'/'bekliyor' görünen ama
        artık aktif görevi olmayan taramaları 'hata' (kesildi) olarak işaretler."""
        for ozet in await storage.taramalari_listele():
            if (
                ozet.durum in (TaramaDurum.ISLENIYOR, TaramaDurum.BEKLIYOR)
                and ozet.tarama_id not in self._gorevler
            ):
                await storage.durum_guncelle(
                    ozet.tarama_id,
                    TaramaDurum.HATA,
                    0,
                    hata_mesaji="Cihaz yeniden başlatıldığı için tarama yarıda kesildi.",
                )


tarama_servisi = TaramaService()
