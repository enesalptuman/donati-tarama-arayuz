# Donatı Tarama Cihazı — Operatör Arayüzü

Raspberry Pi CM5 üzerinde çalışan, betonarme donatı tarama cihazının
operatör arayüzü. Bu depo **sadece son halkayı** kapsar: rekonstrüksiyon
ve donatı tespit algoritmasının ürettiği sonucu operatöre/denetçiye
göstermek. Algoritma başka bir ekip tarafından geliştiriliyor; bu yüzden
arayüz şu an gerçekçi bir **mock veri kaynağı** üzerine kuruludur.

## Mimari

```
Algoritma (henüz yok) ──▶ DataSource arayüzü ──▶ TaramaService ──▶ FastAPI ──▶ Web arayüzü
                              │
                    ┌─────────┴─────────┐
              MockDataSource      SerialDataSource
              (şu an aktif)       (iskelet, ileride doldurulacak)
```

Arayüz ve API, hangi `DataSource` implementasyonunun kullanıldığını
bilmez — sadece `app/datasource/base.py`'deki soyut arayüzle konuşur.
Hangi kaynağın aktif olduğu `config.yaml`'daki tek satırla seçilir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma (geliştirme)

```bash
uvicorn app.main:app --reload
```

Tarayıcıda `http://localhost:8000` adresini açın.

## config.yaml

```yaml
veri_kaynagi: mock   # mock | serial
sinirda_pay_mm: 10.0
maks_tarama_sayisi: 0    # 0 = sınırsız (otomatik silme yok)
uyari_tarama_sayisi: 50  # kayıt bu sayıyı aşınca arayüzde uyarı (0 = kapalı)
seri_port: /dev/ttyACM0
seri_baud: 921600
```

**Disk yönetimi:** Bu bir denetim kayıt cihazı olduğu için varsayılan
davranış **otomatik silme yapmamaktır** (`maks_tarama_sayisi: 0`). Kayıt
sayısı `uyari_tarama_sayisi`'ni aşınca arayüzde "disk dolabilir" uyarısı
çıkar ve operatör istediğini elle silebilir. `maks_tarama_sayisi` > 0
yapılırsa, yeni tarama tamamlandığında en eski **tamamlanmış** taramalar
bu sayının üstünde kalanlar otomatik silinir (devam edenlere dokunulmaz).

**Gerekli minimum pas payı burada sabit DEĞİL.** TS 500/TBDY 2018'e göre
bu değer maruziyet sınıfına, yapı elemanı tipine ve projeye göre
değiştiği için her taramada **operatör/denetçi giriş formunda girer**
("Eleman Tipi" seçilince tipik bir değer önerilir, elle değiştirilebilir).
`config.yaml`'daki `sinirda_pay_mm`, girilen min. değere eklenen ve
turuncu "SINIRDA" bölgesini oluşturan sabit bir görsel erken-uyarı payıdır
— ayrı bir mühendislik değeri değildir.

- Girilen değerin altı → **YETERSİZ** (kırmızı)
- Girilen değer – (değer + `sinirda_pay_mm`) arası → **SINIRDA** (turuncu)
- Bunun üstü → **UYGUN** (yeşil)

Eleman tipine göre önerilen varsayımlar (`app/services/analiz.py` →
`ELEMAN_TIPI_VARSAYILAN_PAS_PAYI_MM`) ve bu mantık tek yerden kullanılır
(API yanıtı, kritik uyarı bandı ve PDF rapor aynı hesaplamayı paylaşır).

## Veri Şeması

Algoritmadan beklenen JSON şeması `app/models/tarama.py` içinde
Pydantic modelleri olarak tanımlıdır (`TaramaSonucu` ve alt modelleri).
Şema değişirse **tek bu dosya** güncellenir; storage, API ve mock
üreteç otomatik olarak yeni şemayı kullanır.

## Mock → Gerçek Veri Kaynağına Geçiş

1. `app/datasource/serial_source.py` içindeki `SerialDataSource` sınıfını
   doldurun:
   - `_baglan`: pyserial ile STM32H753'e bağlanma (`self._port`, `self._baud`
     zaten `config.yaml`'dan okunuyor).
   - `_veri_oku`: ham veri akışını okuma, `ilerleme_cb` ile yüzde bildirme.
   - `_isle`: algoritma çıktısını `TaramaSonucu` modeline dönüştürüp
     `TaramaCiktisi(sonuc=..., goruntu_png=...)` döndürme.
