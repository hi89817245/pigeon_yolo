### 下载本项目
`git clone https://github.com/cci183147/pigeon_yolo`

`uv sync`

### Windows 使用注意
- 现在所有脚本都改成以專案目錄為基準的相對路徑，Windows 直接可跑
- 如果你的資料集不放在專案根目錄，可先設定 `PIGEON_DATA_ROOT`
  - PowerShell：`$env:PIGEON_DATA_ROOT="D:\\your_data_root"`
- 运行 Flask 服務可直接用 `uv run python project/app.py`

### 遷移文件
- `SPEC.md`：Go.exe + Python.exe + models 三段式規格
- `PLAN.md`：三段式打包與遷移工作計畫
- `config.json`：Go / Python 共用設定
- `scripts/build_windows.ps1`：Windows 打包腳本

### 啟動方式
#### 1. 安裝環境
```powershell
git clone https://github.com/cci183147/pigeon_yolo
cd pigeon_yolo
uv sync
```

#### 1-1. Go 開發環境
- 安裝 Go 1.22 以上
- 確認 `go version` 可正常執行

#### 2. 準備資料
- 把原始圖片、標註與血統資料放到專案根目錄，或先設定 `PIGEON_DATA_ROOT`
- 如果要重新整理資料，可依序執行：
```powershell
uv run python unzip.py
uv run python yoloData.py
uv run python train.py
uv run python check.py
uv run python crops.py
uv run python crops2blood.py
uv run python crops2blood_clean.py
uv run python pairs.py
uv run python siamese/train.py
uv run python siamese/embed_all.py
uv run python retrieval/build_index.py
```

#### 3. 啟動服務
- 開發模式直接啟動 Go 入口：
```powershell
go run .
```
- 打包後執行 Go 執行檔：
```powershell
go build -o Go.exe .
```
- 若要單獨啟動 Python 模型服務：
```powershell
uv run python python_service/app.py
```

#### 4. 開啟網頁
- 瀏覽器開啟 `http://localhost:8000`
- 可使用「虹膜比對」上傳兩張圖片做比對
- 也可使用「虹膜搜索」上傳單張圖片查詢 top-k 結果

#### 5. API 說明
- `POST /compare`：上傳 `img1`、`img2` 兩張圖，回傳相似度與是否同血親
- `POST /search`：上傳 `image` 與 `k`，回傳裁切圖與 top-k 搜尋結果
- `POST /embed`：上傳 `image`，回傳裁切圖與 embedding

### 目錄結構
- `main.go`：Go 入口，負責前端與 API 代理
- `go.mod`：Go 模組設定
- `project/`：正式可執行的後端與前端
  - `app.py`：Flask API，提供比對與搜尋
  - `core/`：共用推論流程
  - `static/`：前端頁面
  - `utils/`：YOLO 裁切、embedding、FAISS 搜尋工具
  - `models/`：Siamese 模型定義與載入
  - `assets/`：已訓練好的模型與索引檔
- `python_service/`：獨立 Python 模型服務入口
- `siamese/`：Siamese 訓練、推論、產生 embedding 的腳本
- `retrieval/`：FAISS 索引建立與查詢腳本
- `train.py`：YOLO 偵測模型訓練入口
- `yoloData.py`：把原始標註轉成 YOLO 資料格式
- `unzip.py`：解壓圖片並整理到 `images_all/`
- `crops.py`、`crops2blood.py`、`crops2blood_clean.py`、`pairs.py`：裁切、標註對應與訓練資料產生流程
- `check.py`、`predict.py`：資料檢查與單張推論
- `PLAN.md`：開發計畫與待辦紀錄

### 打包方式
- `Go.exe`：負責前端、API 與流程控制
- `Python.exe`：負責 ML 推論服務
- `models/`：獨立放 `best.pt`、`best.pth`、`idx.faiss`、`meta.csv`
- 兩個執行檔透過 `127.0.0.1` HTTP 溝通，不把模型硬塞進 exe
- Go 啟動時會優先尋找同目錄的 `python_service.exe`，找不到則回退執行 `python python_service/app.py`
- Python 可用 `pyinstaller --onefile python_service/app.py` 打包成 `python_service.exe`
- 推薦直接執行 `scripts/build_windows.ps1` 產生 `dist/Go.exe` 與 `dist/python_service.exe`
- 打包前請先安裝 `pyinstaller`，例如 `uv pip install pyinstaller`

#### 数据处理
`uv run python unzip.py`解压图片文件1~12.zip,并统一置于images_all中

`uv run python yoloData.py` 将数据处理为yolo格式，输出于pigeon_iris_yolo
### Yolo模型训练
本项目使用**Yolov11n.pt**训练，请提前准备好

`uv run python train.py` 参数如下:

	epochs=10,
    imgsz=640,
    batch=-1,
    cache=False,
    workers=0,`

得到模型**best.pt**

`uv run python check.py` 处理错误图片

`uv run python crops.py ` 获得虹膜切片，存放于crops中

`uv run python crops2blood.py` 建立blood_id和对应切片的映射关系

`uv run python crops2blood_clean.py` 清洗null值，得到crops_metadata_clean.csv

### Siamese embedding
##### 数据处理

`uv run python pairs.py`得到pairs.csv作为模型训练数据

##### 模型训练

`uv run python siamese/train.py`

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

`uv run python siamese/embed_all.py`

构建 FAISS 索引 — `uv run python retrieval/build_index.py`
### 使用效果
系统会检索图片q，返回 top-k 匹配，包括 blood_id 和分数

同时比较p1和p2，返回相似度分数（0~1）

<img width="2148" height="238" alt="image" src="https://github.com/user-attachments/assets/3b447b99-c435-4853-b313-af319f5dd60c" />


<img width="2586" height="221" alt="image" src="https://github.com/user-attachments/assets/6ab908e6-75d4-4da6-921c-1e709c4939ac" />
