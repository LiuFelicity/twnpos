# Batch Table OCR（去紅章版）使用說明

## 1. 安裝系統需求
- 安裝 Tesseract OCR：
  - macOS（Homebrew）：`brew install tesseract`
  - Windows：下載安裝程式（記得勾選語言包）
  - Linux（Debian/Ubuntu）：`sudo apt-get install tesseract-ocr`
- 建議安裝語言包：繁體中文 `tesseract-ocr-chi-tra`
- 若要支援 PDF：安裝 poppler（macOS：`brew install poppler`）

## 2. 安裝 Python 套件
```bash
pip install -r requirements.txt
```

## 3. 放置檔案
- 建立資料夾 `scans`，把 100 份表單（JPG/PNG/PDF）放入。

## 4. 執行
```bash
python batch_table_ocr.py --input ./scans --output ./csv_out
```
- 產出會在 `csv_out/`，每一張對應一個 `.csv`。

## 5. 原理重點
- 先用 HSV 遮罩抓出紅色印章，OpenCV Inpaint 補洞（不讀入紅字）。
- 自動找表格線（水平/垂直膨脹侵蝕），切成儲存格。
- 逐格以 Tesseract OCR（預設 `chi_tra+eng`，系統沒有則退回 `eng`）。
- 匯出 CSV（UTF-8-SIG），可直接用 Excel/Google Sheets 開啟。

## 6. 小技巧
- 若表格線太淡，可先把掃描解析度提高到 300 DPI 以上。
- 如果是固定版型，成效會更好。必要時可在程式內調整：
  - `detect_table_lines` 的 kernel 長度
  - `extract_cells_from_grid` 的大小和列群組閾值
- 如果你要把「差額」欄位做數字清洗（移除逗號/括號→負號），我可以再加後處理規則。
