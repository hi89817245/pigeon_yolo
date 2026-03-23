import os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", ROOT))

META = DATA_ROOT / "crops_metadata.csv"
OUT = DATA_ROOT / "crops_metadata_clean.csv"

df = pd.read_csv(META)

# 删除 blood_id 空的行
df = df.dropna(subset=["blood_id"])

# 转成字符串（很重要）
df["blood_id"] = df["blood_id"].astype(str)
df["img_id"] = df["img_id"].astype(str)

df.to_csv(OUT, index=False)

print("Cleaned metadata saved to:", OUT)
print("Total cleaned rows:", len(df))
print(df.head())
