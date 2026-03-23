# siamese/embed_all.py
import os
import sys
from pathlib import Path
import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from PIL import Image
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siamese.model import SiameseNet
from siamese.dataset import SingleImageDataset, get_transforms

DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", REPO_ROOT))

CHECKPOINT = REPO_ROOT / "siamese" / "checkpoints" / "best.pth"
CROPS_ROOT = DATA_ROOT / "crops"  # folder with cleaned crops (224x224)
META = (
    DATA_ROOT / "crops_metadata_clean.csv"
)  # must contain crop_path,blood_id (crop_path relative or absolute)
OUT_EMB = REPO_ROOT / "retrieval" / "embeddings.npy"
OUT_META = REPO_ROOT / "retrieval" / "meta.csv"

os.makedirs(OUT_EMB.parent, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SiameseNet(emb_size=128, backbone_name="resnet50").to(device)
model.load_state_dict(torch.load(CHECKPOINT, map_location=device))
model.eval()

# load metadata, build list of image full paths and blood_id
df = pd.read_csv(META)
paths = []
bloods = []
for _, r in df.iterrows():
    p = r["crop_path"]
    if not os.path.isabs(p):
        p = os.path.join(CROPS_ROOT, p)
    if not os.path.exists(p):
        continue
    paths.append(p)
    bloods.append(r["blood_id"])

dataset = SingleImageDataset(paths, transform=get_transforms(train=False))
loader = DataLoader(dataset, batch_size=64, num_workers=4)

embs = []
meta_rows = []
with torch.no_grad():
    for imgs, ps in tqdm(loader, total=len(loader)):
        imgs = imgs.to(device)
        e = model(imgs).cpu().numpy()
        embs.append(e)
        meta_rows.extend(ps)
embs = np.vstack(embs)
# L2 normalize (should already be normalized by model, but ensure)
norms = np.linalg.norm(embs, axis=1, keepdims=True)
embs = embs / (norms + 1e-12)

np.save(OUT_EMB, embs)
pd.DataFrame({"path": meta_rows, "blood_id": bloods[: len(meta_rows)]}).to_csv(
    OUT_META, index=False
)
print("Saved embeddings:", embs.shape, "meta rows:", len(meta_rows))
