// Özet panel: durum kartı, donatı tablosu, boşluk uyarısı — usta için sade özet.

const OzetPanel = (() => {
  const DURUM_ETIKET = {
    uygun: { metin: "✓ UYGUN", sinif: "uygun" },
    sinirda: { metin: "⚠ SINIRDA", sinif: "sinirda" },
    yetersiz: { metin: "✕ YETERSİZ", sinif: "yetersiz" },
  };

  const ELEMAN_TIPI_ETIKET = {
    kolon: "Kolon",
    kiris: "Kiriş",
    doseme: "Döşeme",
    perde: "Perde",
    temel: "Temel",
    diger: "Diğer",
  };

  function _esikBilgisiRenderla(sonuc) {
    const p = document.getElementById("esik-bilgisi");
    const tip = ELEMAN_TIPI_ETIKET[sonuc.parametreler.eleman_tipi] || sonuc.parametreler.eleman_tipi;
    p.textContent = `Kullanılan eşik: ${tip} — gerekli min. pas payı ${sonuc.parametreler.gerekli_pas_payi_mm.toFixed(0)} mm (operatör/denetçi girdisi)`;
  }

  function _durumKartiRenderla(sonuc) {
    const kart = document.getElementById("durum-karti");
    if (sonuc.donati_var_mi) {
      kart.className = "durum-karti bulundu";
      kart.textContent = `✓ DONATI TESPİT EDİLDİ — ${sonuc.donati_sayisi} adet`;
    } else {
      kart.className = "durum-karti bulunamadi";
      kart.textContent = "✕ DONATI BULUNAMADI";
    }
  }

  function _tabloRenderla(sonuc) {
    const govde = document.getElementById("donati-tablosu-govde");
    govde.innerHTML = "";
    for (const d of sonuc.donatilar) {
      const etiket = DURUM_ETIKET[d.durum] || { metin: "-", sinif: "" };
      const satir = document.createElement("tr");
      satir.innerHTML = `
        <td>${d.id}</td>
        <td>${d.cap_mm} mm</td>
        <td>${d.pas_payi_mm.toFixed(0)} mm</td>
        <td>${d.katman}</td>
        <td>${d.yon === "dusey" ? "Düşey" : "Yatay"}</td>
        <td><span class="durum-etiket ${etiket.sinif}">${etiket.metin}</span></td>
      `;
      govde.appendChild(satir);
    }
  }

  function _bosluklariRenderla(sonuc) {
    const bolum = document.getElementById("bosluk-uyari-bolumu");
    const liste = document.getElementById("bosluk-listesi");
    if (!sonuc.bosluklar || sonuc.bosluklar.length === 0) {
      bolum.hidden = true;
      return;
    }
    liste.innerHTML = "";
    for (const b of sonuc.bosluklar) {
      const oge = document.createElement("li");
      oge.textContent = `Boşluk #${b.id} — boyut ${b.boyut_mm.toFixed(0)} mm, derinlik ${b.derinlik_mm.toFixed(0)} mm`;
      liste.appendChild(oge);
    }
    bolum.hidden = false;
  }

  function renderla(sonuc) {
    _durumKartiRenderla(sonuc);
    _esikBilgisiRenderla(sonuc);
    _tabloRenderla(sonuc);
    _bosluklariRenderla(sonuc);
  }

  return { renderla };
})();
