import zipfile
import os
import sys
import glob
from pathlib import Path


def extract_and_flatten():
    """
    1. 解压1~12.zip文件到images_all文件夹
    2. 将所有图片移动到images_all根目录
    3. 删除所有子文件夹
    """

    root = Path(__file__).resolve().parent
    out_dir = root / "images_all"

    # 创建目标文件夹
    out_dir.mkdir(exist_ok=True)

    # 统计信息
    total_files = 0
    successful_zips = 0

    # 支持的图片扩展名
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".ico",
        ".svg",
    }

    print("开始解压并整理图片...")
    print("=" * 60)

    # 按顺序处理1~12.zip
    for i in range(1, 13):
        zip_file = f"{i}.zip"
        zip_path = root / zip_file

        if not zip_path.exists():
            print(f"⚠  警告: {zip_file} 不存在，跳过")
            continue

        print(f"处理: {zip_file}")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # 获取ZIP文件中的所有文件
                file_list = zf.namelist()
                zip_file_count = 0

                for file_name in file_list:
                    # 检查是否为图片文件
                    file_ext = os.path.splitext(file_name)[1].lower()
                    if file_ext in image_extensions:
                        # 提取文件名（不含路径）
                        base_name = os.path.basename(file_name)

                        # 处理同名文件冲突
                        dest_name = base_name
                        dest_path = out_dir / dest_name

                        # 如果文件已存在，重命名
                        counter = 1
                        while dest_path.exists():
                            name_part, ext = os.path.splitext(base_name)
                            dest_name = f"{name_part}_{counter}{ext}"
                            dest_path = out_dir / dest_name
                            counter += 1

                        # 直接提取文件到目标位置
                        with zf.open(file_name) as source:
                            with open(dest_path, "wb") as target:
                                target.write(source.read())

                        zip_file_count += 1
                        total_files += 1

                print(f"  ✓ 提取了 {zip_file_count} 个图片文件")
                successful_zips += 1

        except Exception as e:
            print(f"  ✗ 处理 {zip_file} 时出错: {e}")

    print("=" * 60)
    print(f"完成！")
    print(f"成功处理: {successful_zips}/12 个ZIP文件")
    print(f"总图片数: {total_files} 个")
    print(f"图片位置: {out_dir.resolve()}")

    # 显示目录中的文件数
    try:
        files_in_dir = len(
            [f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
        )
        print(f"images_all文件夹中的文件数: {files_in_dir}")
    except Exception as e:
        print(f"无法统计文件数: {e}")


if __name__ == "__main__":
    # 检查当前目录是否有ZIP文件
    zip_files = glob.glob("*.zip")
    if not zip_files:
        print("当前目录没有找到ZIP文件")
        sys.exit(1)

    print(f"找到 {len(zip_files)} 个ZIP文件")
    extract_and_flatten()
