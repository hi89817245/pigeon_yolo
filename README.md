### 下载本项目
`git clone https://github.com/cci183147/pigeon_yolo`

`uv sync`

### Windows 使用注意
- 现在所有脚本都改成以專案目錄為基準的相對路徑，Windows 直接可跑
- 如果你的資料集不放在專案根目錄，可先設定 `PIGEON_DATA_ROOT`
  - PowerShell：`$env:PIGEON_DATA_ROOT="D:\\your_data_root"`
- 运行 Flask 服務可直接用 `python project/app.py`

### 啟動方式
#### 1. 安裝環境
```powershell
git clone https://github.com/cci183147/pigeon_yolo
cd pigeon_yolo
uv sync
```

#### 2. 準備資料
- 把原始圖片、標註與血統資料放到專案根目錄，或先設定 `PIGEON_DATA_ROOT`
- 如果要重新整理資料，可依序執行：
```powershell
python unzip.py
python yoloData.py
python train.py
python check.py
python crops.py
python crops2blood.py
python crops2blood_clean.py
python pairs.py
python siamese/train.py
python siamese/embed_all.py
python retrieval/build_index.py
```

#### 3. 啟動服務
```powershell
python project/app.py
```

#### 4. 開啟網頁
- 瀏覽器開啟 `http://localhost:8000`
- 可使用「虹膜比對」上傳兩張圖片做比對
- 也可使用「虹膜搜索」上傳單張圖片查詢 top-k 結果

#### 5. API 說明
- `POST /compare`：上傳 `img1`、`img2` 兩張圖，回傳相似度與是否同血親
- `POST /search`：上傳 `image` 與 `k`，回傳裁切圖與 top-k 搜尋結果

### 目錄結構
- `project/`：正式可執行的後端與前端
  - `app.py`：Flask API，提供比對與搜尋
  - `static/`：前端頁面
  - `utils/`：YOLO 裁切、embedding、FAISS 搜尋工具
  - `models/`：Siamese 模型定義與載入
  - `assets/`：已訓練好的模型與索引檔
- `siamese/`：Siamese 訓練、推論、產生 embedding 的腳本
- `retrieval/`：FAISS 索引建立與查詢腳本
- `train.py`：YOLO 偵測模型訓練入口
- `yoloData.py`：把原始標註轉成 YOLO 資料格式
- `unzip.py`：解壓圖片並整理到 `images_all/`
- `crops.py`、`crops2blood.py`、`crops2blood_clean.py`、`pairs.py`：裁切、標註對應與訓練資料產生流程
- `check.py`、`predict.py`：資料檢查與單張推論
- `PLAN.md`：開發計畫與待辦紀錄

#### 数据处理
`python unzip.py`解压图片文件1~12.zip,并统一置于images_all中

`python yoloData.py` 将数据处理为yolo格式，输出于pigeon_iris_yolo
### Yolo模型训练
本项目使用**Yolov11n.pt**训练，请提前准备好

`python train.py` 参数如下:

	epochs=10,
    imgsz=640,
    batch=-1,
    cache=False,
    workers=0,`

得到模型**best.pt**

`python check.py` 处理错误图片

`python crops.py ` 获得虹膜切片，存放于crops中

`python crops2blood.py` 建立blood_id和对应切片的映射关系

`python crops2blood_clean` 清洗null值，得到crops_metadata_clean.csv

### Siamese embedding
##### 数据处理

`python pairs.py`得到pairs.csv作为模型训练数据

##### 模型训练

`python siamese/train.py`

模型参数如下：

	EMB_SIZE = 128
	BACKBONE = 'resnet50'   
	BATCH = 32
	EPOCHS = 10
	LR = 1e-4
	WEIGHT_DECAY = 1e-5
	VAL_SPLIT = 0.1
	MARGIN = 1.0 

用训练好的模型对所有图像生成 embedding

`python siamese/embed_all.py`

构建 FAISS 索引 — `retrieval/build_index.py`
### 使用效果
系统会检索图片q，返回 top-k 匹配，包括 blood_id 和分数

同时比较p1和p2，返回相似度分数（0~1）

<img width="2148" height="238" alt="image" src="https://github.com/user-attachments/assets/3b447b99-c435-4853-b313-af319f5dd60c" />


<img width="2586" height="221" alt="image" src="https://github.com/user-attachments/assets/6ab908e6-75d4-4da6-921c-1e709c4939ac" />
