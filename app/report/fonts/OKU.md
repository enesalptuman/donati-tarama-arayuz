# PDF Türkçe Font Klasörü

PDF raporundaki Türkçe karakterlerin (ş, ğ, İ, ı) doğru basılması için
bu klasöre isteğe bağlı olarak bir TrueType font konabilir.

`pdf_rapor.py` fontu şu sırayla arar:

1. **Bu klasör** — `DejaVuSans.ttf` (+ isteğe bağlı `DejaVuSans-Bold.ttf`)
2. Raspberry Pi/Linux sistem fontu — `/usr/share/fonts/truetype/dejavu/…`
3. Windows — `arial.ttf`
4. Hiçbiri yoksa reportlab Helvetica (Türkçe karakterler bozuk çıkar)

## Ne zaman buraya font koymalıyım?

- Raspberry Pi OS **Lite** (masaüstüsüz) imajı kullanıyorsanız DejaVu
  kurulu olmayabilir. İki seçenek:
  - `sudo apt install fonts-dejavu` (önerilen), **veya**
  - `DejaVuSans.ttf` ve `DejaVuSans-Bold.ttf` dosyalarını bu klasöre kopyalayın.

DejaVu fontları özgürce dağıtılabilir (Bitstream Vera / DejaVu lisansı).
Genellikle Linux'ta `/usr/share/fonts/truetype/dejavu/` altında bulunur.
