# Fabricium — 技術提案書

**提案編號：** FB-PROP-001  
**版本：** v1.0（草案）  
**日期：** 2026-07-12  
**狀態：** 待審議

---

## 摘要

Fabricium 是一個 Python library，將 Hermes plugin 的通用管理功能（CLI 生命週期、bundled skills 安裝、Git 自我更新、狀態持久化）從 Caelterra 與 Jovaltus 兩個 plugin 中抽離，形成共用的基礎設施。任何新的 Hermes plugin 只需導入 Fabricium，即可一行完成 `hermes <plugin> setup|status|update` 的 CLI 註冊，專注於 plugin 獨有的業務邏輯。

---

## 目錄

1. [背景與問題](#1-背景與問題)
2. [設計哲學](#2-設計哲學)
3. [範圍界定：什麼進 Library，什麼留 Plugin](#3-範圍界定)
4. [架構設計](#4-架構設計)
5. [遷移路徑](#5-遷移路徑)
6. [開發規模估算](#6-開發規模估算)

---

## 1. 背景與問題

### 1.1 現狀

Uniterra 旗下目前有兩個 Hermes plugin：

| Plugin | 定位 | 獨有功能 |
|---|---|---|
| **Caelterra** | 團隊標準化工具 | 多 profile 互動式選擇器 |
| **Jovaltus** | 自動化開發管線 | `implement / verify / simplify` 三工具 + hooks |

兩個 plugin 各自獨立在 `__init__.py` 中實現了一套幾乎完全相同的 plugin 管理邏輯。`git_utils.py` 更是逐行複製。

### 1.2 重複範圍

對比兩個 plugin 的程式碼：

| 模塊 | 重疊度 | 說明 |
|---|---|---|
| Path helpers (`_get_global_hermes_home`, `_get_profiles_dir`) | 100% | 完全相同 |
| State management (`_load_state`, `_save_state`, `_set_profile_state`) | 95% | 僅 state filename 不同 |
| Interactive prompts (`_prompt_yes_no`) | 100% | 完全相同 |
| Bundled skills (`_is_skill_dir`, `_install_bundled_skills`, `_remove_stale_skills`) | 95% | 實質相同 |
| Profile/SOUL.md (`_ensure_profile`, `_apply_soul_md`) | 90% | 僅 profile 名稱不同 |
| CLI subcommands (`setup`, `status`, `update`, `update --check`) | 85% | 結構一致 |
| `register()` — `register_cli_command` / `register_skill` | 90% | 模式相同 |
| `git_utils.py` | 90% | jovaltus 版多 4 個函數 |

Caelterra 的 `__init__.py` 全長 726 行，其中約 500 行是通用管理邏輯。Jovaltus 全長 747 行，約 520 行是同一套邏輯的複本。

### 1.3 問題本質

這不是兩個 plugin 的問題，而是一個**架構模式缺失**的問題：

> Hermes 的 plugin 系統提供了 `register_cli_command`、`register_tool`、`register_skill` 等底層 API，但沒有提供任何 plugin 生命週期管理的上層抽象。每個 plugin 作者都必須從頭實現 `setup`、`status`、`update`、bundled skills 安裝、Git 自我更新、狀態持久化 — 這些與 plugin 業務邏輯完全無關的基礎設施。

Caelterra 的定位是「團隊標準化 plugin」— 意味著未來每個新專案都可能產生自己的 Hermes plugin。如果不解決這個重複問題，每增加一個 plugin，就要再複製一份 ~500 行的 boilerplate。

---

## 2. 設計哲學

### 2.1 核心命題

> **讓 plugin 作者只寫「這個 plugin 做什麼」，不寫「plugin 怎麼管理自己」。**

### 2.2 設計原則

**原則一：只抽「現在真的共用的部分」**

Fabricium 僅包含 Caelterra 和 Jovaltus 兩個 plugin 中實際重疊的程式碼。不預先設計只有一個 plugin 需要的功能，不為「未來可能」做抽象。

**原則二：Convention over Configuration**

提供合理的預設行為（單一 profile、標準路徑），允許必要時覆蓋。99% 的 plugin 不需要碰設定。

**原則三：Plugin 仍擁有完全的自主權**

Fabricium 是一個 library，不是一個 framework。Plugin 導入它，不是被它控制。任何 Fabricium 提供的行為都可以被 plugin 繞過或替換。

**原則四：向後相容遷移**

Caelterra 和 Jovaltus 遷移到 Fabricium 後，CLI 行為、state file 格式、用戶體驗保持不變。遷移是內部重構，不對外可見。

### 2.3 命名

**Fabricium** — 源自拉丁文 *fabrica*（工坊、鍛造場），後綴 *-ium* 表示場所。

- Caelterra（天 + 地）— 格局
- Jovaltus（朱庇特 + 高）— 權威與力量
- Fabricium（鍛造工坊）— 創造與構築

三者各據不同的詞源領域，構成 Uniterra 的 plugin 生態三角：Caelterra 定義團隊標準，Jovaltus 執行開發管線，Fabricium 提供兩者共用的基礎設施。

---

## 3. 範圍界定

### 3.1 進入 Fabricium（通用層）

| 模組 | 來源 | 說明 |
|---|---|---|
| `HermesPlugin` class | caelterra + jovaltus `__init__.py` | 封裝 plugin 生命週期：`register()`, `setup`, `status`, `update` |
| `git_utils` module | jovaltus 版本（較完整） | Git subprocess wrappers：fetch, pull, ahead/behind, diff, commit 等 |
| `state` module | 兩者合併 | JSON state 讀寫，支援 custom filename |
| `skills` module | 兩者合併 | Bundled skills 安裝、偵測、移除 stale |
| `prompts` module | 兩者合併 | TTY detection、`yes_no` prompt |

### 3.2 留在 Plugin（業務層）

| 留在 Caelterra | 留在 Jovaltus |
|---|---|
| 多 profile 互動式選擇器 | `implement` tool handler |
| Caelterra 專屬 skills | `verify` tool handler |
| Caelterra SOUL.md | `simplify` tool handler |
| | hooks (`post_tool_call`, `pre_llm_call`) |
| | Jovaltus 專屬 skills |
| | Jovaltus SOUL.md |

### 3.3 明確不納入

- Jovaltus 的 subagent 調度邏輯（`tools.py`, `schemas.py`, `state.py` 中的 task 狀態管理）— 這是 Jovaltus 的核心業務，不是通用基礎設施
- Caelterra 的多 profile 互動式選擇器 — 這是 Caelterra 獨有的 UX，不是所有 plugin 都需要
- 任何與特定 LLM provider / model 相關的邏輯

---

## 4. 架構設計

### 4.1 Package 結構

```
hermes-plugin-kit/                  # repo name (PyPI: fabricium)
├── pyproject.toml
├── src/
│   └── fabricium/
│       ├── __init__.py             # HermesPlugin class
│       ├── git_utils.py            # Git subprocess wrappers
│       ├── state.py                # JSON state management
│       ├── skills.py               # Bundled skill lifecycle
│       └── prompts.py              # Interactive prompt utilities
└── tests/
    ├── test_git_utils.py
    ├── test_state.py
    ├── test_skills.py
    └── test_plugin.py
```

### 4.2 核心 API：`HermesPlugin`

```python
from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="my-plugin",               # plugin 名稱（用於 CLI、state file）
    default_profile="my-profile",   # 預設 profile 名稱（None = 多 profile 模式）
    soul_md_path="SOUL.md",         # SOUL.md 路徑（相對 plugin 根目錄）
)

def register(ctx):
    # 一行註冊 setup / status / update CLI + bundled skills
    plugin.register(ctx)

    # 然後註冊 plugin 獨有的工具和 hooks
    ctx.register_tool(...)
```

### 4.3 `HermesPlugin.register(ctx)` 自動做什麼

1. 自動掃描 `skills/` 目錄，註冊所有 bundled skills
2. 註冊 `hermes <name> setup` — profile 建立、skills 安裝、SOUL.md 部署
3. 註冊 `hermes <name> status` — 顯示安裝狀態
4. 註冊 `hermes <name> update` — Git pull + skills 刷新 + stale 清理
5. 註冊 `hermes <name> update --check` — ahead/behind 檢查

### 4.4 Profile 模式

| 模式 | `default_profile` | 行為 |
|---|---|---|
| 單一 profile | `"my-profile"` | setup 直接安裝到指定 profile，status 只顯示一個 |
| 多 profile | `None` | setup 列出所有 profile 讓用戶選擇（caelterra 模式） |

### 4.5 遷移後 Caelterra 的 `register()` 範例

```python
from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="caelterra",
    default_profile=None,           # 多 profile 模式
)

def register(ctx):
    plugin.register(ctx)            # ← 取代 ~500 行 boilerplate
    # Caelterra 無其他獨有工具
```

### 4.6 遷移後 Jovaltus 的 `register()` 範例

```python
from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="jovaltus",
    default_profile="jovaltus-agent",
)

def register(ctx):
    plugin.register(ctx)            # ← 取代 ~520 行 boilerplate

    # Jovaltus 獨有的工具和 hooks
    ctx.register_tool(name="jovaltus_implement", ...)
    ctx.register_tool(name="jovaltus_verify", ...)
    ctx.register_tool(name="jovaltus_simplify", ...)
    ctx.register_hook("post_tool_call", hooks.on_post_tool_call)
    ctx.register_hook("pre_llm_call", hooks.on_pre_llm_call)
```

---

## 5. 遷移路徑

### Phase 1：建立 Fabricium 核心（本提案範圍）

1. 從 jovaltus 提取 `git_utils.py`（以 jovaltus 較完整版本為基礎）
2. 從兩者提取 `state.py`, `skills.py`, `prompts.py`
3. 實現 `HermesPlugin` class
4. 建立完整測試（65+ tests）

### Phase 2：遷移 Caelterra

1. 添加 `fabricium` 依賴到 `pyproject.toml`
2. 用 `plugin.register(ctx)` 替換 `__init__.py` 中的 ~500 行 boilerplate
3. 驗證：`hermes caelterra setup|status|update` 行為不變
4. State file 格式保持向後相容

### Phase 3：遷移 Jovaltus

1. 添加 `fabricium` 依賴
2. 用 `plugin.register(ctx)` 替換 `__init__.py` 中的 ~520 行 boilerplate
3. 刪除自己的 `git_utils.py`（改用 fabricium 的）
4. 驗證：所有 68 個現有測試仍然通過

### Phase 4：文件與發布

1. PyPI 發布 `fabricium`
2. 撰寫 plugin 開發者文件：「如何用 Fabricium 在 5 分鐘內建立一個 Hermes plugin」

---

## 6. 開發規模估算

| 項目 | 預估工作量 |
|---|---|
| `git_utils.py` — 提取 + 測試 | 1–2 小時 |
| `state.py` — 提取 + 測試 | 1 小時 |
| `skills.py` — 提取 + 測試 | 1 小時 |
| `prompts.py` — 提取 + 測試 | 0.5 小時 |
| `HermesPlugin` class — 組合上述模組 | 2 小時 |
| 整合測試 | 1 小時 |
| Caelterra 遷移 + 驗證 | 1 小時 |
| Jovaltus 遷移 + 驗證 | 1.5 小時 |
| PyPI 發布 + 文件 | 1 小時 |
| **合計** | **約 10 小時** |

---

> 從拉丁詞根 *fabrica*（鍛造場）：Fabricium 是所有 Uniterra Hermes plugin 的共同根基。
> Caelterra 定義團隊標準，Jovaltus 執行開發管線，Fabricium 提供它們站立的地基。
