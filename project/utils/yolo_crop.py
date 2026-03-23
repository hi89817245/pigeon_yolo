from pathlib import Path
import cv2, os, uuid
from ultralytics import YOLO


class IrisCropper:
    def __init__(self, model_path, out_dir="tmp/crops"):
        self.model = YOLO(str(model_path))
        base_dir = Path(__file__).resolve().parents[1]
        self.out_dir = Path(out_dir)
        if not self.out_dir.is_absolute():
            self.out_dir = base_dir / self.out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def crop(self, img_path):
        res = self.model.predict(
            source=str(img_path), conf=0.25, iou=0.45, verbose=False
        )[0]

        if len(res.boxes) == 0:
            return None

        img = cv2.imread(str(img_path))
        if img is None:
            return None

        # 取置信度最高的 box
        box = res.boxes.xyxy[0].cpu().numpy().astype(int)
        x1, y1, x2, y2 = box
        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            return None

        out_path = self.out_dir / f"{uuid.uuid4().hex}.jpg"
        cv2.imwrite(str(out_path), crop)

        return str(out_path)
