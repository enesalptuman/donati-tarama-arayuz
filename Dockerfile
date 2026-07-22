# =====================================================================
# AŞAMA 1 — builder: bağımlılıkları bir sanal ortama kurar.
# Bu aşamadaki her şey (pip önbelleği, geçici dosyalar) son imaja GİRMEZ.
# =====================================================================
FROM python:3.13-slim AS builder

# pip'i sessiz ve önbelleksiz çalıştır (imaj katmanlarını şişirmesin)
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Güvence: bir paketin hazır wheel'i yoksa kaynaktan derleyebilmek için
# derleme araçları. Yalnızca BUILDER aşamasında — son imaja gitmez.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# Önce SADECE requirements'ı kopyala. Neden ayrı katman? Docker katman
# önbelleği: requirements değişmedikçe pip install adımı yeniden çalışmaz,
# sadece kod değişince hızlı yeniden derlenir.
COPY requirements.txt .

# İzole bir sanal ortam oluştur ve çalışma zamanı bağımlılıklarını kur.
# (requirements-dev.txt KURULMAZ → test/lint araçları üretime gitmez.)
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# =====================================================================
# AŞAMA 2 — runtime: sadece çalışması için gerekenleri içeren ince imaj.
# =====================================================================
FROM python:3.13-slim AS runtime

# PDF raporundaki Türkçe karakterler (ş, ğ, İ) için DejaVu fontu.
# --no-install-recommends: gereksiz paket getirme. Sonra apt önbelleğini sil.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# Güvenlik: uygulamayı root olarak DEĞİL, ayrı bir kullanıcıyla çalıştır.
RUN useradd --create-home --uid 1000 donati

WORKDIR /app

# Builder'dan sadece hazır sanal ortamı kopyala (derleme araçları gelmez).
COPY --from=builder /opt/venv /opt/venv

# venv'i PATH'e ekle → "python"/"uvicorn"/"alembic" doğrudan venv'den çalışır.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Uygulama dosyalarını kopyala (yalnızca çalışması için gerekenler).
COPY app ./app
COPY static ./static
COPY alembic ./alembic
COPY alembic.ini config.yaml ./
COPY deploy/docker-entrypoint.sh /usr/local/bin/entrypoint.sh

# Entrypoint'i hazırla: olası CRLF'leri temizle (Windows checkout güvencesi),
# çalıştırılabilir yap, görüntü dizinini oluştur, sahipliği donati'ye ver.
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh \
 && chmod +x /usr/local/bin/entrypoint.sh \
 && mkdir -p /app/taramalar \
 && chown -R donati:donati /app

# Bundan sonraki komutlar root değil, donati kullanıcısıyla çalışır.
USER donati

# Konteynerin dinlediği port (belgeleme amaçlı; yayınlamak compose'da).
EXPOSE 8000

# Sağlık kontrolü: /health 200 dönmezse Docker konteyneri "unhealthy" işaretler.
# curl yerine Python kullanıyoruz (imajda ekstra paket gerekmesin).
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

# Konteyner başlarken önce migration (entrypoint), sonra CMD'yi çalıştırır.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
