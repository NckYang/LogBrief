# LogBrief：日誌壓縮與 MCP

將冗長的 Python 日誌整理成有原始行號、符合 token 預算的除錯證據，交給 agent 分析。使用標準 stdio MCP，可接到支援本機 MCP 的 agent。

- 合併重複進度與相同警告，保留出現次數。
- 保留所有可辨識的完整 Python traceback、第一個錯誤與相關前後文。
- 優先選取設定、資料欄位及指標變化，附上原始行號。
- 必要證據放不進預算時明確回報錯誤。

## 首次安裝

需要 Python 3.11 以上。在 repo 根目錄執行一次：

```powershell
python -m pip install -e ".[mcp]"
```

安裝套件與首次取得 tokenizer 字典需要網路。安裝與執行應使用同一個 Python。

## 本機壓縮示範

```powershell
python -m examples.compression_demo
```

直接顯示壓縮結果，並保存 `outputs/compressed.txt` 與 `outputs/report.json`。
範例日誌有 342 行，包含 300 筆進度、30 筆相同警告，以及 `KeyError: 'label'`。結果保留重複次數、L334 欄位線索、第一個錯誤 L335 與完整 traceback L336–L341。

## 讓 agent 使用 MCP

安裝完成後，在 agent 的 MCP 設定新增「本機／stdio」server，填入：

| 欄位 | 內容 |
|---|---|
| 名稱 | `logbrief` |
| Command | `python` |
| Arguments | `-m logbrief.mcp_server`（若欄位要求 JSON 陣列，填 `["-m", "logbrief.mcp_server"]`） |

若主機提供完整命令輸入欄，直接填入：

```text
python -m logbrief.mcp_server
```

啟用後對 agent 說：

> 請使用 logbrief MCP 的 compress_log 工具，壓縮 examples/training.log，token_budget 設為 1200；再根據回傳的 evidence 分析錯誤原因、修復方式與驗證步驟，引用原始行號。請實際呼叫 MCP 工具。



**使用 Codex 的捷徑：** repo 另附 [.codex/config.toml](.codex/config.toml)，信任專案並開啟新的 Codex 對話即可載入，省去手動新增 server。這是方便設定，工具本身不依賴 Codex。

## Gemini 診斷品質證明

[GEMINI_DIAGNOSIS.md](GEMINI_DIAGNOSIS.md) 收錄先前真實呼叫 Gemini 3.5 Flash-Lite 的壓縮輸入、完整回答、用量及品質核對，供助教直接檢閱。該次模型收到的壓縮證據與目前示範一致。

模型指出程式要求 `label`，但可見欄位為 `feature_1`、`feature_2`、`target`，並引用行號提出修復方向。這是單一合成案例的歷史實測，沒有真的執行修復，也不能代表一般診斷準確率。

## AI 協作紀錄

[AI_COLLABORATION.md](AI_COLLABORATION.md) 整理需求、AI 分工、開發迭代、驗證結果與最終交付決策，並區分歷史實驗及目前版本。

## 工具與範圍

MCP 提供 `compress_log`，輸入 `log_path` 或 `log_text`（擇一），可指定 `token_budget`、`context_lines`、`question`、`encoding`。回傳壓縮證據、統計及 traceback 範圍。

檔案限 repo 工作目錄內 UTF-8 的 `.log`／`.txt`，MCP 輸入最多 1,000,000 bytes。預設預算為 4000、前後文為 3、encoding 為 `cl100k_base`。
token 預算包含準備的系統指示、問題、日誌證據與 32 預留量；它是本機 tokenizer 的計數，不包含 agent 其他對話，也不保證等於 agent 模型實際用量。
主要支援 Python 純文字日誌；短日誌不保證縮短，選取規則也不能保證保留所有根因線索。程式不會執行修復。

## 報告與驗證證據

[完整報告](reports/LogBrief_HW2_Report.md) 說明目的、AI 協作、工程實作與結果。[證據索引](reports/evidence/README.md) 區分目前示範快照與歷史紀錄，並說明重現方式及限制。
