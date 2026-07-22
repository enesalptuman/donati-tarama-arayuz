#!/bin/sh
# Konteyner başlangıç betiği: önce DB şemasını güncelle, sonra uygulamayı başlat.
# `set -e`: herhangi bir komut hata verirse betik anında durur (sessiz hata olmaz).
set -e

echo "[entrypoint] Veritabanı migration'ları uygulanıyor (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Uygulama başlatılıyor..."
# `exec "$@"`: Dockerfile'daki CMD'yi (uvicorn ...) bu sürecin YERİNE geçirerek
# çalıştırır → uvicorn PID 1 olur, sinyalleri (docker stop) doğru alır.
exec "$@"
