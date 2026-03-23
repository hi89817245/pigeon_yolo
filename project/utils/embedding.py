from pathlib import Path
import sys
import torch
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siamese.dataset import get_transforms

transform = get_transforms(train=False)


def embed_image(model, img_path, device):
    img = Image.open(img_path).convert("RGB")
    x = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        e = model(x).cpu().numpy().astype("float32")

    # L2 normalize（必须）
    e = e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-12)
    return e
