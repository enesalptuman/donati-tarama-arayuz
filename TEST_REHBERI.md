# Test Rehberi — Adım Adım

Bu dosya, geliştirilen operatör arayüzünü kendi bilgisayarınızda nasıl
çalıştırıp test edeceğinizi anlatır. Genel mimari/API bilgisi için
[README.md](README.md)'ye bakın; burası sadece "şimdi ne yapayım" sorusuna
cevap verir.

## 1. Sunucuyu başlatın

Proje kök dizininde (bu dosyanın olduğu yerde):

```bash
# Sanal ortam daha önce kurulmadıysa:
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell/cmd
# veya: source .venv/Scripts/activate   (Git Bash)

pip install -r requirements.txt

# Sunucuyu başlatın:
uvicorn app.main:app --reload
```

Terminalde `Uvicorn running on http://127.0.0.1:8000` satırını görünce
tarayıcıda **http://localhost:8000** adresini açın.

## 2. Giriş ekranını test edin

- **Operatör Adı** ve **Konum Etiketi** alanlarına bir şeyler yazın (örn.
  "Ahmet Y." / "B Blok - Kolon K12").
- **Eleman Tipi** açılır menüsünden "Kolon" seçin → **Gerekli Min. Pas
  Payı (mm)** alanının otomatik `25` ile dolduğunu görün. "Temel" seçin →
  alanın `50` olarak güncellendiğini görün (her eleman tipinin kendi
  varsayımı var). Alanı elle `30` gibi başka bir değere değiştirin —
  bu değer korunmalı, seçim değişmediği sürece üzerine yazılmamalı.
- Operatör/konum alanlarından birini boş bırakıp **TARAMAYI BAŞLAT**'a
  basın → kırmızı uyarı metni çıkmalı. Pas payı alanını boşaltıp
  deneyin → "Lütfen geçerli bir gerekli min. pas payı (mm) girin."
  uyarısı çıkmalı.
- Formu doldurup butona basın, sayfayı yenileyin (F5), tekrar giriş
  ekranına gelin → operatör/konum/eleman tipi/mm değerlerinin
  hatırlandığını görün (localStorage).

## 3. Tarama / ilerleme ekranını izleyin

- Formu doldurup **TARAMAYI BAŞLAT**'a basınca ilerleme ekranına
  geçmeli: ilerleme çubuğu + yüzde her ~1 saniyede artmalı.
- Mock tarama **60–120 saniye** arası sürer (gerçek algoritma da benzer
  sürecek diye böyle tasarlandı) — sabırla bekleyin ya da:
- **TARAMAYI İPTAL ET**'e basıp taramayı yarıda kesin → onay
  penceresinden sonra giriş ekranına dönmeli, geçmiş listesinde
  görünmemeli (iptal edilen taramalar listelenmez).

Daha hızlı test etmek isterseniz, yeni bir terminalde (sunucu
kapanmadan) aşağıdaki komutla anlık bir tarama sonucu üretip diske
yazabilir, sonra tarayıcıyı yenileyip geçmiş listesinden açabilirsiniz:

```bash
.venv\Scripts\python -c "
import random
from app.generators.mock_generator import sahte_sonuc_uret
from app.generators.image_generator import yansima_haritasi_uret
from app.models.tarama import TaramaDurumBilgisi, TaramaDurum, TaramaParametreleri, ElemanTipi
from app import storage

tarama_id = 'hizli-test-1'
s = sahte_sonuc_uret(tarama_id, 'Test Op', 'Hizli Test Konumu').model_copy(update={'tarama_id': tarama_id})
storage.sonucu_kaydet(tarama_id, s)
storage.goruntuyu_kaydet(tarama_id, yansima_haritasi_uret(s))
storage.parametreler_kaydet(tarama_id, TaramaParametreleri(eleman_tipi=ElemanTipi.KOLON, gerekli_pas_payi_mm=25))
storage.durumu_kaydet(tarama_id, TaramaDurumBilgisi(tarama_id=tarama_id, durum=TaramaDurum.TAMAMLANDI, ilerleme=100))
print('Tarama hazır:', tarama_id, '- donati_var_mi:', s.donati_var_mi)
"
```

Sunucuyu yeniden başlatmanıza gerek yok; dosyayı diske yazmak yeterli.
Tarayıcıyı yenileyin, **Son Taramalar** listesinde "Hizli Test
Konumu" görünmeli, tıklayınca sonuç ekranı açılmalı.

## 4. Sonuç ekranını kontrol edin

Bir tarama tamamlandığında (veya yukarıdaki hızlı yöntemle ürettiğinizde):

- **Kritik uyarı bandı** en üstte, her zaman görünür olmalı, girdiğiniz
  mm değerine göre değişmeli:
  - Pas payı yetersizse kırmızı `⚠ PAS PAYI YETERSİZ — X mm (min. Y mm)`
    (Y = giriş formunda girdiğiniz değer, sabit değil)
  - Sınırdaysa turuncu, uygunsa yeşil `✓ DONATI DÜZENİ UYGUN`
  - Donatı bulunamadıysa kırmızı `DONATI TESPİT EDİLEMEDİ`
