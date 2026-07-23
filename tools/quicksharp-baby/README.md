# 快晰寶貝｜QuickSharp Baby

一個住在電腦裡、讓人眼高速比較照片清晰度的輕量巡圖器。

## v1.6 穩定版

- 使用 Ubuntu 原生資料夾選擇器，保留路徑輸入欄
- 匯入只讀選定的單一資料夾，不遞迴混入子層
- JPG／RAW／TIF 格式篩選視圖
- 匯入資料夾後優先進入 JPG 視圖
- JPG 視圖完全不解碼 RAW，也不建立 RAW 縮圖
- 切到 RAW 時只解碼目前這一張，其他 RAW 不預讀
- RAW 縮圖優先借用同名 JPG，避免批次解碼 RAW
- 同名 JPG／RAW／TIF 切換時保持相同倍率與比例座標
- 刪除 RAW 後，若有同名 JPG，自動回到該 JPG 繼續巡圖
- 讀取單一資料夾內的 JPG、JPEG、TIF、TIFF 與常見 RAW
- 全螢幕主影像，預設 300%
- `←`／`→` 切換上一張、下一張
- 滑鼠拖曳主圖，滾輪每格調整 25% 倍率
- 可移動的全圖導覽器
- 底部縮圖列與控制列已併入主視窗，縮小時不會殘留
- `Delete` 或垃圾桶按鈕將目前檔案移到系統垃圾桶

## 格式切換

底部控制區有：

```text
JPG | RAW | TIF
```

配對規則採用完全相同的檔名主體，例如：

```text
IMG_001.JPG
IMG_001.ARW
IMG_001.TIF
```

按下 RAW 時，只有目前 JPG 有同名 RAW 才會切換，避免跳到不相關照片。

## 目前版本的性質

這是目前已由實機驗收的穩定版本。後續若重建原生版，預定評估 GTK4、libvips 與 LibRaw。

目前原型使用：

- Python + Tkinter：介面
- Pillow：JPG／TIFF 顯示
- ImageMagick：RAW 解碼，僅在使用者切到 RAW 時呼叫
- Send2Trash：移到系統垃圾桶

## 執行

```bash
python3 -m pip install -r requirements.txt
./run.sh
```

也可以直接指定資料夾：

```bash
./run.sh /path/to/photos
```

## 快捷操作

- `→`：下一張
- `←`：上一張
- `Delete`：目前照片移到垃圾桶
- `Esc`：第一次離開全螢幕，第二次關閉
- 主圖拖曳：移動畫面
- 主圖滾輪：放大／縮小
- 導覽器內拖曳：移動到照片對應位置
- 導覽器標題拖曳：移動導覽器

## 已知限制

- 為避免 Ubuntu 縮小後殘留獨立面板，底部列採單一視窗深灰透明感外觀；Tkinter 不提供子元件真正 alpha。
- RAW 目前由 ImageMagick 解碼，速度與支援度依系統安裝內容而定。
- 巨型 TIFF 尚未改為區塊讀取。
- JPG／RAW／TIF 配對目前要求完全相同的檔名主體。
