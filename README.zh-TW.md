# Options Daily Report — 資料庫

**閱讀語言：** [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md)

**Options** 行動應用程式的公開資料儲存庫。

此儲存庫僅包含我們選擇權分析管線產出的**最終資料**。分析引擎本身是專有
程式碼，並未開源。

## 內容

```
reports/
  YYYY-MM-DD.md                 — 每日策略報告（Markdown）
  weekly_summary_YYYY-MM-DD.md  — 每週回顧與下週展望

dashboard/
  data.json                     — 最新的儀表板整合資料
  weekly_summary.json           — 最新的週報整合資料
  index.html                    — 靜態儀表板檢視器（GitHub Pages）

schemas/
  data.schema.json              — data.json 的 JSON Schema
  weekly_summary.schema.json    — weekly_summary.json 的 JSON Schema
```

## 更新時程

| 檔案 | 頻率 | 時間（UTC） |
|------|------|-------------|
| `reports/YYYY-MM-DD.md` | 週一至週五 | 13:20 |
| `reports/weekly_summary_*.md` | 週日 | 18:00 |
| `dashboard/*.json` | 每次日報/週報執行後 | 13:25 / 18:05 |

## 授權

### 資料與報告 — **CC BY-NC 4.0**

您可以在**個人、非商業**用途下檢視、分享、引用已發布的報告，前提是附上
來源標示（連結至 `options.laiyanlong.dev`）。商業散佈、轉售，或用於訓練
AI/ML 模型需另外取得書面授權。

### 分析原始碼 — **專有（版權所有）**

產生這些報告的原始碼存放於私有儲存庫，並未授權公開使用。方法論
（Black-Scholes 模型、CP 評分、OI 聚集分析、時機訊號、AI 評論管線）屬於
專有技術。

## 免責聲明

報告僅供**教育**與**資訊**目的。內容不構成投資建議、買賣證券的邀約，或
採用特定策略的推薦。選擇權交易具有重大虧損風險。在做任何投資決策前，請
諮詢合法的財務顧問。

## 取得 App

Options 行動應用程式（iOS）目前為私人 Beta 階段。即將於 App Store 上架。

---

© 2026 Yan Long Lai。版權所有。
