"""Pas payı değerlendirmesi ve kritik uyarı — tek kaynaklı iş kuralları.

Gerçek minimum pas payı TS 500 / TBDY 2018'e göre maruziyet sınıfı, yapı
elemanı tipi ve beton sınıfına göre değişir; tek bir sabit sayı her proje
için doğru değildir. Bu yüzden "uygun mu" kararı, tarama başlatılırken
operatör/denetçinin girdiği `TaramaParametreleri.gerekli_pas_payi_mm`
değerine göre hesaplanır — burası sadece bu değeri nasıl yorumlayacağını
(renk/eşik mantığını) tek yerden tanımlar. Hem API yanıtını zenginleştirmek
hem de PDF raporunu üretmek için kullanılır.
"""

from __future__ import annotations

from app.config import ayarlari_al
from app.models.tarama import (
    Donati,
    ElemanTipi,
    ElemanTipiBilgisi,
    KritikUyari,
    PasPayiDurumu,
    TaramaParametreleri,
    TaramaSonucu,
    TaramaSonucuZenginlestirilmis,
)

# TS 500'e yakın tipik varsayımlar — giriş formunda eleman tipi seçilince
# öneri olarak sunulur, operatör projeye göre değiştirebilir. Bunlar
# mühendislik kararı yerine geçmez, sadece makul bir başlangıç noktasıdır.
ELEMAN_TIPI_VARSAYILAN_PAS_PAYI_MM: dict[ElemanTipi, float] = {
    ElemanTipi.KOLON: 25.0,
    ElemanTipi.KIRIS: 25.0,
    ElemanTipi.DOSEME: 20.0,
    ElemanTipi.PERDE: 25.0,
    ElemanTipi.TEMEL: 50.0,
    ElemanTipi.DIGER: 25.0,
}

ELEMAN_TIPI_ETIKETI: dict[ElemanTipi, str] = {
    ElemanTipi.KOLON: "Kolon",
    ElemanTipi.KIRIS: "Kiriş",
    ElemanTipi.DOSEME: "Döşeme",
    ElemanTipi.PERDE: "Perde",
    ElemanTipi.TEMEL: "Temel",
    ElemanTipi.DIGER: "Diğer",
}


def eleman_tipleri_listele() -> list[ElemanTipiBilgisi]:
    return [
        ElemanTipiBilgisi(deger=tip, etiket=ELEMAN_TIPI_ETIKETI[tip], varsayilan_mm=mm)
        for tip, mm in ELEMAN_TIPI_VARSAYILAN_PAS_PAYI_MM.items()
    ]


def varsayilan_parametreler() -> TaramaParametreleri:
    """parametreler.json bulunamayan (eski/test) taramalar için düşülecek varsayım."""
    return TaramaParametreleri(
        eleman_tipi=ElemanTipi.DIGER,
        gerekli_pas_payi_mm=ELEMAN_TIPI_VARSAYILAN_PAS_PAYI_MM[ElemanTipi.DIGER],
    )


def _sinirda_pay_mm() -> float:
    return ayarlari_al().sinirda_pay_mm


def pas_payi_durumu(deger_mm: float, min_mm: float, sinirda_pay_mm: float | None = None) -> PasPayiDurumu:
    pay = _sinirda_pay_mm() if sinirda_pay_mm is None else sinirda_pay_mm
    if deger_mm < min_mm:
        return PasPayiDurumu.YETERSIZ
    if deger_mm <= min_mm + pay:
        return PasPayiDurumu.SINIRDA
    return PasPayiDurumu.UYGUN


def _donatiyi_degerlendir(donati: Donati, min_mm: float, sinirda_pay_mm: float) -> Donati:
    return donati.model_copy(update={"durum": pas_payi_durumu(donati.pas_payi_mm, min_mm, sinirda_pay_mm)})


def kritik_uyari_belirle(sonuc: TaramaSonucu, min_mm: float, sinirda_pay_mm: float | None = None) -> KritikUyari:
    pay = _sinirda_pay_mm() if sinirda_pay_mm is None else sinirda_pay_mm

    if not sonuc.donati_var_mi or not sonuc.donatilar:
        return KritikUyari(
            seviye=PasPayiDurumu.YETERSIZ,
            mesaj="DONATI TESPİT EDİLEMEDİ — taranan bölgede donatı bulunamadı",
        )

    if sonuc.min_pas_payi_mm is not None and sonuc.min_pas_payi_mm < min_mm:
        return KritikUyari(
            seviye=PasPayiDurumu.YETERSIZ,
            mesaj=f"PAS PAYI YETERSİZ — {sonuc.min_pas_payi_mm:.0f} mm (min. {min_mm:.0f} mm)",
        )

    if sonuc.min_pas_payi_mm is not None and sonuc.min_pas_payi_mm <= min_mm + pay:
        return KritikUyari(
            seviye=PasPayiDurumu.SINIRDA,
            mesaj=f"PAS PAYI SINIRDA — {sonuc.min_pas_payi_mm:.0f} mm (min. {min_mm:.0f} mm) — kontrol edilmeli",
        )

    return KritikUyari(seviye=PasPayiDurumu.UYGUN, mesaj="DONATI DÜZENİ UYGUN")


def sonucu_zenginlestir(sonuc: TaramaSonucu, parametreler: TaramaParametreleri) -> TaramaSonucuZenginlestirilmis:
    """Her donatıya `durum` alanını ekler, genel kritik uyarıyı ve kullanılan
    eşikleri hesaplar. Karar, `parametreler.gerekli_pas_payi_mm`'ye (operatör/
    denetçi girdisi) göre verilir — sabit bir uygulama varsayımına değil."""
    min_mm = parametreler.gerekli_pas_payi_mm
    pay = _sinirda_pay_mm()

    degerlendirilmis_donatilar = [_donatiyi_degerlendir(d, min_mm, pay) for d in sonuc.donatilar]
    kritik_uyari = kritik_uyari_belirle(sonuc, min_mm, pay)

    return TaramaSonucuZenginlestirilmis(
        **{**sonuc.model_dump(exclude={"donatilar"}), "donatilar": degerlendirilmis_donatilar},
        kritik_uyari=kritik_uyari,
        parametreler=parametreler,
        sinirda_pas_payi_mm=min_mm + pay,
    )
