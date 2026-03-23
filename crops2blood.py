import os
import re
from pathlib import Path
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------
# 配置区（按你的路径填写即可）
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", ROOT))

CROP_DIR = DATA_ROOT / "crops"
META_BLOOD = DATA_ROOT / "blood.csv"
OUT_CSV = DATA_ROOT / "crops_metadata.csv"


# ---------------------------------------------------------
# 工具函数：从文件名中提取数字 ID
# ---------------------------------------------------------
def extract_img_id(filename):
    """从任意文件名提取连续数字作为 imageID"""
    nums = re.findall(r"\d+", filename)
    return nums[0] if nums else None


# ---------------------------------------------------------
# Step 1: 读取 blood.csv（变长行 → python engine）
# ---------------------------------------------------------
print("📥 Loading blood.csv ...")

blood_df = pd.read_csv(
    META_BLOOD,
    header=None,
    engine="python",
    on_bad_lines="skip",  # 跳过异常行
)

print(f"👉 Loaded blood.csv, total rows (blood lines): {len(blood_df)}")

# ---------------------------------------------------------
# Step 2: 建立映射：img_id → blood_id
# ---------------------------------------------------------
print("🔧 Building blood_map (image_id → blood_id) ...")

blood_map = {}

for _, row in blood_df.iterrows():
    blood_id = str(row[0]).strip()

    # 遍历该血统对应的所有图片 ID
    for img_id in row[1:].dropna():
        img_id = str(img_id).strip()
        if img_id != "":
            blood_map[img_id] = blood_id

print(f"👉 Mapping built: {len(blood_map)} images have blood IDs")


# ---------------------------------------------------------
# Step 3: 遍历 CROP_DIR，构建结果记录
# ---------------------------------------------------------
print("📂 Scanning crop folder ...")

records = []
missing = 0

for root, _, files in os.walk(CROP_DIR):
    for file in tqdm(files):
        if not file.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        crop_path = os.path.join(root, file)
        img_id = extract_img_id(file)  # 从 crop 文件名提取 ID

        if img_id is None:
            missing += 1
            continue

        # 获取血统 ID（可能没有）
        blood_id = blood_map.get(img_id, None)

        records.append({"crop_path": crop_path, "img_id": img_id, "blood_id": blood_id})

print(f"👉 Total crops processed: {len(records)}")
print(f"⚠️ Missing image ID in filenames: {missing}")

# ---------------------------------------------------------
# Step 4: 保存结果
# ---------------------------------------------------------
print(f"💾 Saving metadata to {OUT_CSV} ...")

df_out = pd.DataFrame(records)
df_out.to_csv(OUT_CSV, index=False)

print("✅ Done!")
print(f"📄 Output CSV: {OUT_CSV}")
print("Columns:")
print(df_out.head())
