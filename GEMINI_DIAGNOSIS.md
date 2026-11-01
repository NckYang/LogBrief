# 呼叫Gemini API診斷品質實測紀錄

本附件整理先前真實 MCP → LogBrief → Gemini 的成功呼叫，供助教直接檢閱。

## 案例與模型

- 模型：`gemini-3.5-flash-lite`，provider：`gemini`。
- 原始日誌：`examples/training.log`，342 行人工合成訓練日誌。
- 任務：根據壓縮日誌說明可能原因、處理方式與驗證步驟。


## 用量與證據保留

| 項目 | 實測值 |
|---|---|
| 第一個錯誤 | L335 |
| Traceback | L336–L341，完整保留 |
| 重複摘要 | 300 筆進度、30 筆警告 |
| 本機估算的完整提示詞 tokens | 4429 |
| 本機估算的壓縮提示詞 tokens | 526 |
| Gemini 原生輸入計數／實際輸入 | 575／575 tokens |
| 輸入預算檢查 | 575 + 32 預留 = 607 ≤ 1200 |
| 生成輸出 | 663 tokens |
| 回答截斷 | 否 |
| 生成請求耗時 | 2.827 秒 |



## 模型收到的壓縮日誌證據

```text
[L1] 2026-10-31 09:00:00 INFO Python=3.14 device=cpu

[L2] 2026-10-31 09:00:01 INFO Loading training configuration

[PROGRESS x300; first=L3; last=L331; includes any exact excerpts]
[L3] INFO Step 1/300 preprocessing samples
[L331] INFO Step 300/300 preprocessing samples

[WARNING x30; first=L13; last=L332; includes any exact excerpts]
[L13] WARNING Dataset cache is unavailable; using source files

[L332] WARNING Dataset cache is unavailable; using source files
[L333] INFO Opening data/train.csv
[L334] INFO Available columns: feature_1, feature_2, target
[L335] ERROR Requested label column 'label' does not exist
[L336] Traceback (most recent call last):
[L337]   File "train.py", line 42, in <module>
[L338]     train(config)
[L339]   File "train.py", line 18, in train
[L340]     labels = frame["label"]
[L341] KeyError: 'label'
[L342] INFO Training aborted; no model checkpoint was written
```

## Gemini 完整原始回答



根據提供的日誌內容，以下是問題分析、可能原因、修復步驟與驗證方式：

### 1. 觀察到的問題與證據 (Observed Problem and Evidence)
* **資料集欄位與程式碼預期不符**：
  * 程式嘗試從讀取的資料集中取得名為 `'label'` 的欄位 [L340]。
  * 觸發了 `KeyError: 'label'` [L341]，導致訓練中止並印出 Traceback [L336-L341]，且未寫入任何模型檢查點 [L342]。
* **實際存在的欄位**：
  * 日誌顯示 `data/train.csv` 被開啟 [L333]，其實際可用欄位為 `feature_1`、`feature_2`、`target` [L334]，其中並沒有 `'label'`，而是使用了 `'target'`。

---

### 2. 可能原因排名與不確定性 (Likely Causes Ranked with Uncertainty)
1. **程式碼中的標籤欄位名稱設定錯誤 (高信心)**：
   * 程式碼 (`train.py` 第 18 行) 直接寫死了硬編碼的欄位名稱 `"label"` [L340]，但實際 CSV 檔案中的目標欄位名稱為 `"target"` [L334]。
2. **訓練設定檔 (Configuration) 參數不匹配 (中等信心)**：
   * 設定檔中可能定義了目標欄位為 `label`，但資料集本身使用的是 `target`，導致程式讀取錯誤的鍵值。

---

### 3. 具體修復步驟 (Concrete Repair Steps)
* **方法 A：修改程式碼**
  * 打開 `train.py` 並找到第 18 行左右的程式碼 [L339-L340]。
  * 將讀取標籤的鍵值由 `"label"` 改為實際存在的 `"target"`：
    ```python
    # 修改前 (範例)
    labels = frame["label"]

    # 修改後
    labels = frame["target"]
    ```
* **方法 B：修改資料集欄位或設定檔**
  * 若程式碼不宜更動，請檢查訓練設定檔或將 `data/train.csv` 中的 `target` 欄位名稱重新命名為 `label`。

---

### 4. 驗證指令/檢查與缺少資訊 (Verification Commands/Checks and Missing Information)
* **驗證指令**：
  * 重新執行訓練腳本並觀察日誌：
    ```bash
    python train.py
    ```
  * 確認日誌中不再出現 `KeyError: 'label'` 與 Traceback，並且能順利通過資料載入與後續的訓練步驟。
* **缺少的資訊**：
  * 缺少 `train.py` 的完整設定檔內容，無法完全排除是否為設定檔參數傳遞錯誤。

## 品質核對與限制

| 面向 | 核對結果 |
|---|---|
| 核心錯誤 | 正確指出程式存取 `frame["label"]`，並在 L341 發生 `KeyError` |
| 證據引用 | L334 可核對現有欄位，L340–L341 可核對欄位存取與例外 |
| 修復方向 | 提出統一欄位名稱或設定，與可見錯誤相符 |
| 驗證步驟 | 建議重跑並檢查例外是否消失；沒有宣稱已修復成功 |
| 回答不足 | 把 `target` 視為應使用的標籤欄位，仍須確認資料語意；設定檔不匹配只是推測 |

此單一成功案例支持「壓縮後仍可辨識這個錯誤」，不能證明所有日誌的診斷品質或宣稱壓縮提高準確率。

## 原始 API 回報用量

```json
{
  "promptTokenCount": 575,
  "candidatesTokenCount": 663,
  "totalTokenCount": 1238,
  "promptTokensDetails": [
    {
      "modality": "TEXT",
      "tokenCount": 575
    }
  ],
  "serviceTier": "standard"
}
```
