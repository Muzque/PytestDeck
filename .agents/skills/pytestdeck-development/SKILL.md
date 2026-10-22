---
name: pytestdeck-development
description: >-
  Standard end-to-end development workflow for PytestDeck. Use this skill when
  implementing GitHub issues, developing new features, fixing bugs, or adding tests.
  Covers issue intake, branching, test-first / TDD use case preparation, architecture
  boundary rules, testing pyramid (unit, integration, acceptance, e2e), linting,
  build, and git commit standards.
---

# 🚀 PytestDeck Development Workflow Guide

本指南定義了在 PytestDeck 專案中處理 GitHub Issue、新增功能或修復問題時的標準端到端開發流程與規範。

---

## 1. 需求與 Issue 剖析 (Issue Intake & Analysis)

在動手寫程式碼之前，必須先完整掌握目標與邊界：

1. **讀取 Issue 內容**：
   - 使用 GitHub API 或 CLI 獲取 Issue 的完整資訊。
   - 審視四大核心區塊：
     - **背景與現象 (Background & Symptoms)**：使用者目前遇到了什麼問題。
     - **根因分析 (Root Cause)**：造成該現象的底層機制（例如 subprocess tty 寬度、WebSocket message 格式、Reactive state 更新時機等）。
     - **影響範圍 (Impact Scope)**：明確劃分「會動到的檔案」與「不在範圍內」的項目。
     - **驗收準則與 Action Items (Acceptance Criteria & Action Items)**：完成的驗收條件與待確認 (TBD) 事項。
2. **釐清不明確與 TBD 項目**：
   - 若 Issue 內有標示 `TBD`、潛在副作用或架構分歧，**在實作前必須先向 User 提出並確認決策**。

---

## 2. 分支管理策略 (Branching Strategy)

確認需求後，建立獨立的分支進行開發：

1. 確保 `main` 分支乾淨且為最新狀態：
   ```bash
   git checkout main
   git pull origin main
   ```
2. 建立語意化開發分支：
   - 功能新增：`feat/issue-<num>-<short-slug>`（例如：`feat/issue-8-stream-acceptance-steps`）
   - 問題修復：`fix/issue-<num>-<short-slug>`（例如：`fix/issue-2-directory-tree-running-color`）

---

## 3. 測試先行與 Use Case 準備 (Test-First & Use Case Preparation)

**在動手修改或撰寫實作程式碼 (Production Code) 之前，必須先撰寫測試案例 (Test Cases)**，嚴格落實 Test-First / TDD 原則：

1. **檢驗現有 Use Case 與目標專案資源**：
   - 檢查 `sample-target-repo` 與 PytestDeck 測試套件中是否已經存在能夠重現問題、或足以驗證新功能的 Use Case。
   - **重要**：若 `sample-target-repo` 根本沒有該功能的使用場景（例如缺乏特定測試結構、logger 配置、非同步測試、或 step 定義），**絕對不可直接通靈實作程式碼**。
2. **實際觀測 CLI 原始輸出與時間尺度 (Raw Output & Pacing Inspection)**：
   - **禁止假設 CLI 輸出格式**：凡涉及解析 `stdout` / WebSocket 串流（如 `pytest -v -s`、`log_cli = true`、fixture teardown、自訂 print banner 或 `behave` 步驟），必須先在 `sample-target-repo` 實際執行 CLI 指令，觀察真實多行輸出與邊界案例後再設計解析器。
   - **確保人類肉眼可觀測的時間尺度 (Human-Observable Pacing)**：凡涉及「執行中狀態 (running state)」、「即時進度更新 (on-the-fly updates)」或動畫回饋的功能，若 `sample-target-repo` 測試在 `< 1ms` 內瞬間跑完，人類在瀏覽器一個 frame (`16ms`) 內根本看不到變化。必須先在 `sample-target-repo` 補齊多檔案、多層目錄、多 Class 以及合理的每項測試延遲（如 `0.1s`–`0.25s`），確保肉眼與自動化測試皆能清楚觀測逐項狀態轉換。
3. **建立/補齊或更新測試案例與 Use Case**：
   - **在目標專案建立真實情境**：先在 `sample-target-repo` 撰寫符合需求的 feature 檔案、step definitions、單元或整合測試（例如新增 `tests/acceptance/features/<usecase>.feature`、設定 `pytest.ini` / `behave.ini` 等）。
   - **在專案端新增或更新測試（特別是 E2E 測試）**：
     - 在 `backend/tests/` 撰寫或更新單元/整合/驗收測試，定義期望的行為、API 規格或 WebSocket 訊息協定。
     - **審視並同步更新 `frontend/e2e/app.spec.js`**：每處理一個涉及前端或全端互動的 Issue，必須檢視現有的 E2E 測試是否受新行為或 `sample-target-repo` 資料變動影響，並**修改既有 E2E 測試或新增專屬 E2E 測試案例**以完整對應 Issue 的 Acceptance Criteria。
