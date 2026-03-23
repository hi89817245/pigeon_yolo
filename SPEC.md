# Go 遷移規格

## 目標
將現有專案調整為 Go + Python 混合架構。
- Go 負責 Web、API、檔案管理、流程編排
- Python 負責 YOLO、Siamese、FAISS 與離線訓練

## 作用範圍
### Go 端
- 提供首頁與靜態頁面
- 接收圖片上傳
- 驗證參數與檔案格式
- 呼叫 Python 模型服務
- 整理回傳結果給前端

### Python 端
- 虹膜裁切
- embedding 產生
- 相似度搜尋
- 模型訓練與索引更新

## API 規格
### `POST /compare`
輸入：
- `img1`
- `img2`

輸出：
- `similarity`
- `same_blood`
- `crop1`
- `crop2`

### `POST /search`
輸入：
- `image`
- `k`

輸出：
- `query_crop`
- `results`

### `POST /embed`
輸入：
- `image`

輸出：
- `embedding`

## 非功能需求
- Windows 可執行
- 路徑採相對路徑或環境變數控制
- 回傳格式穩定
- 模型服務可獨立部署

## 驗收標準
- Go 可單獨提供 Web 與 API
- Python 可單獨提供模型服務
- 比對與搜尋結果與現行版本一致或接近
- 前後端整合流程可正常運作
