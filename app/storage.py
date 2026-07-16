"""Taramaların diske kalıcı kaydı ve okunması.

Her tarama `taramalar/{id}/` altında üç dosyayla tutulur:
  - durum.json  → yaşam döngüsü durumu + ilerleme (işlem sırasında güncellenir)
  - sonuc.json  → tamamlandığında yazılan, algoritma şemasına uyan tam sonuç
  - harita.png  → yansıma haritası

Pi yeniden başlasa bile taramalar kaybolmaz; TaramaService, durum.json'u
kullanarak yarıda kesilmiş taramaları "hata" olarak işaretler.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.config import TARAMALAR_DIZINI
from app.models.tarama import TaramaDurum, TaramaDurumBilgisi, TaramaOzet, TaramaParametreleri, TaramaSonucu
from app.services import analiz


def tarama_dizini(tarama_id: str) -> Path:
    dizin = TARAMALAR_DIZINI / tarama_id
    dizin.mkdir(parents=True, exist_ok=True)
    return dizin


def durumu_kaydet(tarama_id: str, durum_bilgisi: TaramaDurumBilgisi) -> None:
    dizin = tarama_dizini(tarama_id)
    (dizin / "durum.json").write_text(durum_bilgisi.model_dump_json(indent=2), encoding="utf-8")


def durumu_oku(tarama_id: str) -> TaramaDurumBilgisi | None:
    dosya = TARAMALAR_DIZINI / tarama_id / "durum.json"
    if not dosya.exists():
        return None
    return TaramaDurumBilgisi.model_validate_json(dosya.read_text(encoding="utf-8"))


def sonucu_kaydet(tarama_id: str, sonuc: TaramaSonucu) -> None:
    dizin = tarama_dizini(tarama_id)
    (dizin / "sonuc.json").write_text(sonuc.model_dump_json(indent=2), encoding="utf-8")


def sonucu_oku(tarama_id: str) -> TaramaSonucu | None:
    dosya = TARAMALAR_DIZINI / tarama_id / "sonuc.json"
    if not dosya.exists():
        return None
    return TaramaSonucu.model_validate_json(dosya.read_text(encoding="utf-8"))


def parametreler_kaydet(tarama_id: str, parametreler: TaramaParametreleri) -> None:
    dizin = tarama_dizini(tarama_id)
    (dizin / "parametreler.json").write_text(parametreler.model_dump_json(indent=2), encoding="utf-8")


def parametreler_oku(tarama_id: str) -> TaramaParametreleri | None:
    dosya = TARAMALAR_DIZINI / tarama_id / "parametreler.json"
    if not dosya.exists():
        return None
    return TaramaParametreleri.model_validate_json(dosya.read_text(encoding="utf-8"))


def goruntuyu_kaydet(tarama_id: str, png_bayt: bytes) -> None:
    dizin = tarama_dizini(tarama_id)
    (dizin / "harita.png").write_bytes(png_bayt)


def goruntu_yolu(tarama_id: str) -> Path | None:
    dosya = TARAMALAR_DIZINI / tarama_id / "harita.png"
    return dosya if dosya.exists() else None


def tarama_var_mi(tarama_id: str) -> bool:
    return (TARAMALAR_DIZINI / tarama_id).exists()


def taramayi_sil(tarama_id: str) -> None:
    dizin = TARAMALAR_DIZINI / tarama_id
    if dizin.exists():
        shutil.rmtree(dizin)


def taramalari_listele() -> list[TaramaOzet]:
    TARAMALAR_DIZINI.mkdir(parents=True, exist_ok=True)
    ozetler: list[TaramaOzet] = []
    for dizin in TARAMALAR_DIZINI.iterdir():
        if not dizin.is_dir():
            continue
        tarama_id = dizin.name
        sonuc = sonucu_oku(tarama_id)
        durum_bilgisi = durumu_oku(tarama_id)
        if sonuc is not None:
            parametreler = parametreler_oku(tarama_id) or analiz.varsayilan_parametreler()
            kritik_uyari = analiz.kritik_uyari_belirle(sonuc, parametreler.gerekli_pas_payi_mm)
            ozetler.append(
                TaramaOzet(
                    tarama_id=tarama_id,
                    tarih=sonuc.tarih,
                    operator=sonuc.operator,
                    konum_etiketi=sonuc.konum_etiketi,
                    donati_sayisi=sonuc.donati_sayisi,
                    kritik_uyari_var_mi=kritik_uyari.seviye != "uygun",
                    durum=durum_bilgisi.durum if durum_bilgisi else TaramaDurum.TAMAMLANDI,
                )
            )
        elif durum_bilgisi is not None:
            ozetler.append(
                TaramaOzet(
                    tarama_id=tarama_id,
                    tarih=_id_den_tarih_tahmini(tarama_id),
                    operator="-",
                    konum_etiketi="-",
                    donati_sayisi=0,
                    kritik_uyari_var_mi=False,
                    durum=durum_bilgisi.durum,
                )
            )
    ozetler.sort(key=lambda o: o.tarih, reverse=True)
    return ozetler


def tamamlanan_tarama_sayisi() -> int:
    return sum(1 for o in taramalari_listele() if o.durum == TaramaDurum.TAMAMLANDI)


def eski_taramalari_buda(maks_sayi: int) -> list[str]:
    """En yeni `maks_sayi` tamamlanmış taramayı tutar, daha eskilerini siler.

    Devam eden (isleniyor/bekliyor) taramalara dokunmaz. Silinen id'leri döner.
    maks_sayi <= 0 ise hiçbir şey silmez (sınırsız = otomatik silme kapalı).
    """
    if maks_sayi <= 0:
        return []
    ozetler = taramalari_listele()  # tarihe göre yeniden eskiye sıralı
    tamamlananlar = [o for o in ozetler if o.durum == TaramaDurum.TAMAMLANDI]
    silinecekler = tamamlananlar[maks_sayi:]  # limitin üstünde kalan en eskiler
    silinen_idler: list[str] = []
    for ozet in silinecekler:
        taramayi_sil(ozet.tarama_id)
        silinen_idler.append(ozet.tarama_id)
    return silinen_idler


def _id_den_tarih_tahmini(tarama_id: str):
    from datetime import datetime, timezone

    try:
        return datetime.strptime(tarama_id, "%Y-%m-%dT%H-%M-%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
