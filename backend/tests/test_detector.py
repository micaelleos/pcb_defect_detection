import numpy as np
import pytest
from PIL import Image

from app.detector import decode_predictions, preprocess

NUM_ANCHORS = 80**2 + 40**2 + 20**2
LABELS = ["a", "b"]


def encode(left, top, right, bottom):
    """Monta a regressão de uma célula com distâncias inteiras, em strides."""
    logits = np.full((4, 16), -100.0, dtype=np.float32)
    for side, value in enumerate((left, top, right, bottom)):
        logits[side, value] = 100.0
    return logits.ravel()


def outputs():
    return np.zeros((NUM_ANCHORS, 64), np.float32), np.zeros((NUM_ANCHORS, 2), np.float32)


def decode(boxes, scores, scale=1.0, size=(640, 640), threshold=0.25):
    return decode_predictions(boxes, scores, LABELS, scale, size, threshold)


def test_preprocess_keeps_aspect_ratio_and_pads_bottom():
    batch, scale = preprocess(Image.new("RGB", (1280, 640), (255, 255, 255)))
    assert batch.shape == (1, 640, 640, 3)
    assert scale == 0.5
    assert batch[0, 319, 639, 0] == pytest.approx(255)
    assert batch[0, 320, 0, 0] == 0


def test_decodes_box_class_and_confidence():
    boxes, scores = outputs()
    # Linha 10, coluna 10 da grade de stride 8: centro em (84, 84).
    boxes[810] = encode(2, 2, 2, 2)
    scores[810] = [0.1, 0.9]

    [detection] = decode(boxes, scores)

    assert detection.class_name == "b"
    assert detection.confidence == pytest.approx(0.9)
    assert detection.box.x_min == pytest.approx(68)
    assert detection.box.y_max == pytest.approx(100)


def test_uses_coarser_grid_after_finer_ones():
    boxes, scores = outputs()
    # Primeira célula da grade de stride 16: centro em (8, 8).
    boxes[80**2] = encode(0, 0, 3, 1)
    scores[80**2] = [0.8, 0.0]

    [detection] = decode(boxes, scores)

    assert (detection.box.x_max, detection.box.y_max) == pytest.approx((56, 24))


def test_suppresses_overlapping_boxes_keeping_best():
    boxes, scores = outputs()
    boxes[810] = encode(2, 2, 2, 2)
    scores[810] = [0.6, 0.0]
    # Célula vizinha, mesma caixa (68..100), outra classe: o NMS ignora a classe.
    boxes[811] = encode(3, 2, 1, 2)
    scores[811] = [0.0, 0.9]

    [detection] = decode(boxes, scores)

    assert detection.class_name == "b"


def test_filters_low_confidence():
    boxes, scores = outputs()
    scores[810] = [0.2, 0.0]
    assert decode(boxes, scores) == []


def test_maps_boxes_to_original_image_and_clips():
    boxes, scores = outputs()
    boxes[810] = encode(2, 2, 2, 2)
    scores[810] = [0.9, 0.0]
    boxes[0] = encode(2, 2, 2, 2)  # centro em (4, 4): sairia da imagem à esquerda.
    scores[0] = [0.8, 0.0]

    first, second = decode(boxes, scores, scale=0.5, size=(1280, 640))

    assert first.box.x_min == pytest.approx(136)
    assert first.box.x_max == pytest.approx(200)
    assert second.box.x_min == 0
