from pydantic import BaseModel


class Box(BaseModel):
    """Caixa em pixels da imagem enviada."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float


class Detection(BaseModel):
    class_name: str
    confidence: float
    box: Box


class PredictResponse(BaseModel):
    width: int
    height: int
    detections: list[Detection]
