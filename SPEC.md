# Go 遷移規格

## 目標
將專案拆成三段：
- `Go.exe`：前端、API、啟動與流程控制
- `Python.exe`：ML 推論服務
- `models/`：模型與索引檔，獨立放置，不打包進 exe

## 系統分工
### Go 端
- 提供首頁與靜態資源
- 接收圖片上傳
- 驗證參數與檔案格式
- 啟動與關閉 Python 服務
- 將 Python 結果轉成前端格式

### Python 端
- 虹膜裁切
- embedding 產生
- 相似度搜尋
- 對外提供本機 API

### 模型檔
- `best.pt`
- `best.pth`
- `idx.faiss`
- `meta.csv`

### 設定與打包
- `config.json`：定義埠號、模型路徑與啟動參數
- `scripts/build_windows.ps1`：打包 Go.exe、Python.exe 與模型資料夾

## 目前實作對應
- `main.go`：Go 入口與 Python 服務啟動器
- `python_service/app.py`：獨立 Python 模型服務
- `project/core/iris_pipeline.py`：共用推論流程
- `config.json`：開發與打包共用設定
- `scripts/build_windows.ps1`：Windows 打包流程

## 服務規格
### Go.exe
- 內嵌前端頁面
- 提供使用者操作入口
- 代理呼叫 Python API

### Python.exe
- `POST /compare`
- `POST /search`
- `POST /embed`

## API 規格
### `POST /compare`
輸入：`img1`, `img2`

輸出：`similarity`, `same_blood`, `crop1`, `crop2`

### `POST /search`
輸入：`image`, `k`

輸出：`query_crop`, `results`

### `POST /embed`
輸入：`image`

輸出：`embedding`

## 啟動流程
1. 使用者啟動 `Go.exe`
2. Go 檢查 `Python.exe` 與模型檔是否存在
3. Go 啟動 Python 本機服務
4. 前端透過 Go 操作
5. Go 轉送請求到 Python

## 非功能需求
- Windows 可執行
- 路徑以設定檔或相對路徑控制
- 模型檔可獨立更新
- Go 與 Python 透過 `127.0.0.1` 溝通

## 驗收標準
- `Go.exe` 可獨立啟動前端與流程
- `Python.exe` 可獨立提供模型服務
- 模型檔獨立存放且可替換
- 比對與搜尋結果與現行版本一致或接近
