from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
DATA_YAML = ROOT / "pigeon_iris_yolo" / "data.yaml"

model = YOLO("yolo11n.pt")
model.train(
    data=str(DATA_YAML),
    epochs=10,
    imgsz=640,
    batch=-1,
    cache=False,
    workers=0,
)