- **Görsel** sekmesinde: gri/beyaz beton dokulu bir görüntü, üzerinde
  donatı çizgileri/noktaları olmalı. Alttaki lejanttaki `Uygun (>Y mm)` /
  `Sınırda (X–Y mm)` / `Yetersiz (<X mm)` sayılarının, girdiğiniz mm
  değerine ve `config.yaml`'daki `sinirda_pay_mm` payına göre değiştiğini
  kontrol edin (sabit 25/35 değil). Bir işarete tıklayınca detay kutusu
  (çap, pas payı, katman, yön, güven) açılmalı; "Kapat" ile kapanmalı.
  Sol altta `X cm` yazan bir ölçek çizgisi olmalı.
- **Özet** sekmesinde: durum kartının altında `Kullanılan eşik: Kolon —
  gerekli min. pas payı 25 mm (operatör/denetçi girdisi)` gibi bir satır
  olmalı — hangi eşiğin kullanıldığı açıkça görünmeli. Ardından donatı
  tablosu (No/Çap/Pas Payı/Katman/Yön/Durum — renkli + ikonlu etiketler:
  ✓ UYGUN / ⚠ SINIRDA / ✕ YETERSİZ).
- Eğer tarama boşluk (segregasyon) içeriyorsa turuncu bir uyarı bölümü
  çıkmalı — her taramada olmayabilir, birkaç tarama deneyin.
- **PDF RAPOR İNDİR** butonuna basın → bir PDF inmeli, içinde tarih,
  konum, operatör, **Eleman Tipi** ve **Gerekli Min. Pas Payı** satırları,
  harita görseli, donatı tablosu ve imza alanı olmalı.
- **YENİ TARAMA** ile giriş ekranına dönün.

## 5. Geçmiş taramalar listesini test edin

- Birkaç tarama tamamladıktan sonra giriş ekranındaki **Son Taramalar**
  listesinde hepsi görünmeli (en yeni üstte), her satırda tarih/operatör/
  donatı sayısı ve UYGUN/UYARI etiketi olmalı.
- Bir satıra tıklayınca doğrudan o taramanın sonuç ekranı açılmalı
  (yeniden tarama yapmadan).

## 6. Ekran boyutu testleri (responsive)

Tarayıcıda **F12** (Geliştirici Araçları) → cihaz araç çubuğu simgesi
(Ctrl+Shift+M) ile "Responsive" moda geçin ve şu genişlikleri deneyin:

| Genişlik | Beklenen davranış |
|---|---|
| 800×480 | Sonuç ekranında GÖRSEL/ÖZET sekmeleri görünür, panel'ler alt alta değil sekmeli; kritik uyarı bandı en üstte sabit kalır (scroll etseniz de) |
| 1280×800 | Sekmeler kaybolur, Görsel solda (%55) Özet sağda (%45) yan yana |
| 1920×1080 | Aynı yan yana düzen, daha geniş boşluklar, tablo yazı boyutu biraz büyür |

Ayrıca dokunmatik hedeflerin (butonlar, sekmeler) küçük ekranda bile
rahat tıklanabilir büyüklükte olduğunu gözle kontrol edin.

## 7. API'yi doğrudan test etmek isterseniz

Tarayıcı yerine `curl` ile de deneyebilirsiniz (Türkçe karakter içeren
gövdeler için `-d` yerine bir dosyadan okutmak daha güvenli):

```bash
curl http://127.0.0.1:8000/api/eleman-tipleri
# -> [{"deger":"kolon","etiket":"Kolon","varsayilan_mm":25.0}, ...]

curl -X POST http://127.0.0.1:8000/api/tarama/baslat \
  -H "Content-Type: application/json" \
  -d "{\"operator\":\"Test\",\"konum_etiketi\":\"K1\",\"eleman_tipi\":\"kolon\",\"gerekli_pas_payi_mm\":25}"
# -> {"tarama_id": "..."}

curl http://127.0.0.1:8000/api/tarama/<tarama_id>/durum
curl http://127.0.0.1:8000/api/tarama/<tarama_id>          # tamamlandıktan sonra
curl http://127.0.0.1:8000/api/taramalar
```

Otomatik oluşan Swagger arayüzünü de kullanabilirsiniz:
**http://localhost:8000/docs**

## 8. Temizlik

Test verilerini silmek isterseniz `taramalar/` klasörü altındaki
tarama id'si ile adlandırılmış klasörleri silmeniz yeterli (uygulama
kapalıyken de yapabilirsiniz, veri kaybı riski yok çünkü zaten test
verisi). Sunucuyu durdurmak için terminalde `Ctrl+C`.

## Sık karşılaşabileceğiniz durumlar

- **"Henüz kayıtlı tarama yok" hep görünüyor**: Sadece `tamamlandi`
  durumundaki taramalar listelenir; işleniyor/iptal edilmiş/hatalı
  taramalar geçmiş listesinde çıkmaz (bilinçli tasarım).
- **Türkçe karakterler terminalde bozuk görünüyor ama tarayıcıda
  düzgün**: Bu Windows terminalinin (cp1254/cp1252) kod sayfası
  sınırlaması, veri bozuk değil — tarayıcı ve gerçek kullanım için
  önemli olan budur.
- **Sunucu yeniden başladı, eski tarama "hata" görünüyor**: Beklenen
  davranış — yarıda kesilen taramalar açılışta otomatik "hata" olarak
  işaretlenir (Pi'nin beklenmedik kapanmasını simüle eder).
