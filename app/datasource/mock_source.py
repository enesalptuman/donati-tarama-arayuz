"""Sahte (mock) veri kaynağı — gerçek algoritma gelene kadar kullanılır.

İşlem süresini config'ten okunan aralıkta (üretim varsayılanı 60-120 sn)
simüle eder ve ilerleme yüzdesini periyodik olarak bildirir; gerçek
algoritma da benzer bir süre alacağı için arayüz bu davranışa göre
tasarlanmıştır. Süre config/env ile ayarlanır (bkz. app/config.py).
"""

from __future__ import annotations

import asyncio
import random

from app.config import ayarlari_al
from app.datasource.base import DataSource, IlerlemeCallback, TaramaCiktisi, TaramaIptalEdildi
from app.generators.image_generator import yansima_haritasi_uret
from app.generators.mock_generator import sahte_sonuc_uret


class MockDataSource(DataSource):
    def __init__(self) -> None:
        self._iptal_edilenler: set[str] = set()

    async def tara(
        self,
        tarama_id: str,
        operator: str,
        konum_etiketi: str,
        ilerleme_cb: IlerlemeCallback,
    ) -> TaramaCiktisi:
        # Süre artık kodda sabit değil; config/env'den gelir (bkz. app/config.py).
        # Üretim: 60-120 sn. Test/geliştirme: DONATI_MOCK_SURE_MIN_SN=3 gibi.
        ayarlar = ayarlari_al()
        toplam_sure_sn = random.uniform(ayarlar.mock_sure_min_sn, ayarlar.mock_sure_maks_sn)
        adim_sn = 0.3
        adim_sayisi = max(int(toplam_sure_sn / adim_sn), 1)

        for adim in range(1, adim_sayisi + 1):
            if tarama_id in self._iptal_edilenler:
                self._iptal_edilenler.discard(tarama_id)
                raise TaramaIptalEdildi(tarama_id)
            await asyncio.sleep(adim_sn)
            yuzde = min(int(adim / adim_sayisi * 100), 99)
            await ilerleme_cb(yuzde)

        if tarama_id in self._iptal_edilenler:
            self._iptal_edilenler.discard(tarama_id)
            raise TaramaIptalEdildi(tarama_id)

        sonuc = sahte_sonuc_uret(tarama_id, operator, konum_etiketi)
        goruntu_png = yansima_haritasi_uret(sonuc)
        await ilerleme_cb(100)
        return TaramaCiktisi(sonuc=sonuc, goruntu_png=goruntu_png)

    async def iptal_et(self, tarama_id: str) -> None:
        self._iptal_edilenler.add(tarama_id)
