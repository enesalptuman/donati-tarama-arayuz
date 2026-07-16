"""Yansıma haritası PNG üreteci.

Gerçek X-ray/radar rekonstrüksiyonunu taklit eder: gri tonlarda beton
dokusu gürültüsü üzerine, donatı konumlarında parlak çizgi/nokta
işaretleri bindirir. Sadece görsel gerçekçilik amaçlıdır; gerçek
piksel değerleri arayüz tarafından yorumlanmaz (koordinatlar cm
cinsinden ayrı olarak JSON'da tutulur).
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter

from app.models.tarama import TaramaSonucu


def _beton_dokusu(genislik_px: int, yukseklik_px: int, rng: np.random.Generator) -> np.ndarray:
    taban = rng.normal(loc=90, scale=14, size=(yukseklik_px, genislik_px))
    kaba_gurultu = rng.normal(loc=0, scale=25, size=(yukseklik_px // 8 + 1, genislik_px // 8 + 1))
    kaba_img = Image.fromarray(kaba_gurultu.astype(np.float32), mode="F").resize(
        (genislik_px, yukseklik_px), Image.BILINEAR
    )
    doku = taban + np.asarray(kaba_img)
    return doku


def _cizgi_ciz(katman: np.ndarray, x0: float, y0: float, x1: float, y1: float, kalinlik: int, parlaklik: float) -> None:
    yukseklik_px, genislik_px = katman.shape
    uzunluk = max(int(np.hypot(x1 - x0, y1 - y0)), 1)
    for t in np.linspace(0, 1, uzunluk):
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        for dx in range(-kalinlik, kalinlik + 1):
            for dy in range(-kalinlik, kalinlik + 1):
                px, py = int(cx + dx), int(cy + dy)
                if 0 <= px < genislik_px and 0 <= py < yukseklik_px:
                    mesafe = np.hypot(dx, dy)
                    if mesafe <= kalinlik:
                        katman[py, px] = max(katman[py, px], parlaklik * (1 - mesafe / (kalinlik + 1)))


def yansima_haritasi_uret(sonuc: TaramaSonucu, tohum: int | None = None) -> bytes:
    """TaramaSonucu'na göre PNG bayt dizisi üretir."""
    rng = np.random.default_rng(tohum)
    mm_per_px = sonuc.goruntu.piksel_boyut_mm
    genislik_px = max(int(sonuc.tarama_alani.genislik_cm * 10 / mm_per_px), 32)
    yukseklik_px = max(int(sonuc.tarama_alani.yukseklik_cm * 10 / mm_per_px), 32)

    doku = _beton_dokusu(genislik_px, yukseklik_px, rng)
    parlaklik_katmani = np.zeros_like(doku)

    cm_to_px = 10.0 / mm_per_px

    for donati in sonuc.donatilar:
        merkez_x = donati.x_cm * cm_to_px
        merkez_y = donati.y_cm * cm_to_px
        kalinlik = max(int(donati.cap_mm / mm_per_px / 2), 2)
        parlaklik = 150 + min(donati.cap_mm, 26) * 3

        if donati.yon.value == "dusey":
            _cizgi_ciz(parlaklik_katmani, merkez_x, 0, merkez_x, yukseklik_px, kalinlik, parlaklik)
        else:
            _cizgi_ciz(parlaklik_katmani, 0, merkez_y, genislik_px, merkez_y, kalinlik, parlaklik)

    for bosluk in sonuc.bosluklar:
        merkez_x = int(bosluk.x_cm * cm_to_px)
        merkez_y = int(bosluk.y_cm * cm_to_px)
        yaricap = max(int(bosluk.boyut_mm / mm_per_px / 2), 3)
        for dx in range(-yaricap, yaricap + 1):
            for dy in range(-yaricap, yaricap + 1):
                px, py = merkez_x + dx, merkez_y + dy
                if 0 <= px < genislik_px and 0 <= py < yukseklik_px and dx * dx + dy * dy <= yaricap * yaricap:
                    doku[py, px] -= 35  # boşluk bölgesi daha koyu (zayıflatılmış yansıma)

    birlesik = np.clip(doku + parlaklik_katmani, 0, 255).astype(np.uint8)
    img = Image.fromarray(birlesik, mode="L").filter(ImageFilter.GaussianBlur(radius=0.6))

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
