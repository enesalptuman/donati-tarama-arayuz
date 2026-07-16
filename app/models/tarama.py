"""Tarama sonucu için Pydantic modelleri.

Bu dosya, rekonstrüksiyon/tespit algoritmasından beklenen JSON çıktısının
tek doğrulama kaynağıdır. Algoritma ekibi şemayı netleştirdikçe sadece
burası güncellenir; API, servis katmanı ve mock üreteç bu modelleri kullanır.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaramaDurum(str, Enum):
    """Bir taramanın yaşam döngüsü durumu."""

    BEKLIYOR = "bekliyor"
    ISLENIYOR = "isleniyor"
    TAMAMLANDI = "tamamlandi"
    HATA = "hata"
    IPTAL_EDILDI = "iptal_edildi"


class Yon(str, Enum):
    DUSEY = "dusey"
    YATAY = "yatay"


class PasPayiDurumu(str, Enum):
    """analiz.py tarafından hesaplanan, tek kaynaklı pas payı değerlendirmesi."""

    UYGUN = "uygun"
    SINIRDA = "sinirda"
    YETERSIZ = "yetersiz"


class ElemanTipi(str, Enum):
    """Gerekli pas payı varsayımı bu tipe göre önerilir (bkz. analiz.py)."""

    KOLON = "kolon"
    KIRIS = "kiris"
    DOSEME = "doseme"
    PERDE = "perde"
    TEMEL = "temel"
    DIGER = "diger"


class TaramaParametreleri(BaseModel):
    """Tarama başlatılırken operatör/denetçi tarafından girilen değerlendirme
    parametreleri. Algoritmanın ürettiği ham ölçümden bağımsızdır; "uygun mu"
    kararı bu değerlere göre analiz.py'de hesaplanır."""

    eleman_tipi: ElemanTipi
    gerekli_pas_payi_mm: float = Field(gt=0)


class ElemanTipiBilgisi(BaseModel):
    """GET /api/eleman-tipleri yanıtındaki tek satır — giriş formundaki
    açılır menüyü ve varsayılan mm değerini tek kaynaktan besler."""

    deger: ElemanTipi
    etiket: str
    varsayilan_mm: float


class TaramaAlani(BaseModel):
    genislik_cm: float
    yukseklik_cm: float


class Goruntu(BaseModel):
    dosya: str
    piksel_boyut_mm: float


class Donati(BaseModel):
    id: int
    x_cm: float
    y_cm: float
    cap_mm: int
    pas_payi_mm: float
    katman: int
    yon: Yon
    guven: float = Field(ge=0.0, le=1.0)
    # Aşağıdaki alan ham algoritma çıktısında yok; analiz.py API yanıtını
    # zenginleştirirken doldurur (persisted sonuc.json'da bulunmaz).
    durum: PasPayiDurumu | None = None


class Bosluk(BaseModel):
    id: int
    x_cm: float
    y_cm: float
    boyut_mm: float
    derinlik_mm: float
    guven: float = Field(ge=0.0, le=1.0)


class TaramaSonucu(BaseModel):
    """Algoritmadan (veya mock üreteçten) gelen, diske kaydedilen tam sonuç."""

    tarama_id: str
    tarih: datetime
    operator: str
    konum_etiketi: str
    tarama_alani: TaramaAlani
    goruntu: Goruntu
    donati_var_mi: bool
    donati_sayisi: int
    donatilar: list[Donati] = Field(default_factory=list)
    bosluklar: list[Bosluk] = Field(default_factory=list)
    katman_sayisi: int
    ortalama_pas_payi_mm: float | None = None
    min_pas_payi_mm: float | None = None


class KritikUyari(BaseModel):
    """Sonuç ekranındaki en üst banda basılan tek cümlelik değerlendirme."""

    seviye: PasPayiDurumu
    mesaj: str


class TaramaSonucuZenginlestirilmis(TaramaSonucu):
    """API'nin GET /api/tarama/{id} için döndüğü, analiz.py ile zenginleştirilmiş sonuç."""

    kritik_uyari: KritikUyari
    parametreler: TaramaParametreleri
    # min + sinirda_pay_mm, analiz.py'de hesaplanır — frontend bu sabiti bilmek zorunda kalmaz.
    sinirda_pas_payi_mm: float


class TaramaOzet(BaseModel):
    """Geçmiş taramalar listesinde (GET /api/taramalar) gösterilen özet satır."""

    tarama_id: str
    tarih: datetime
    operator: str
    konum_etiketi: str
    donati_sayisi: int
    kritik_uyari_var_mi: bool
    durum: TaramaDurum


class TaramaDurumBilgisi(BaseModel):
    """GET /api/tarama/{id}/durum yanıtı."""

    tarama_id: str
    durum: TaramaDurum
    ilerleme: int = Field(ge=0, le=100)
    hata_mesaji: str | None = None


class TaramaBaslatIstegi(BaseModel):
    """POST /api/tarama/baslat gövdesi."""

    operator: str = Field(min_length=1)
    konum_etiketi: str = Field(min_length=1)
    eleman_tipi: ElemanTipi
    gerekli_pas_payi_mm: float = Field(gt=0)


class TaramaBaslatYaniti(BaseModel):
    tarama_id: str


class DepolamaDurumu(BaseModel):
    """GET /api/depolama-durumu — disk birikmesi uyarısı için."""

    tarama_sayisi: int
    uyari_esigi: int
    maks_tarama_sayisi: int
    uyari_var_mi: bool
