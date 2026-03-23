# PLAN

## 階段一：拆出 Python.exe
- [x] 將 YOLO、Siamese、FAISS 整理成獨立 Python 服務
- [x] 固定 `/compare`、`/search`、`/embed` API 格式
- [ ] 驗證服務可在本機獨立啟動

## 階段二：建立 Go.exe
- [x] 用 Go 內嵌前端頁面
- [ ] 加入檔案上傳、參數驗證、錯誤處理
- [x] 啟動與監控 Python.exe
- [x] 代理轉送 API 請求

## 階段三：模型檔獨立化
- [ ] 將 `best.pt`、`best.pth`、`idx.faiss`、`meta.csv` 放到獨立資料夾
- [ ] 透過設定檔指定模型路徑
- [ ] 確認模型可替換而不用重新打包程式

## 階段四：整合與驗證
- [ ] 驗證比對結果與現行版本一致
- [ ] 驗證搜尋結果與現行版本一致
- [ ] 完成部署與啟動文件

## 現況
- [x] 盤點所有寫死的 Linux 路徑與相依點
- [x] 改成以專案目錄為基準的相對路徑
- [x] 加入 `PIGEON_DATA_ROOT` 方便 Windows 指定資料集位置
- [x] 更新 Flask 後端與前端說明
