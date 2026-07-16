"""Yapı denetim raporuna eklenebilecek ciddiyette PDF rapor üreteci."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app import storage
from app.models.tarama import PasPayiDurumu, TaramaSonucuZenginlestirilmis
from app.services.analiz import ELEMAN_TIPI_ETIKETI

logger = logging.getLogger("pdf_rapor")

# --- Türkçe font desteği ---------------------------------------------------
# reportlab'ın yerleşik Helvetica'sı Türkçe'ye özgü ş, ğ, İ, ı karakterlerini
# basamaz (■ kutu olarak çıkar). Bu yüzden sistemde bulunan bir TrueType fontu
# kaydediyoruz. Aday sıralaması: önce projeye gömülmüş font (app/report/fonts/),
# sonra Raspberry Pi/Linux'ta standart DejaVu/Liberation, en son Windows Arial.
# Hiçbiri bulunamazsa Helvetica'ya düşülür (log'a uyarı yazılır).
_GOMULU_FONT_DIZINI = Path(__file__).resolve().parent / "fonts"
_FONT_ADAYLARI: list[tuple[Path, Path]] = [
    (_GOMULU_FONT_DIZINI / "DejaVuSans.ttf", _GOMULU_FONT_DIZINI / "DejaVuSans-Bold.ttf"),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ),
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
]

FONT_NORMAL = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _turkce_fontu_ayarla() -> None:
    """Sistemde bulunan ilk Türkçe-destekli TTF fontu 'TR'/'TR-Bold' olarak kaydeder."""
    global FONT_NORMAL, FONT_BOLD
    for normal_yol, bold_yol in _FONT_ADAYLARI:
        if not normal_yol.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("TR", str(normal_yol)))
            bold_kaynak = bold_yol if bold_yol.exists() else normal_yol
            pdfmetrics.registerFont(TTFont("TR-Bold", str(bold_kaynak)))
            pdfmetrics.registerFontFamily("TR", normal="TR", bold="TR-Bold", italic="TR", boldItalic="TR-Bold")
            FONT_NORMAL = "TR"
            FONT_BOLD = "TR-Bold"
            logger.info("PDF Türkçe fontu kullanılıyor: %s", normal_yol)
            return
        except Exception:
            logger.exception("Font kaydı başarısız (%s), sonraki aday deneniyor.", normal_yol)
    logger.warning(
        "Türkçe destekli TTF font bulunamadı — PDF Helvetica'ya düşecek ve ş/ğ/İ/ı bozuk çıkabilir. "
        "Pi'de 'sudo apt install fonts-dejavu' ile kurun veya app/report/fonts/ içine DejaVuSans.ttf koyun."
    )


_turkce_fontu_ayarla()

_DURUM_RENK = {
    PasPayiDurumu.UYGUN: colors.HexColor("#1e7d34"),
    PasPayiDurumu.SINIRDA: colors.HexColor("#b56a00"),
    PasPayiDurumu.YETERSIZ: colors.HexColor("#b3261e"),
}

_DURUM_METNI = {
    PasPayiDurumu.UYGUN: "UYGUN",
    PasPayiDurumu.SINIRDA: "SINIRDA",
    PasPayiDurumu.YETERSIZ: "YETERSİZ",
}


def rapor_uret(sonuc: TaramaSonucuZenginlestirilmis) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )

    stiller = getSampleStyleSheet()
    baslik_stili = ParagraphStyle(
        "Baslik", parent=stiller["Title"], fontName=FONT_BOLD, fontSize=18, spaceAfter=4
    )
    alt_baslik_stili = ParagraphStyle(
        "AltBaslik", parent=stiller["Normal"], fontName=FONT_NORMAL, fontSize=11, textColor=colors.grey
    )
    bolum_stili = ParagraphStyle(
        "Bolum", parent=stiller["Heading2"], fontName=FONT_BOLD, fontSize=13, spaceBefore=12, spaceAfter=6
    )
    normal_stil = ParagraphStyle("NormalTR", parent=stiller["Normal"], fontName=FONT_NORMAL)

    icerik = []

    icerik.append(Paragraph("Betonarme Donatı Tarama Raporu", baslik_stili))
    icerik.append(
        Paragraph(
            f"Tarama No: {sonuc.tarama_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Tarih: {sonuc.tarih.strftime('%d.%m.%Y %H:%M')}",
            alt_baslik_stili,
        )
    )
    icerik.append(Spacer(1, 0.4 * cm))

    bilgi_tablosu = Table(
        [
            ["Konum", sonuc.konum_etiketi],
            ["Operatör", sonuc.operator],
            ["Tarama Alanı", f"{sonuc.tarama_alani.genislik_cm:.0f} x {sonuc.tarama_alani.yukseklik_cm:.0f} cm"],
            ["Katman Sayısı", str(sonuc.katman_sayisi)],
            ["Eleman Tipi", ELEMAN_TIPI_ETIKETI[sonuc.parametreler.eleman_tipi]],
            ["Gerekli Min. Pas Payı", f"{sonuc.parametreler.gerekli_pas_payi_mm:.0f} mm (operatör/denetçi girdisi)"],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    bilgi_tablosu.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NORMAL),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    icerik.append(bilgi_tablosu)
    icerik.append(Spacer(1, 0.5 * cm))

    # Kritik uyarı bandı
    uyari_renk = _DURUM_RENK[sonuc.kritik_uyari.seviye]
    uyari_tablosu = Table([[sonuc.kritik_uyari.mesaj]], colWidths=[16 * cm])
    uyari_tablosu.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), uyari_renk),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 13),
                ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    icerik.append(uyari_tablosu)
    icerik.append(Spacer(1, 0.6 * cm))

    # Yansıma haritası
    goruntu_yolu = storage.goruntu_yolu(sonuc.tarama_id)
    if goruntu_yolu is not None:
        icerik.append(Paragraph("Yansıma Haritası", bolum_stili))
        icerik.append(Image(str(goruntu_yolu), width=10 * cm, height=10 * cm, kind="proportional"))
        icerik.append(Spacer(1, 0.4 * cm))

    # Donatı tablosu
    icerik.append(Paragraph("Tespit Edilen Donatılar", bolum_stili))
    if sonuc.donatilar:
        satirlar = [["No", "Çap (mm)", "Pas Payı (mm)", "Katman", "Yön", "Durum"]]
        for d in sonuc.donatilar:
            satirlar.append(
                [
                    str(d.id),
                    str(d.cap_mm),
                    f"{d.pas_payi_mm:.0f}",
                    str(d.katman),
                    "Düşey" if d.yon.value == "dusey" else "Yatay",
                    _DURUM_METNI[d.durum] if d.durum else "-",
                ]
            )
        donati_tablosu = Table(satirlar, colWidths=[1.6 * cm, 2.6 * cm, 3.2 * cm, 2.4 * cm, 2.6 * cm, 3.2 * cm])
        stil_komutlari = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e5e5")),
            ("FONTNAME", (0, 0), (-1, -1), FONT_NORMAL),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for i, d in enumerate(sonuc.donatilar, start=1):
            if d.durum:
                stil_komutlari.append(("TEXTCOLOR", (5, i), (5, i), _DURUM_RENK[d.durum]))
                stil_komutlari.append(("FONTNAME", (5, i), (5, i), FONT_BOLD))
        donati_tablosu.setStyle(TableStyle(stil_komutlari))
        icerik.append(donati_tablosu)
        icerik.append(
            Paragraph(
                f"Ortalama pas payı: {sonuc.ortalama_pas_payi_mm:.0f} mm &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Minimum pas payı: {sonuc.min_pas_payi_mm:.0f} mm",
                ParagraphStyle("Ozet", parent=normal_stil, spaceBefore=6),
            )
        )
    else:
        icerik.append(Paragraph("Taranan bölgede donatı tespit edilemedi.", normal_stil))

    # Boşluklar
    if sonuc.bosluklar:
        icerik.append(Paragraph("Tespit Edilen Boşluklar (Segregasyon)", bolum_stili))
        bosluk_satirlari = [["No", "Boyut (mm)", "Derinlik (mm)", "Güven"]]
        for b in sonuc.bosluklar:
            bosluk_satirlari.append([str(b.id), f"{b.boyut_mm:.0f}", f"{b.derinlik_mm:.0f}", f"%{b.guven * 100:.0f}"])
        bosluk_tablosu = Table(bosluk_satirlari, colWidths=[2 * cm, 3 * cm, 3 * cm, 3 * cm])
        bosluk_tablosu.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5d6a8")),
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NORMAL),
                    ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        )
        icerik.append(bosluk_tablosu)

    # İmza alanı
    icerik.append(Spacer(1, 1.5 * cm))
    imza_tablosu = Table(
        [["Operatör İmza", "Denetçi İmza"], ["", ""]],
        colWidths=[8 * cm, 8 * cm],
        rowHeights=[0.6 * cm, 2 * cm],
    )
    imza_tablosu.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NORMAL),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
                ("LINEABOVE", (0, 1), (0, 1), 0.6, colors.grey),
                ("LINEABOVE", (1, 1), (1, 1), 0.6, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ]
        )
    )
    icerik.append(imza_tablosu)

    doc.build(icerik)
    return buf.getvalue()
