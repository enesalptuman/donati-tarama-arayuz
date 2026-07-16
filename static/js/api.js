// Backend ile iletişim için ince fetch sarmalayıcı.
// Arayüzün geri kalanı bu fonksiyonlar dışında fetch() çağırmaz.

// Sunucunun döndürdüğü hata mesajını (FastAPI `detail`) çıkarır, yoksa
// verilen varsayılana düşer.
async function _hataMesajiOku(yanit, varsayilan) {
  try {
    const govde = await yanit.json();
    if (govde && govde.detail) return govde.detail;
  } catch (e) {
    /* JSON değilse varsayılana düş */
  }
  return varsayilan;
}

const Api = {
  async elemanTipleriListele() {
    const yanit = await fetch("/api/eleman-tipleri");
    if (!yanit.ok) throw new Error("Eleman tipleri alınamadı");
    return yanit.json();
  },

  async taramaBaslat(operator, konumEtiketi, elemanTipi, gerekliPasPayiMm) {
    const yanit = await fetch("/api/tarama/baslat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator,
        konum_etiketi: konumEtiketi,
        eleman_tipi: elemanTipi,
        gerekli_pas_payi_mm: gerekliPasPayiMm,
      }),
    });
    if (!yanit.ok) throw new Error(await _hataMesajiOku(yanit, "Tarama başlatılamadı"));
    return yanit.json();
  },

  async durumAl(taramaId) {
    const yanit = await fetch(`/api/tarama/${taramaId}/durum`);
    if (!yanit.ok) throw new Error("Durum alınamadı");
    return yanit.json();
  },

  async sonucAl(taramaId) {
    const yanit = await fetch(`/api/tarama/${taramaId}`);
    if (!yanit.ok) throw new Error("Sonuç alınamadı");
    return yanit.json();
  },

  goruntuUrl(taramaId) {
    return `/api/tarama/${taramaId}/goruntu`;
  },

  raporUrl(taramaId) {
    return `/api/tarama/${taramaId}/rapor.pdf`;
  },

  async taramalariListele() {
    const yanit = await fetch("/api/taramalar");
    if (!yanit.ok) throw new Error("Geçmiş taramalar alınamadı");
    return yanit.json();
  },

  async depolamaDurumu() {
    const yanit = await fetch("/api/depolama-durumu");
    if (!yanit.ok) throw new Error("Depolama durumu alınamadı");
    return yanit.json();
  },

  async iptalEt(taramaId) {
    const yanit = await fetch(`/api/tarama/${taramaId}/iptal`, { method: "POST" });
    if (!yanit.ok) throw new Error("İptal edilemedi");
  },

  async sil(taramaId) {
    const yanit = await fetch(`/api/tarama/${taramaId}`, { method: "DELETE" });
    if (!yanit.ok) throw new Error(await _hataMesajiOku(yanit, "Silinemedi"));
  },
};
