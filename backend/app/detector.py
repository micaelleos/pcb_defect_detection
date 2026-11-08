import json
import threading
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from app.config import get_settings
from app.schemas import Box, Detection

# Valores do treino (notebook) e do YOLOV8Detector do KerasCV.
INPUT_SIZE = 640
STRIDES = (8, 16, 32)
REG_BINS = 16
NMS_IOU_THRESHOLD = 0.7
MAX_DETECTIONS = 100


class ModelNotAvailable(Exception):
    """O modelo ainda não pode responder a inferências."""


class Detector(Protocol):
    def predict(self, image: Image.Image) -> list[Detection]: ...


def preprocess(image: Image.Image) -> tuple[np.ndarray, float]:
    """Redimensiona mantendo a proporção e completa à direita e embaixo com zeros.

    Retorna o tensor (1, 640, 640, 3) com valores de 0 a 255, pois o modelo faz a
    própria normalização, e a escala aplicada à imagem.
    """
    scale = INPUT_SIZE / max(image.width, image.height)
    size = (
        min(INPUT_SIZE, max(1, round(image.width * scale))),
        min(INPUT_SIZE, max(1, round(image.height * scale))),
    )
    resized = np.asarray(image.resize(size, Image.Resampling.BILINEAR), dtype=np.float32)
    canvas = np.zeros((INPUT_SIZE, INPUT_SIZE, 3), dtype=np.float32)
    canvas[: size[1], : size[0]] = resized
    return canvas[np.newaxis], scale


def _anchors() -> tuple[np.ndarray, np.ndarray]:
    """Centros (x, y) em pixels e stride de cada célula, em ordem de linhas."""
    points, strides = [], []
    for stride in STRIDES:
        centers = np.arange(0, INPUT_SIZE, stride, dtype=np.float32) + stride / 2
        xs, ys = np.meshgrid(centers, centers)
        points.append(np.stack([xs.ravel(), ys.ravel()], axis=1))
        strides.append(np.full(xs.size, stride, dtype=np.float32))
    return np.concatenate(points), np.concatenate(strides)


def _decode_boxes(raw_boxes: np.ndarray) -> np.ndarray:
    """Converte a saída de regressão (N, 64) em caixas xyxy na escala de 640 px."""
    points, strides = _anchors()
    logits = raw_boxes.reshape(-1, 4, REG_BINS)
    logits -= logits.max(axis=-1, keepdims=True)
    probabilities = np.exp(logits) / np.exp(logits).sum(axis=-1, keepdims=True)
    distances = (probabilities * np.arange(REG_BINS)).sum(axis=-1) * strides[:, np.newaxis]
    return np.concatenate([points - distances[:, :2], points + distances[:, 2:]], axis=1)


def _non_max_suppression(boxes: np.ndarray, scores: np.ndarray) -> list[int]:
    """NMS independente de classe, como o decodificador padrão do KerasCV."""
    remaining = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]).clip(0) * (boxes[:, 3] - boxes[:, 1]).clip(0)
    kept: list[int] = []
    while remaining.size and len(kept) < MAX_DETECTIONS:
        best, remaining = remaining[0], remaining[1:]
        kept.append(int(best))
        top_left = np.maximum(boxes[best, :2], boxes[remaining, :2])
        bottom_right = np.minimum(boxes[best, 2:], boxes[remaining, 2:])
        intersection = (bottom_right - top_left).clip(0).prod(axis=1)
        iou = intersection / (areas[best] + areas[remaining] - intersection + 1e-9)
        remaining = remaining[iou <= NMS_IOU_THRESHOLD]
    return kept


def decode_predictions(
    raw_boxes: np.ndarray,
    raw_scores: np.ndarray,
    labels: list[str],
    scale: float,
    image_size: tuple[int, int],
    confidence_threshold: float,
) -> list[Detection]:
    """Gera as detecções em pixels da imagem recebida, da maior para a menor confiança."""
    boxes = _decode_boxes(raw_boxes)
    classes = raw_scores.argmax(axis=-1)
    scores = raw_scores.max(axis=-1)

    candidates = np.flatnonzero(scores >= confidence_threshold)
    width, height = image_size
    detections = []
    for index in candidates[_non_max_suppression(boxes[candidates], scores[candidates])]:
        x_min, y_min, x_max, y_max = (boxes[index] / scale).tolist()
        detections.append(
            Detection(
                class_name=labels[classes[index]],
                confidence=float(scores[index]),
                box=Box(
                    x_min=min(max(x_min, 0.0), width),
                    y_min=min(max(y_min, 0.0), height),
                    x_max=min(max(x_max, 0.0), width),
                    y_max=min(max(y_max, 0.0), height),
                ),
            )
        )
    return detections


class TfliteYoloDetector:
    """Executa o YOLOv8 exportado do KerasCV para TFLite.

    O arquivo contém apenas a rede: a decodificação das caixas e o NMS são feitos aqui.
    O TensorFlow é importado na primeira inferência, reduzindo o custo de inicialização.
    """

    def __init__(
        self,
        model_path: Path,
        labels_path: Path,
        confidence_threshold: float,
        num_threads: int,
    ) -> None:
        self._model_path = model_path
        self._labels_path = labels_path
        self._confidence_threshold = confidence_threshold
        self._num_threads = num_threads
        self._interpreter = None
        self._labels: list[str] = []
        # O interpretador TFLite não pode ser usado por duas threads ao mesmo tempo.
        self._lock = threading.Lock()

    def _load(self) -> None:
        if self._interpreter is not None:
            return
        if not self._model_path.exists():
            raise ModelNotAvailable(f"Arquivo do modelo não encontrado: {self._model_path.name}")
        try:
            import tensorflow as tf
        except ImportError as exc:
            raise ModelNotAvailable("TensorFlow não está instalado.") from exc

        interpreter = tf.lite.Interpreter(
            model_path=str(self._model_path), num_threads=self._num_threads
        )
        interpreter.resize_tensor_input(
            interpreter.get_input_details()[0]["index"], [1, INPUT_SIZE, INPUT_SIZE, 3]
        )
        interpreter.allocate_tensors()

        labels = json.loads(self._labels_path.read_text(encoding="utf-8"))
        output_channels = {d["shape"][-1] for d in interpreter.get_output_details()}
        if output_channels != {REG_BINS * 4, len(labels)}:
            raise ModelNotAvailable("labels.json não corresponde às saídas do modelo.")
        self._labels = labels
        self._interpreter = interpreter

    def _run(self, batch: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        with self._lock:
            self._load()
            interpreter = self._interpreter
            interpreter.set_tensor(interpreter.get_input_details()[0]["index"], batch)
            interpreter.invoke()
            outputs = [interpreter.get_tensor(d["index"])[0] for d in interpreter.get_output_details()]
        # A ordem das saídas não é garantida; a de regressão tem 64 canais.
        raw_boxes = next(o for o in outputs if o.shape[-1] == REG_BINS * 4)
        raw_scores = next(o for o in outputs if o.shape[-1] != REG_BINS * 4)
        return raw_boxes, raw_scores

    def predict(self, image: Image.Image) -> list[Detection]:
        batch, scale = preprocess(image)
        raw_boxes, raw_scores = self._run(batch)
        return decode_predictions(
            raw_boxes,
            raw_scores,
            self._labels,
            scale,
            image.size,
            self._confidence_threshold,
        )


@lru_cache
def get_detector() -> Detector:
    settings = get_settings()
    return TfliteYoloDetector(
        settings.model_path,
        settings.labels_path,
        settings.confidence_threshold,
        settings.num_threads,
    )
