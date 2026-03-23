from ultralytics import YOLO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
model = YOLO(str(ROOT / "project" / "assets" / "best.pt"))
model.predict(
    source=str(ROOT / "images_all" / "916.jpg"),
    save=True,
    show=False,
    conf=0.25,
    iou=0.45,
)
