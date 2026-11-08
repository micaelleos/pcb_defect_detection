import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@dataclass(frozen=True)
class Settings:
    model_path: Path
    labels_path: Path
    confidence_threshold: float
    num_threads: int
    max_upload_bytes: int
    firebase_project_id: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        model_path=Path(os.getenv("MODEL_PATH", MODELS_DIR / "pcb_yolo.tflite")),
        labels_path=Path(os.getenv("LABELS_PATH", MODELS_DIR / "labels.json")),
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.25")),
        num_threads=int(os.getenv("NUM_THREADS", "2")),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID"),
    )
