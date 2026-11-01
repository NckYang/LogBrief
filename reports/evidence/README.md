# 報告證據索引

此目錄只收錄報告引用的證據。歷史紀錄與目前版本的重現結果分開標示。

| 檔案 | 性質與核對方式 |
|---|---|
| [current_demo_report.json](current_demo_report.json) | 2026-11-01 報告修訂時，執行目前版本 `python -m examples.compression_demo` 產生的 `outputs/report.json` 快照。輸入為 repo 的 `examples/training.log`，預算 1200，使用 cl100k_base。可核對 4429 → 526 tokens、L335 與 traceback L336–L341。 |
| [selection_ablation.json](selection_ablation.json) | 舊版選取比較的摘要，保存三個案例的指定行與選取結果。原比較程式及完整輸入未包含於精簡交付，因此只能檢閱紀錄，不能僅憑此檔重現比較；也不代表診斷準確率。 |
| [unit-tests.txt](unit-tests.txt) | 舊完整開發版本的 47 項測試輸出，包含已移除功能。不是目前精簡版本的測試結果；原交付報告記載的 18 項核心測試也不是此檔。 |

重現目前示範，在專案根目錄執行：

```powershell
python -m pip install -e ".[mcp]"
python -m examples.compression_demo
```

新輸出位於 `outputs/`，該目錄不納入 Git；本目錄的 JSON 是固定快照。`omitted_records = 0` 表示各事件有原文或摘要代表，不表示全部原文逐字保留。Gemini 歷史診斷與 API 用量另見根目錄 `GEMINI_DIAGNOSIS.md`。