4. **驗證測試可重現問題 (Red Phase)**：
   - 執行剛剛建立的測試（注意：跑 Playwright E2E 前必須先執行 `npm run build` / `make build-frontend`），確認該測試能成功跑起並重現錯誤，或是明確指出缺少的功能。
5. **進入實作修復 (Green Phase)**：
   - 只有在測試案例與驗證情境皆已就緒並能精準捕捉預期行為後，才開始編寫業務邏輯與架構程式碼。

---

## 4. 架構分層與實作規範 (Architecture & Boundaries)

嚴格遵守專案的領域驅動設計（DDD）分層與前後端職責劃分：

### 後端（Backend - Clean Architecture / DDD）
- **`backend/src/domain/`**：
  - 核心領域模型、純粹邏輯與設定實體（例如 `BehaveConfig`、`DirectoryNode`、`TestOutcome`）。
  - **禁忌**：不可依賴 FastAPI、Uvicorn、Subprocess I/O 或任何外部框架。
- **`backend/src/application/`**：
  - 應用程式 Use Cases（例如 `DiscoverTestsUseCase`）。負責編排領域物件。
- **`backend/src/infrastructure/`**：
  - 與作業系統、子進程、Pytest/Behave CLI 執行串流、檔案系統互動（例如 `runner_service.py`、`output_splitter.py`）。
- **`backend/src/api/`**：
  - FastAPI Route Handler 與 WebSocket 連線管理（例如 `/ws/run`、`/api/discover`）。

### 前端（Frontend - Vue 3 + xterm.js）
- **`frontend/src/composables/`**：
  - 集中管理狀態與 WebSocket 事件（例如 `useTestRunner.js`、`useTheme.js`、`useTooltip.js`、`useSidebarResize.js`）。
  - 狀態變更應具備可預測性，避免在多個組件中直接 mutate 全域狀態。
  - **全路徑與選取矩陣檢查 (Entry-Point & Selection Matrix)**：
    - 任何與測試執行或樹狀選取相關的邏輯，必須同時涵蓋：
      1. `0` 個節點選取（點擊 `Run Selected (0)` 代表執行當前 Active Suite 全部測試）
      2. 選取單一/多個目錄 (`directory`)、檔案 (`file`)、類別 (`class`)、或單一函式 (`function` / `scenario`)
      3. 不同測試套件切換（`unit`、`integration`、`acceptance`）與檔案預設收合 (`isOpen = false`) vs. 展開狀態。
  - **背景事件與生命週期防呆 (Lifecycle & Race-Condition Guards)**：
    - 瀏覽器視窗切換會觸發 `window` 的 `focus` 事件（例如 `loadStoredMethodOutputs` 重新拉取舊結果）、或 Vue `watch` 觸發 API 請求。凡是在 `isRunning.value === true` 期間可能覆寫即時狀態的背景 fetch，**必須加上 `if (isRunning.value) return` 防護**，避免使用者切換視窗時把執行中狀態洗掉。
- **`frontend/src/components/`**：
  - UI 展示層。樣式必須沿用專案定義之 CSS 變數（如 `--accent-blue`、`--bg-primary` 等），切勿使用任意 ad-hoc hardcoded 顏色。
- **終端機輸出處理**：
  - `TerminalView.vue` 透過 xterm.js 渲染串流 ANSI 與控制字元。注意游標控制碼（如 cursor-up `\x1b[{n}A`）在不同寬度下的表現。

---

## 5. 驗證與測試金字塔 (Testing & Verification Pipeline)

在任何程式碼提交或回報「完成」前，必須通過對應層級的自動化驗收：

1. **程式碼檢查與排版 (Linting)**：
   ```bash
   make lint
   ```
   - 後端：`Ruff` 檢查與修正。
   - 前端：`ESLint` 檢查。
2. **單元測試 (Unit Tests)**：
   ```bash
   make unit-test
   ```
   - 針對有修改的領域邏輯、工具函式補齊 1-to-1 單元測試（`backend/tests/unit/`）。
