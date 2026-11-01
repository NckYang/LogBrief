# HW2 報告交付檔案

- `LogBrief_HW2_Report.docx`：本次補強後的完整 Word 報告，建議使用此檔繳交。
- `LogBrief_HW2_Report.md`：報告文字來源。
- `LogBrief_HW2_Report.html`：瀏覽器閱讀及列印版本。
- `LogBrief_Report_Package.zip`：完整報告、HTML、Markdown、AI 協作與 Gemini 診斷附件，以及報告引用的歷史證據與本次壓縮結果。
- `LogBrief_HW2_Report_Concise.*`：保留的舊精簡版，不是本次更新版本。
- `evidence/`：歷史實驗快照，不代表目前交付版本的新一輪測試。

本次保留作業的四大章節，補強問題背景、價值、設計取捨、AI 迭代、驗證口徑、診斷證據鏈、MCP 展示與限制。2026-11-01 重新執行壓縮示範，確認 4,429 → 526 tokens；未重新呼叫 Gemini，未重新執行歷史測試套件。

重新匯出：

```powershell
python -m pip install -r reports/requirements-report.txt
python reports/export_report.py
```

程式碼見 https://github.com/NckYang/LogBrief；私人 repo 需確保助教具備存取權。報告包不包含完整程式碼。歷史 47 項測試紀錄、原交付文字記載的 18 項核心測試與本次示範重跑，已在報告中分別說明。
