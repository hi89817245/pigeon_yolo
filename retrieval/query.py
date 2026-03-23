# retrieval/query.py
import faiss, numpy as np, os, sys
import torch
from PIL import Image
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siamese.model import SiameseNet
from siamese.dataset import get_transforms

DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", REPO_ROOT))

INDEX = REPO_ROOT / "retrieval" / "idx.faiss"
EMB_META = REPO_ROOT / "retrieval" / "meta.csv"
CHECKPOINT = REPO_ROOT / "siamese" / "checkpoints" / "best.pth"

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SiameseNet(emb_size=128, backbone_name="resnet50").to(device)
model.load_state_dict(torch.load(CHECKPOINT, map_location=device))
model.eval()

index = faiss.read_index(str(INDEX))
meta = pd.read_csv(EMB_META)

transform = get_transforms(train=False)


def embed_image(path):
    img = Image.open(path).convert("RGB")
    x = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        e = model(x).cpu().numpy().astype("float32")
    # ensure normalized
    e = e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-12)
    return e


def compare_two(path1, path2):
    e1 = embed_image(path1)
    e2 = embed_image(path2)
    sim = float((e1 * e2).sum())  # inner product on normalized = cosine
    return sim


def search(path, topk=5):
    q = embed_image(path)
    D, I = index.search(q, topk)
    results = []
    for dist, idx in zip(D[0], I[0]):
        row = meta.iloc[idx]
        results.append(
            {"path": row["path"], "blood_id": row["blood_id"], "score": float(dist)}
        )
    return results


# Example usage
if __name__ == "__main__":
    q = DATA_ROOT / "crops" / "1337_0.jpg"
    print("Top matches:", search(q, topk=5))
    print(
        "Compare:",
        compare_two(
            DATA_ROOT / "crops" / "320224_0.jpg", DATA_ROOT / "crops" / "677532_0.jpg"
        ),
    )