3. **整合測試 (Integration Tests)**：
   ```bash
   make integration-test
   ```
   - 驗證 API 與 WebSocket 訊息格式與通訊協議。
4. **驗收測試 (BDD Acceptance Tests)**：
   ```bash
   make acceptance-test
   ```
   - 或指定 feature：
     ```bash
     make acceptance-test FEATURES="tests/acceptance/features/<target>.feature"
     ```
5. **前端建置驗證與靜態產物同步 (Frontend Build — 每次前端修改與 E2E 測試前必跑)**：
   ```bash
   make build-frontend
   ```
   - **關鍵原因**：本機運行的 PytestDeck 伺服器 (`uvicorn app:app --port 9388`) 與 Playwright E2E 測試皆直接從 `frontend/dist` 提供靜態檔案，而非 Vite HMR dev server。**只要改動任何 `frontend/src/` 檔案，在執行 Playwright E2E 測試或請使用者檢視 UI 前，必定要先執行 `make build-frontend`（或 `cd frontend && npm run build`）更新 `frontend/dist`**，否則 Playwright 與使用者的瀏覽器只會載入舊版 bundle。
6. **端到端測試 (E2E Tests)**（凡改動涉及前端或使用者互動流程必跑）：
   ```bash
   make e2e-test
   ```
   - **新增或調整 E2E 測試**：針對 Issue 的需求，必須在 `frontend/e2e/app.spec.js` 新增對應的 E2E 測試案例或調整既有案例，確保覆蓋實際使用者操作組合（例如：未勾選直接執行全部 `Run Selected (0)`、勾選子節點執行、展開/收合節點、切換不同 Suite、視窗 `focus` 事件、中途點擊 Stop 等）。
   - **注意本機伺服器狀態 (`reuseExistingServer: true`)**：`playwright.config.js` 預設重用 `9388` port 上的既有伺服器。若修改了 `backend/src/` 且本機伺服器未開啟 `--reload`，執行 E2E 前必須先重啟伺服器（如 `make stop && make dev`），確保後端載入最新程式碼。

---

## 6. 提交與 PR 規範 (Git Commit Standards)

遵守 `git-commit` 技能規範、Conventional Commits 與嚴格的 **50/72 格式規範**：

- **尊重 Staged 狀態**：只提交已 stage 的檔案；若尚無 staged 檔案，先向使用者確認要打包哪些變更（例如拆分為原子化 commits），切勿未經確認直接執行 `git add .` 或 `git add -A`。
- **50/72 長度限制**：Subject line 嚴格 `<= 50` 字元；Body 每行嚴格 `<= 72` 字元。

### Commit Message 結構
```text
<type>(<scope>): <subject line <= 50 chars>

<Detailed explanation body wrapped at 72 characters explaining why
the change was made, what trade-offs were considered, and how the
behavior was adjusted.>

Refs #<issue_number>
```

### Type 清單
- `feat`: 新增功能
- `fix`: 修復 bug
- `refactor`: 重構（不影響外部行為）
- `test`: 新增或調整測試案例
- `docs`: 文件更動
- `style`: 程式碼格式調整（不影響邏輯）
- `chore`: 建置腳本、依賴套件調整

---

## 7. 開發檢核清單 (Developer Checklist)

在將任務回報為完成前，確認以下項目：
- [ ] 已詳讀 Issue 並解決所有 acceptance criteria
- [ ] 測試先行：已在動手寫程式碼前，先在目標專案 (`sample-target-repo`) 或測試套件建立對應的 test case / use case，且測試時間尺度足以讓人類肉眼在 UI 上清楚觀測
- [ ] 若涉及串流輸出解析，已實際執行並檢視 `sample-target-repo` 各套件 (`unit` / `integration` / `acceptance`) 的真實 CLI 輸出格式
- [ ] 若涉及前端狀態，已檢查全選/未選 (`Run Selected (0)`)、局部勾選、跨套件切換、以及 `window` `focus` 等非同步請求是否會覆蓋即時狀態
- [ ] 已在 `frontend/e2e/app.spec.js` 新增或調整對應的 E2E 測試案例，且全數通過
- [ ] 未更動無關檔案（維持乾淨 diff）
- [ ] 通過 `make lint`，無任何 warning 或 error
- [ ] 相關單元、整合、驗收與 E2E 測試皆通過
- [ ] **若動到前端，最後一步已執行 `make build-frontend` 更新 `frontend/dist`，確保本機伺服器提供最新畫面**
- [ ] Commit 訊息符合 50/72 規範並附上 Issue 編號
