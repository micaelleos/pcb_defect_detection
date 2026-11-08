from io import BytesIO
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from PIL import Image, ImageOps

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.detector import Detector, ModelNotAvailable, get_detector
from app.schemas import PredictResponse

app = FastAPI(title="PCB Defect Detection API")


def _read_image(file: UploadFile, max_bytes: int) -> Image.Image:
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Imagem muito grande.")
    try:
        with Image.open(BytesIO(data)) as image:
            # Fotos de celular guardam a rotação no EXIF.
            return ImageOps.exif_transpose(image).convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo de imagem inválido.") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Rota síncrona: o FastAPI a executa em uma thread, sem bloquear o event loop.
@app.post("/api/predict", response_model=PredictResponse)
def predict(
    file: Annotated[UploadFile, File()],
    _user: Annotated[dict, Depends(get_current_user)],
    detector: Annotated[Detector, Depends(get_detector)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PredictResponse:
    image = _read_image(file, settings.max_upload_bytes)
    try:
        detections = detector.predict(image)
    except ModelNotAvailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return PredictResponse(width=image.width, height=image.height, detections=detections)
