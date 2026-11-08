from dataclasses import replace
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.auth import get_current_user
from app.config import get_settings
from app.detector import TfliteYoloDetector, get_detector
from app.main import app
from app.schemas import Box, Detection


class FakeDetector:
    def predict(self, image):
        return [
            Detection(
                class_name="defeito",
                confidence=0.9,
                box=Box(x_min=1, y_min=2, x_max=3, y_max=4),
            )
        ]


def png_upload():
    buffer = BytesIO()
    Image.new("RGB", (32, 16)).save(buffer, format="PNG")
    return {"file": ("pcb.png", buffer.getvalue(), "image/png")}


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated(client):
    app.dependency_overrides[get_current_user] = lambda: {"uid": "teste"}
    return client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_requires_token(client):
    app.dependency_overrides[get_detector] = FakeDetector
    assert client.post("/api/predict", files=png_upload()).status_code == 401


def test_predict_rejects_invalid_token_without_google_credentials(client):
    settings = replace(get_settings(), firebase_project_id="projeto-teste")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_detector] = FakeDetector
    headers = {"Authorization": "Bearer token-invalido"}
    assert client.post("/api/predict", files=png_upload(), headers=headers).status_code == 401


def test_predict_returns_detections(authenticated):
    app.dependency_overrides[get_detector] = FakeDetector
    response = authenticated.post("/api/predict", files=png_upload())
    assert response.status_code == 200
    body = response.json()
    assert (body["width"], body["height"]) == (32, 16)
    assert body["detections"][0]["class_name"] == "defeito"
    assert body["detections"][0]["box"]["x_max"] == 3


def test_predict_rejects_invalid_image(authenticated):
    app.dependency_overrides[get_detector] = FakeDetector
    files = {"file": ("pcb.png", b"nao e imagem", "image/png")}
    assert authenticated.post("/api/predict", files=files).status_code == 400


def test_predict_without_model_returns_503(authenticated, tmp_path):
    missing = tmp_path / "model.tflite"
    labels = tmp_path / "labels.json"
    app.dependency_overrides[get_detector] = lambda: TfliteYoloDetector(missing, labels, 0.25, 1)
    assert authenticated.post("/api/predict", files=png_upload()).status_code == 503
