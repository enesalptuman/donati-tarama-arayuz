// Ana durum makinesi: giriş / ilerleme / sonuç ekranları arası geçiş.

(() => {
  const LS_OPERATOR = "donati_tarama_operator";
  const LS_KONUM = "donati_tarama_konum";
  const LS_ELEMAN_TIPI = "donati_tarama_eleman_tipi";
  const LS_PAS_PAYI = "donati_tarama_pas_payi_mm";

  const ekranlar = {
    giris: document.getElementById("ekran-giris"),
    ilerleme: document.getElementById("ekran-ilerleme"),
    sonuc: document.getElementById("ekran-sonuc"),
  };

  const operatorInput = document.getElementById("operator-input");
  const konumInput = document.getElementById("konum-input");
  const elemanTipiSelect = document.getElementById("eleman-tipi-select");
  const pasPayiInput = document.getElementById("pas-payi-input");
  const baslatButonu = document.getElementById("baslat-butonu");
  const girisHata = document.getElementById("giris-hata");
  const gecmisListesi = document.getElementById("gecmis-listesi");
  const gecmisBosMesaj = document.getElementById("gecmis-bos-mesaj");
  const depolamaUyari = document.getElementById("depolama-uyari");

  let elemanTipleri = [];

  const ilerlemeCubugu = document.getElementById("ilerleme-cubugu-ic");
  const ilerlemeYuzde = document.getElementById("ilerleme-yuzde");
  const iptalButonu = document.getElementById("iptal-butonu");

  const kritikUyariBandi = document.getElementById("kritik-uyari-bandi");
  const kritikUyariMetni = document.getElementById("kritik-uyari-metni");
  const pdfIndirButonu = document.getElementById("pdf-indir-butonu");
  const yeniTaramaButonu = document.getElementById("yeni-tarama-butonu");
  const silButonu = document.getElementById("sil-butonu");

  let aktifTaramaId = null;
  let pollingZamanlayici = null;

  function ekranGoster(ad) {
    for (const [k, el] of Object.entries(ekranlar)) {
      el.classList.toggle("aktif", k === ad);
    }
  }

  function tarihFormatla(isoTarih) {
    const t = new Date(isoTarih);
    return t.toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  async function depolamaUyarisiniGuncelle() {
    try {
      const durum = await Api.depolamaDurumu();
      if (durum.uyari_var_mi) {
        const limitMetni = durum.maks_tarama_sayisi > 0
          ? ` En eski taramalar ${durum.maks_tarama_sayisi} adet sınırında otomatik siliniyor.`
          : " Yer açmak için eski taramaları silebilirsiniz.";
        depolamaUyari.textContent =
          `⚠ ${durum.tarama_sayisi} kayıtlı tarama var (uyarı eşiği: ${durum.uyari_esigi}).${limitMetni}`;
        depolamaUyari.hidden = false;
      } else {
        depolamaUyari.hidden = true;
      }
    } catch (e) {
      console.error(e);
      depolamaUyari.hidden = true;
    }
  }

  async function gecmisiYukle() {
    depolamaUyarisiniGuncelle();
    try {
      const liste = await Api.taramalariListele();
      gecmisListesi.innerHTML = "";
      const tamamlananlar = liste.filter((t) => t.durum === "tamamlandi");
      if (tamamlananlar.length === 0) {
        gecmisBosMesaj.hidden = false;
        return;
      }
      gecmisBosMesaj.hidden = true;
      for (const tarama of tamamlananlar) {
        const li = document.createElement("li");
        li.className = "gecmis-ogesi";
        const etiketSinif = tarama.kritik_uyari_var_mi ? "yetersiz" : "uygun";
        const etiketMetin = tarama.kritik_uyari_var_mi ? "UYARI" : "UYGUN";
        li.innerHTML = `
          <span>
            <span class="gecmis-konum">${tarama.konum_etiketi}</span><br>
            <span class="gecmis-tarih">${tarihFormatla(tarama.tarih)} · ${tarama.operator} · ${tarama.donati_sayisi} donatı</span>
          </span>
          <span class="gecmis-etiket ${etiketSinif}">${etiketMetin}</span>
        `;
        li.addEventListener("click", () => sonucuGosterVe(tarama.tarama_id));

        const silBtn = document.createElement("button");
        silBtn.className = "gecmis-sil-buton";
        silBtn.title = "Bu taramayı sil";
        silBtn.setAttribute("aria-label", "Bu taramayı sil");
        silBtn.textContent = "🗑";
        silBtn.addEventListener("click", (evt) => {
          evt.stopPropagation(); // satıra tıklayıp sonucu açmayı engelle
          taramayiSil(tarama.tarama_id, `${tarama.konum_etiketi} (${tarihFormatla(tarama.tarih)})`);
        });
        li.appendChild(silBtn);

        gecmisListesi.appendChild(li);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function elemanTipleriniYukle() {
    try {
      elemanTipleri = await Api.elemanTipleriListele();
      elemanTipiSelect.innerHTML = "";
      for (const tip of elemanTipleri) {
        const secenek = document.createElement("option");
        secenek.value = tip.deger;
        secenek.textContent = tip.etiket;
        elemanTipiSelect.appendChild(secenek);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function varsayilanMmGetir(elemanTipiDegeri) {
    const bulunan = elemanTipleri.find((t) => t.deger === elemanTipiDegeri);
    return bulunan ? bulunan.varsayilan_mm : null;
  }

  // Tek yerden silme: onay ister, siler, hata olursa uyarır.
  // Silme başarılıysa true döner (çağıran ekran güncellemesini yapar).
  async function taramayiSil(taramaId, etiket) {
    if (!confirm(`"${etiket}" taramasını kalıcı olarak silmek istiyor musunuz? Bu işlem geri alınamaz.`)) {
      return false;
    }
    try {
      await Api.sil(taramaId);
      await gecmisiYukle();
      return true;
    } catch (e) {
      alert(e.message || "Tarama silinemedi.");
      return false;
    }
  }

  function girisDegerleriniYukle() {
    operatorInput.value = localStorage.getItem(LS_OPERATOR) || "";
    konumInput.value = localStorage.getItem(LS_KONUM) || "";

    const kayitliElemanTipi = localStorage.getItem(LS_ELEMAN_TIPI);
    if (kayitliElemanTipi && elemanTipleri.some((t) => t.deger === kayitliElemanTipi)) {
      elemanTipiSelect.value = kayitliElemanTipi;
    }

    const kayitliPasPayi = localStorage.getItem(LS_PAS_PAYI);
    pasPayiInput.value = kayitliPasPayi || varsayilanMmGetir(elemanTipiSelect.value) || "";
  }

  async function taramaBaslat() {
    const operator = operatorInput.value.trim();
    const konum = konumInput.value.trim();
    const elemanTipi = elemanTipiSelect.value;
    const gerekliPasPayiMm = parseFloat(pasPayiInput.value);

    if (!operator || !konum) {
      girisHata.textContent = "Lütfen operatör adı ve konum etiketini girin.";
      girisHata.hidden = false;
      return;
    }
    if (!gerekliPasPayiMm || gerekliPasPayiMm <= 0) {
      girisHata.textContent = "Lütfen geçerli bir gerekli min. pas payı (mm) girin.";
      girisHata.hidden = false;
      return;
    }
    girisHata.hidden = true;
    localStorage.setItem(LS_OPERATOR, operator);
    localStorage.setItem(LS_KONUM, konum);
    localStorage.setItem(LS_ELEMAN_TIPI, elemanTipi);
    localStorage.setItem(LS_PAS_PAYI, String(gerekliPasPayiMm));

    try {
      const yanit = await Api.taramaBaslat(operator, konum, elemanTipi, gerekliPasPayiMm);
      aktifTaramaId = yanit.tarama_id;
      ekranGoster("ilerleme");
      ilerlemeCubugu.style.width = "0%";
      ilerlemeYuzde.textContent = "%0";
      pollingBaslat();
    } catch (e) {
      // Sunucu mesajı (örn. "Zaten devam eden bir tarama var") varsa onu göster.
      girisHata.textContent = e.message || "Tarama başlatılamadı, tekrar deneyin.";
      girisHata.hidden = false;
    }
  }

  function pollingBaslat() {
    pollingDurdur();
    pollingZamanlayici = setInterval(async () => {
      if (!aktifTaramaId) return;
      try {
        const durum = await Api.durumAl(aktifTaramaId);
        ilerlemeCubugu.style.width = `${durum.ilerleme}%`;
        ilerlemeYuzde.textContent = `%${durum.ilerleme}`;

        if (durum.durum === "tamamlandi") {
          pollingDurdur();
          await sonucuGosterVe(aktifTaramaId);
        } else if (durum.durum === "hata") {
          pollingDurdur();
          alert(`Tarama sırasında hata oluştu: ${durum.hata_mesaji || "bilinmeyen hata"}`);
          ekranGoster("giris");
          await gecmisiYukle();
        } else if (durum.durum === "iptal_edildi") {
          pollingDurdur();
          ekranGoster("giris");
          await gecmisiYukle();
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  }

  function pollingDurdur() {
    if (pollingZamanlayici) {
      clearInterval(pollingZamanlayici);
      pollingZamanlayici = null;
    }
  }

  async function sonucuGosterVe(taramaId) {
    try {
      const sonuc = await Api.sonucAl(taramaId);
      aktifTaramaId = taramaId;

      kritikUyariBandi.className = `kritik-uyari-bandi ${sonuc.kritik_uyari.seviye}`;
      const onEk = { uygun: "✓", sinirda: "⚠", yetersiz: "⚠" }[sonuc.kritik_uyari.seviye] || "";
      kritikUyariMetni.textContent = `${onEk} ${sonuc.kritik_uyari.mesaj}`;

      document.querySelectorAll(".lejant-sinir-alt").forEach((el) => {
        el.textContent = sonuc.parametreler.gerekli_pas_payi_mm.toFixed(0);
      });
      document.querySelectorAll(".lejant-sinir-ust").forEach((el) => {
        el.textContent = sonuc.sinirda_pas_payi_mm.toFixed(0);
      });

      OzetPanel.renderla(sonuc);
      GorselPanel.ciz(sonuc, Api.goruntuUrl(taramaId));
      pdfIndirButonu.href = Api.raporUrl(taramaId);

      ekranGoster("sonuc");
    } catch (e) {
      console.error(e);
      alert("Sonuç yüklenemedi.");
    }
  }

  function sekmeleriKur() {
    document.querySelectorAll(".sekme").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".sekme").forEach((b) => b.classList.remove("aktif"));
        document.querySelectorAll(".panel").forEach((p) => p.classList.remove("aktif"));
        btn.classList.add("aktif");
        document.getElementById(`panel-${btn.dataset.panel}`).classList.add("aktif");
      });
    });
  }

  elemanTipiSelect.addEventListener("change", () => {
    const varsayilan = varsayilanMmGetir(elemanTipiSelect.value);
    if (varsayilan) pasPayiInput.value = varsayilan;
  });

  baslatButonu.addEventListener("click", taramaBaslat);

  iptalButonu.addEventListener("click", async () => {
    if (!aktifTaramaId) return;
    if (!confirm("Devam eden taramayı iptal etmek istiyor musunuz?")) return;
    pollingDurdur();
    try {
      await Api.iptalEt(aktifTaramaId);
    } catch (e) {
      console.error(e);
    }
    ekranGoster("giris");
    await gecmisiYukle();
  });

  yeniTaramaButonu.addEventListener("click", () => {
    aktifTaramaId = null;
    ekranGoster("giris");
    gecmisiYukle();
  });

  silButonu.addEventListener("click", async () => {
    if (!aktifTaramaId) return;
    const silindi = await taramayiSil(aktifTaramaId, "bu tarama");
    if (silindi) {
      aktifTaramaId = null;
      ekranGoster("giris");
      await gecmisiYukle();
    }
  });

  sekmeleriKur();
  elemanTipleriniYukle().then(girisDegerleriniYukle);
  gecmisiYukle();
  ekranGoster("giris");
})();
