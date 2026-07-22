"""Tarama API entegrasyon testleri (FastAPI TestClient).

Arka plan taraması çalıştırmaz; doğrulama, hata kodları ve okuma yollarını
deterministik biçimde test eder. Tam tarama akışı test_akis.py'dedir.
"""

from __future__ import annotations


def test_eleman_tipleri_listesi(client):
    yanit = client.get("/api/eleman-tipleri")
    assert yanit.status_code == 200
    veri = yanit.json()
    assert len(veri) == 6
    # kolon varsayılanı 25 mm
    kolon = next(x for x in veri if x["deger"] == "kolon")
    assert kolon["varsayilan_mm"] == 25.0


def test_taramalar_bos_liste(client):
    # izole_ortam fixture'ı storage'ı boş tmp dizine yönlendirdi
    yanit = client.get("/api/taramalar")
    assert yanit.status_code == 200
    assert yanit.json() == []


def test_depolama_durumu_bos(client):
    yanit = client.get("/api/depolama-durumu")
    assert yanit.status_code == 200
    assert yanit.json()["tarama_sayisi"] == 0


def test_olmayan_tarama_durum_404(client):
    assert client.get("/api/tarama/yok-boyle-id/durum").status_code == 404


def test_olmayan_tarama_sonuc_404(client):
    assert client.get("/api/tarama/yok-boyle-id").status_code == 404


def test_baslat_eksik_alan_422(client):
    # eleman_tipi ve gerekli_pas_payi_mm eksik → Pydantic doğrulama hatası
    yanit = client.post("/api/tarama/baslat", json={"operator": "Ali", "konum_etiketi": "K1"})
    assert yanit.status_code == 422


def test_baslat_gecersiz_pas_payi_422(client):
    # gerekli_pas_payi_mm = 0, ama model Field(gt=0) → doğrulama hatası
    yanit = client.post(
        "/api/tarama/baslat",
        json={"operator": "Ali", "konum_etiketi": "K1", "eleman_tipi": "kolon", "gerekli_pas_payi_mm": 0},
    )
    assert yanit.status_code == 422


def test_tamamlanmis_taramayi_oku_ve_sil(client, ornek_tarama_kaydi):
    tid = ornek_tarama_kaydi

    # 1) Tam sonuç — zenginleştirilmiş (kritik_uyari + parametreler dolu)
    sonuc = client.get(f"/api/tarama/{tid}")
    assert sonuc.status_code == 200
    govde = sonuc.json()
    assert govde["tarama_id"] == tid
    assert "kritik_uyari" in govde
    assert govde["parametreler"]["eleman_tipi"] == "kolon"

    # 2) Görüntü — PNG dönüyor
    goruntu = client.get(f"/api/tarama/{tid}/goruntu")
    assert goruntu.status_code == 200
    assert goruntu.headers["content-type"] == "image/png"

    # 3) Liste — az önce yazdığımız kayıt görünüyor
    liste = client.get("/api/taramalar").json()
    assert any(x["tarama_id"] == tid for x in liste)

    # 4) Sil — 204, ardından okuma 404
    assert client.delete(f"/api/tarama/{tid}").status_code == 204
    assert client.get(f"/api/tarama/{tid}").status_code == 404


def test_rapor_pdf_uretilir(client, ornek_tarama_kaydi):
    # PDF rapor endpoint'i: geçerli bir PDF (baytları %PDF ile başlar) dönmeli.
    # Bu test aynı zamanda reportlab + Türkçe font çözücüsünü de çalıştırır.
    yanit = client.get(f"/api/tarama/{ornek_tarama_kaydi}/rapor.pdf")
    assert yanit.status_code == 200
    assert yanit.headers["content-type"] == "application/pdf"
    assert yanit.content[:4] == b"%PDF"
