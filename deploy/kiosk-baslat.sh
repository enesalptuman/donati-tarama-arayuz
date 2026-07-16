#!/usr/bin/env bash
# Chromium'u tam ekran (kiosk) modda, operatör arayüzüne yönlendirerek başlatır.
# Backend (donati-tarama.service) hazır olana kadar bekler.

set -euo pipefail

URL="http://localhost:8000"
BEKLEME_SANIYE=1
MAKS_DENEME=60

deneme=0
until curl -s -o /dev/null "$URL"; do
  deneme=$((deneme + 1))
  if [ "$deneme" -ge "$MAKS_DENEME" ]; then
    echo "Backend $((MAKS_DENEME * BEKLEME_SANIYE)) saniyede ayağa kalkmadı, yine de deneniyor." >&2
    break
  fi
  sleep "$BEKLEME_SANIYE"
done

exec chromium-browser \
  --kiosk \
  --app="$URL" \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --incognito
