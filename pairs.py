import pandas as pd
import random
from itertools import combinations
from tqdm import tqdm
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", ROOT))

META = DATA_ROOT / "crops_metadata_clean.csv"
OUT = DATA_ROOT / "pairs.csv"

df = pd.read_csv(META)

# 按 blood_id 分组
groups = {}
for _, row in df.iterrows():
    groups.setdefault(row["blood_id"], []).append(row["crop_path"])

positive_pairs = []
negative_pairs = []

print("Generating positive pairs...")

# 正样本对：同血统
for blood, imgs in tqdm(groups.items()):
    if len(imgs) < 2:
        continue
    for a, b in combinations(imgs, 2):
        positive_pairs.append((a, b, 1))

print("Generating negative pairs...")

all_blood_ids = list(groups.keys())

# 负样本对：不同血统
for _ in tqdm(range(len(positive_pairs))):
    blood1, blood2 = random.sample(all_blood_ids, 2)
    a = random.choice(groups[blood1])
    b = random.choice(groups[blood2])
    negative_pairs.append((a, b, 0))

# 合并
pairs = positive_pairs + negative_pairs
random.shuffle(pairs)

df_pairs = pd.DataFrame(pairs, columns=["img1", "img2", "label"])
df_pairs.to_csv(OUT, index=False)

print(f"Saved: {OUT}")
print(df_pairs.head())
