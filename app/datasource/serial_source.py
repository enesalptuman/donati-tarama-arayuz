"""Gerçek veri kaynağı iskeleti — STM32H753'ten USB/seri üzerinden okuma.

Bu sınıf şu an sadece iskelettir. Rekonstrüksiyon ve donatı tespit
algoritması başka bir ekip tarafından geliştiriliyor; şema netleşip
algoritma teslim edildiğinde aşağıdaki TODO'lar doldurulacak.

Geçiş için yapılması gerekenler:
  1. `config.yaml` içinde `veri_kaynagi: serial` yapın.
  2. `_baglan`, `_veri_oku`, `_isle` metodlarını gerçek protokole göre doldurun.
  3. Üretilen sonucu `app.models.tarama.TaramaSonucu` ile doğrulayın
     (şema uyuşmazlığı olursa Pydantic doğrulama hatası fırlatır — bu
     istenen davranıştır, sessizce geçersiz veri kabul edilmez).

Arayüz ve API kodunda HİÇBİR değişiklik gerekmez; sadece bu dosya ve
config.yaml değişir.
"""

from __future__ import annotations

from app.config import ayarlari_al
from app.datasource.base import DataSource, IlerlemeCallback, TaramaCiktisi


class SerialDataSource(DataSource):
    def __init__(self) -> None:
        ayarlar = ayarlari_al()
        self._port = ayarlar.seri_port
        self._baud = ayarlar.seri_baud
        self._iptal_edilenler: set[str] = set()

    async def _baglan(self) -> None:
        """TODO: pyserial ile STM32H753'e bağlan (self._port, self._baud)."""
        raise NotImplementedError("SerialDataSource henüz iskelet halinde — gerçek protokol bekleniyor.")

    async def _veri_oku(self, tarama_id: str, ilerleme_cb: IlerlemeCallback):
        """TODO: STM32'den ham veri toplama akışını oku, ilerleme_cb ile yüzde bildir."""
        raise NotImplementedError

    async def _isle(self, ham_veri) -> TaramaCiktisi:
        """TODO: Rekonstrüksiyon + donatı tespiti sonucunu TaramaSonucu'na dönüştür."""
        raise NotImplementedError

    async def tara(
        self,
        tarama_id: str,
        operator: str,
        konum_etiketi: str,
        ilerleme_cb: IlerlemeCallback,
    ) -> TaramaCiktisi:
        await self._baglan()
        ham_veri = await self._veri_oku(tarama_id, ilerleme_cb)
        return await self._isle(ham_veri)

    async def iptal_et(self, tarama_id: str) -> None:
        """TODO: Donanıma iptal/durdurma komutu gönder."""
        self._iptal_edilenler.add(tarama_id)
