---
name: pytestdeck-development
description: >-
  Standard end-to-end development workflow for PytestDeck. Use this skill when
  implementing GitHub issues, developing new features, fixing bugs, or adding tests.
  Covers issue intake, architecture boundary rules, branching, testing pyramid (unit,
  integration, acceptance, e2e), linting, build, and git commit standards.
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

## 3. 架構分層與實作規範 (Architecture & Boundaries)

嚴格遵守專案的領域驅動設計（DDD）分層與前後端職責劃分：

### 後端（Backend - Clean Architecture / DDD）
- **`backend/src/domain/`**：
  - 核心領域模型、純粹邏輯與設定實體（例如 `BehaveConfig`、`DirectoryNode`、`TestOutcome`）。
  - **禁忌**：不可依賴 FastAPI、Uvicorn、Subprocess I/O 或任何外部框架。
- **`backend/src/application/`**：
  - 應用程式 Use Cases（例如 `DiscoverTestsUseCase`）。負責編排領域物件。
- **`backend/src/infrastructure/`**：
  - 與作業系統、子進程、Pytest/Behave CLI 執行串流、檔案系統互動（例如 `runner_service.py`）。
- **`backend/src/api/`**：
  - FastAPI Route Handler 與 WebSocket 連線管理（例如 `/ws/run`、`/api/discover`）。

### 前端（Frontend - Vue 3 + xterm.js）
- **`frontend/src/composables/`**：
  - 集中管理狀態與 WebSocket 事件（例如 `useTestRunner.js`、`useTestTree.js`）。
  - 狀態變更應具備可預測性，避免在多個組件中直接 mutate 全域狀態。
- **`frontend/src/components/`**：
  - UI 展示層。樣式必須沿用專案定義之 CSS 變數（如 `--accent-blue`、`--bg-primary` 等），切勿使用任意 ad-hoc hardcoded 顏色。
- **終端機輸出處理**：
  - `TerminalView.vue` 透過 xterm.js 渲染串流 ANSI 與控制字元。注意游標控制碼（如 cursor-up `\x1b[{n}A`）在不同寬度下的表現。

---

## 4. 驗證與測試金字塔 (Testing & Verification Pipeline)

在任何程式碼提交前，必須通過對應層級的自動化驗收：

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
5. **前端建置驗證 (Frontend Build)**：
   ```bash
   make build-frontend
   ```
   - 確保 Vite 打包無報錯，靜態檔案正確輸出至 `backend/src/frontend_dist`。
6. **端到端測試 (E2E Tests)**（若改動涉及使用者互動流程）：
   ```bash
   make e2e-test
   ```

---

## 5. 提交與 PR 規範 (Git Commit Standards)

遵守 Conventional Commits 與 50/72 格式規範：

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

## 6. 開發檢核清單 (Developer Checklist)

在將任務回報為完成前，確認以下項目：
- [ ] 已詳讀 Issue 並解決所有 acceptance criteria
- [ ] 未更動無關檔案（維持乾淨 diff）
- [ ] 通過 `make lint`，無任何 warning 或 error
- [ ] 相關單元與驗收測試皆通過
- [ ] 若動到前端，已驗證 `make build-frontend`
- [ ] Commit 訊息符合規範並附上 Issue 編號
