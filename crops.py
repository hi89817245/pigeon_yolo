# yolov11/batch_crop.py
from pathlib import Path
from ultralytics import YOLO
import cv2, os, pandas as pd, tqdm

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", ROOT))

MODEL = ROOT / "project" / "assets" / "best.pt"
IMG_DIR = DATA_ROOT / "images_all"
OUT_DIR = DATA_ROOT / "crops"
MAP_CSV = DATA_ROOT / "crop2img.csv"
os.makedirs(OUT_DIR, exist_ok=True)

model = YOLO(str(MODEL))
rows = []
for img_fn in tqdm.tqdm(os.listdir(IMG_DIR)):
    img_path = IMG_DIR / img_fn
    try:
        res = model.predict(source=str(img_path), conf=0.25, iou=0.45, verbose=False)[0]
    except Exception as e:
        print("error", img_path, e)
        continue
    img = cv2.imread(str(img_path))
    if img is None:
        continue
    for i, box in enumerate(res.boxes.xyxy.tolist()):
        x1, y1, x2, y2 = map(int, box)
        score = float(res.boxes.conf[i]) if hasattr(res.boxes, "conf") else None
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        outname = f"{os.path.splitext(img_fn)[0]}_{i}.jpg"
        cv2.imwrite(str(OUT_DIR / outname), crop)
        rows.append([outname, img_fn, i, x1, y1, x2, y2, score])

pd.DataFrame(
    rows, columns=["crop", "src_image", "box_idx", "x1", "y1", "x2", "y2", "score"]
).to_csv(MAP_CSV, index=False)
print("Saved crops:", len(rows))
