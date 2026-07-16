"""/api/tarama... uç noktaları."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
import io

from app import storage
from app.models.tarama import (
    DepolamaDurumu,
    ElemanTipiBilgisi,
    TaramaBaslatIstegi,
    TaramaBaslatYaniti,
    TaramaDurumBilgisi,
    TaramaOzet,
    TaramaSonucuZenginlestirilmis,
)
from app.report.pdf_rapor import rapor_uret
from app.services import analiz
from app.services.tarama_service import TaramaBulunamadi, TaramaDurumHatasi, tarama_servisi

router = APIRouter(prefix="/api", tags=["tarama"])


@router.get("/eleman-tipleri", response_model=list[ElemanTipiBilgisi])
async def eleman_tipleri() -> list[ElemanTipiBilgisi]:
    return analiz.eleman_tipleri_listele()


@router.post("/tarama/baslat", response_model=TaramaBaslatYaniti)
async def tarama_baslat(istek: TaramaBaslatIstegi) -> TaramaBaslatYaniti:
    try:
        return await tarama_servisi.baslat(
            istek.operator, istek.konum_etiketi, istek.eleman_tipi, istek.gerekli_pas_payi_mm
        )
    except TaramaDurumHatasi as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/tarama/{tarama_id}/durum", response_model=TaramaDurumBilgisi)
async def tarama_durum(tarama_id: str) -> TaramaDurumBilgisi:
    try:
        return await tarama_servisi.durum_al(tarama_id)
    except TaramaBulunamadi:
        raise HTTPException(status_code=404, detail="Tarama bulunamadı")


@router.get("/tarama/{tarama_id}", response_model=TaramaSonucuZenginlestirilmis)
async def tarama_sonucu(tarama_id: str) -> TaramaSonucuZenginlestirilmis:
    try:
        return await tarama_servisi.sonuc_al(tarama_id)
    except TaramaBulunamadi:
        raise HTTPException(status_code=404, detail="Tarama sonucu bulunamadı (henüz tamamlanmamış olabilir)")


@router.get("/tarama/{tarama_id}/goruntu")
async def tarama_goruntu(tarama_id: str) -> FileResponse:
    yol = storage.goruntu_yolu(tarama_id)
    if yol is None:
        raise HTTPException(status_code=404, detail="Görüntü bulunamadı")
    return FileResponse(yol, media_type="image/png")


@router.get("/taramalar", response_model=list[TaramaOzet])
async def taramalar_listesi() -> list[TaramaOzet]:
    return await tarama_servisi.listele()


@router.get("/depolama-durumu", response_model=DepolamaDurumu)
async def depolama_durumu() -> DepolamaDurumu:
    return await tarama_servisi.depolama_durumu()


@router.get("/tarama/{tarama_id}/rapor.pdf")
async def tarama_rapor(tarama_id: str) -> StreamingResponse:
    try:
        sonuc = await tarama_servisi.sonuc_al(tarama_id)
    except TaramaBulunamadi:
        raise HTTPException(status_code=404, detail="Tarama sonucu bulunamadı")
    pdf_bayt = rapor_uret(sonuc)
    return StreamingResponse(
        io.BytesIO(pdf_bayt),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapor-{tarama_id}.pdf"'},
    )


@router.delete("/tarama/{tarama_id}")
async def tarama_sil(tarama_id: str) -> Response:
    try:
        await tarama_servisi.sil(tarama_id)
    except TaramaBulunamadi:
        raise HTTPException(status_code=404, detail="Tarama bulunamadı")
    except TaramaDurumHatasi as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return Response(status_code=204)


@router.post("/tarama/{tarama_id}/iptal")
async def tarama_iptal(tarama_id: str) -> Response:
    try:
        await tarama_servisi.iptal_et(tarama_id)
    except TaramaBulunamadi:
        raise HTTPException(status_code=404, detail="Tarama bulunamadı")
    return Response(status_code=204)