2. `config.yaml` içinde `veri_kaynagi: serial` yapın.
3. Başka hiçbir dosyayı (API, servis katmanı, frontend) değiştirmenize
   gerek yoktur — `TaramaService` ve arayüz aynı kalır.

Şema taslak/değişken olduğu için Pydantic doğrulaması bilinçli olarak
katı tutulmuştur: `_isle` içinde üretilen veri şemaya uymazsa hata
fırlatılır, sessizce hatalı veri kabul edilmez.

## API Uç Noktaları

| Metod | Yol | Açıklama |
|---|---|---|
| GET | `/api/eleman-tipleri` | Eleman tipi listesi + varsayılan pas payı (mm) |
| GET | `/api/depolama-durumu` | Kayıt sayısı + disk uyarısı bilgisi |
| POST | `/api/tarama/baslat` | `{operator, konum_etiketi, eleman_tipi, gerekli_pas_payi_mm}` → `{tarama_id}` (devam eden tarama varken 409) |
| GET | `/api/tarama/{id}/durum` | İlerleme yüzdesi + durum |
| GET | `/api/tarama/{id}` | Tam sonuç (zenginleştirilmiş) |
| GET | `/api/tarama/{id}/goruntu` | Yansıma haritası PNG |
| GET | `/api/taramalar` | Geçmiş taramalar listesi |
| GET | `/api/tarama/{id}/rapor.pdf` | PDF rapor |
| DELETE | `/api/tarama/{id}` | Tarama kaydını sil |
| POST | `/api/tarama/{id}/iptal` | Devam eden taramayı iptal et |

## Kalıcı Veri

Her tarama `taramalar/{tarama_id}/` altında saklanır:
`sonuc.json`, `harita.png`, `durum.json`, `parametreler.json` (eleman
tipi + operatörün girdiği gerekli pas payı). Pi yeniden başlasa bile
taramalar kaybolmaz; yarıda kesilen taramalar açılışta otomatik olarak
"hata" durumuna işaretlenir.

## Raspberry Pi Kurulumu (systemd + kiosk)

```bash
# Proje /home/pi/donati-tarama altına kopyalanmış ve venv kurulmuş varsayılır.
sudo cp deploy/donati-tarama.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now donati-tarama.service

chmod +x deploy/kiosk-baslat.sh
```

`kiosk-baslat.sh`'ı masaüstü ortamınızın autostart mekanizmasına ekleyin
(ör. `~/.config/autostart/donati-kiosk.desktop` veya Openbox/LabWC
autostart dosyası) ki cihaz açılışta otomatik olarak tam ekran arayüze
girsin.

## Test Etme

Tarayıcı geliştirici araçlarında (DevTools → Responsive Mode) şu
genişliklerde kontrol edin:

- **800×480 – 900px**: Görsel/Özet sekmeli görünüm, kritik uyarı bandı
  sekmelerin üstünde sabit.
- **1024×600 – 1280×800**: Görsel solda %55, özet sağda %45.
- **1920×1080+**: Yan yana, geniş boşluklar.

Farklı mock senaryolarını görmek için birden fazla tarama başlatın
(çift katman/tek katman, boşluklu, "donatı bulunamadı", düşük güven
skorlu tespitler rastgele üretilir).

## Proje Yapısı

```
app/
  main.py            FastAPI uygulaması, static mount
  config.py          config.yaml okuyucu
  models/tarama.py   Pydantic şema — tek doğrulama kaynağı
  datasource/        DataSource soyutlaması (base/mock/serial/factory)
  generators/        Mock veri ve görüntü üreteçleri
  services/          Orkestrasyon (tarama_service) + iş kuralları (analiz)
  report/            PDF rapor üreteci
  routers/           /api/tarama uç noktaları
  storage.py         Diske kalıcı kayıt
static/              Vanilla JS operatör arayüzü
deploy/              systemd + kiosk script
taramalar/           Kalıcı veri (çalışma zamanında oluşur)
```


# push edip otomatik tetiklenme kontrolü için bu cümleyi ekleyip readme'yi pushlayıp deneyeceğim. 