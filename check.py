import cv2
import os
import shutil
from tqdm import tqdm
from pathlib import Path


def check_and_clean_images(image_dir, backup_dir=None, move_corrupted=True):
    """
    检查并清理损坏的图片

    Args:
        image_dir: 图片目录
        backup_dir: 备份目录（可选）
        move_corrupted: True=移动到备份目录，False=直接删除
    """
    image_dir = Path(image_dir)
    if backup_dir:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

    corrupted_files = []
    all_images = (
        list(image_dir.glob("*.jpg"))
        + list(image_dir.glob("*.png"))
        + list(image_dir.glob("*.jpeg"))
    )

    print(f"开始检查 {len(all_images)} 张图片...")

    for img_path in tqdm(all_images):
        try:
            # 尝试用OpenCV读取
            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError("无法读取图片")

            # 检查图像尺寸
            if img.size == 0:
                raise ValueError("图片尺寸为0")

            # 检查数组形状
            if len(img.shape) != 3:
                raise ValueError(f"无效的图像形状: {img.shape}")

        except Exception as e:
            corrupted_files.append(img_path)
            if backup_dir and move_corrupted:
                # 移动到备份目录
                shutil.move(str(img_path), str(backup_dir / img_path.name))
                print(f"已移动损坏文件: {img_path.name}")
            else:
                # 直接删除
                os.remove(str(img_path))
                print(f"已删除损坏文件: {img_path.name}")

    print(f"\n检查完成！发现 {len(corrupted_files)} 张损坏图片")
    if corrupted_files:
        # 保存损坏文件列表
        with open("corrupted_images.txt", "w") as f:
            for path in corrupted_files:
                f.write(str(path) + "\n")
        print("损坏文件列表已保存到 corrupted_images.txt")

    return corrupted_files


# 使用示例
if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    data_root = Path(os.environ.get("PIGEON_DATA_ROOT", root))
    image_dir = data_root / "images_all"
    backup_dir = data_root / "corrupted_backup"

    # 检查并清理
    corrupted = check_and_clean_images(image_dir, backup_dir, move_corrupted=True)
