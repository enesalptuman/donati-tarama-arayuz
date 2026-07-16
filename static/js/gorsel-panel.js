// Görsel panel: yansıma haritasını canvas'a çizer, donatı/boşluk işaretlerini
// bindirir, cm ölçek çizgisi ekler ve tıklamada donatı detayını gösterir.

const GorselPanel = (() => {
  const RENKLER = {
    uygun: "#1e7d34",
    sinirda: "#b56a00",
    yetersiz: "#b3261e",
    bosluk: "#6a3fb5",
  };

  let isaretler = []; // {tipi, veri, cx, cy, r}
  let canvasEl, ctx, olcekCmBasinaPx;

  function _isaretleriHesapla(sonuc, cmBasinaPx) {
    const liste = [];
    for (const d of sonuc.donatilar) {
      liste.push({
        tipi: "donati",
        veri: d,
        cx: d.x_cm * cmBasinaPx,
        cy: d.y_cm * cmBasinaPx,
        r: Math.max((d.cap_mm / 10 / 2) * cmBasinaPx, 10),
      });
    }
    for (const b of sonuc.bosluklar) {
      liste.push({
        tipi: "bosluk",
        veri: b,
        cx: b.x_cm * cmBasinaPx,
        cy: b.y_cm * cmBasinaPx,
        r: Math.max((b.boyut_mm / 10 / 2) * cmBasinaPx, 8),
      });
    }
    return liste;
  }

  function _cizDonati(isaret) {
    const d = isaret.veri;
    const supheli = d.guven < 0.7;
    ctx.beginPath();
    ctx.arc(isaret.cx, isaret.cy, isaret.r, 0, Math.PI * 2);
    ctx.lineWidth = 3;
    ctx.strokeStyle = RENKLER[d.durum] || "#888";
    ctx.setLineDash(supheli ? [5, 4] : []);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.font = "bold 12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(d.id), isaret.cx, isaret.cy);
  }

  function _cizBosluk(isaret) {
    const b = isaret.veri;
    const r = isaret.r;
    ctx.beginPath();
    ctx.moveTo(isaret.cx, isaret.cy - r);
    ctx.lineTo(isaret.cx + r, isaret.cy + r);
    ctx.lineTo(isaret.cx - r, isaret.cy + r);
    ctx.closePath();
    ctx.lineWidth = 3;
    ctx.strokeStyle = RENKLER.bosluk;
    ctx.setLineDash(b.guven < 0.7 ? [5, 4] : []);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function _olcekCizgisiCiz(cmBasinaPx, genislikPx, yukseklikPx) {
    // Yuvarlak bir uzunluk seç (5/10/20/50 cm gibi) ki çizgi okunaklı olsun.
    const adaylar = [5, 10, 20, 25, 50];
    let uzunlukCm = adaylar[0];
    for (const a of adaylar) {
      if (a * cmBasinaPx <= genislikPx * 0.3) uzunlukCm = a;
    }
    const uzunlukPx = uzunlukCm * cmBasinaPx;
    const x0 = 16, y0 = yukseklikPx - 20;

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0 + uzunlukPx, y0);
    ctx.moveTo(x0, y0 - 6);
    ctx.lineTo(x0, y0 + 6);
    ctx.moveTo(x0 + uzunlukPx, y0 - 6);
    ctx.lineTo(x0 + uzunlukPx, y0 + 6);
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 13px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(`${uzunlukCm} cm`, x0, y0 - 10);
  }

  function _yeniden_ciz(sonuc) {
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    ctx.drawImage(canvasEl._goruntu, 0, 0, canvasEl.width, canvasEl.height);
    for (const isaret of isaretler) {
      if (isaret.tipi === "donati") _cizDonati(isaret);
      else _cizBosluk(isaret);
    }
    _olcekCizgisiCiz(olcekCmBasinaPx, canvasEl.width, canvasEl.height);
  }

  function _detayGoster(isaret, ekranX, ekranY) {
    const kutu = document.getElementById("donati-detay-kutusu");
    if (isaret.tipi === "donati") {
      const d = isaret.veri;
      const yonMetni = d.yon === "dusey" ? "Düşey" : "Yatay";
      const durumMetni = { uygun: "✓ UYGUN", sinirda: "⚠ SINIRDA", yetersiz: "✕ YETERSİZ" }[d.durum] || "-";
      kutu.innerHTML = `
        <strong>Donatı #${d.id}</strong><br>
        Çap: ${d.cap_mm} mm<br>
        Pas Payı: ${d.pas_payi_mm.toFixed(0)} mm<br>
        Katman: ${d.katman}<br>
        Yön: ${yonMetni}<br>
        Güven: %${Math.round(d.guven * 100)}<br>
        Durum: ${durumMetni}
        <button type="button">Kapat</button>
      `;
    } else {
      const b = isaret.veri;
      kutu.innerHTML = `
        <strong>Boşluk #${b.id}</strong><br>
        Boyut: ${b.boyut_mm.toFixed(0)} mm<br>
        Derinlik: ${b.derinlik_mm.toFixed(0)} mm<br>
        Güven: %${Math.round(b.guven * 100)}
        <button type="button">Kapat</button>
      `;
    }
    kutu.style.left = `${Math.min(ekranX, canvasEl.clientWidth - 200)}px`;
    kutu.style.top = `${Math.min(ekranY, canvasEl.clientHeight - 140)}px`;
    kutu.hidden = false;
    kutu.querySelector("button").addEventListener("click", () => { kutu.hidden = true; });
  }

  function _tiklamayiIsle(evt) {
    const oran = canvasEl.width / canvasEl.clientWidth;
    const x = (evt.offsetX) * oran;
    const y = (evt.offsetY) * oran;
    let enYakin = null, enYakinMesafe = Infinity;
    for (const isaret of isaretler) {
      const mesafe = Math.hypot(isaret.cx - x, isaret.cy - y);
      if (mesafe <= isaret.r + 8 && mesafe < enYakinMesafe) {
        enYakin = isaret;
        enYakinMesafe = mesafe;
      }
    }
    if (enYakin) {
      _detayGoster(enYakin, evt.offsetX, evt.offsetY);
    } else {
      document.getElementById("donati-detay-kutusu").hidden = true;
    }
  }

  function ciz(sonuc, goruntuUrl) {
    canvasEl = document.getElementById("harita-canvas");
    ctx = canvasEl.getContext("2d");
    document.getElementById("donati-detay-kutusu").hidden = true;

    const img = new Image();
    img.onload = () => {
      canvasEl.width = img.naturalWidth;
      canvasEl.height = img.naturalHeight;
      canvasEl._goruntu = img;

      // piksel_boyut_mm: bir görüntü pikseli kaç mm'ye denk gelir.
      olcekCmBasinaPx = 10 / sonuc.goruntu.piksel_boyut_mm;
      isaretler = _isaretleriHesapla(sonuc, olcekCmBasinaPx);
      _yeniden_ciz(sonuc);
    };
    img.src = goruntuUrl;

    canvasEl.removeEventListener("click", canvasEl._tiklamaDinleyici || (() => {}));
    canvasEl._tiklamaDinleyici = _tiklamayiIsle;
    canvasEl.addEventListener("click", _tiklamayiIsle);
  }

  return { ciz };
})();
