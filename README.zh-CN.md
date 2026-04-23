# Options Daily Report — 数据库

**阅读语言：** [English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md)

**Options** 移动应用的公开数据仓库。

本仓库仅包含我们期权分析流水线的**生成结果**。分析引擎本身为专有代码，
并未开源。

## 内容

```
reports/
  YYYY-MM-DD.md                 — 每日策略报告（Markdown）
  weekly_summary_YYYY-MM-DD.md  — 每周回顾与下周展望

dashboard/
  data.json                     — 最新的仪表板聚合数据
  weekly_summary.json           — 最新的周报聚合数据
  index.html                    — 静态仪表板查看器（GitHub Pages）

schemas/
  data.schema.json              — data.json 的 JSON Schema
  weekly_summary.schema.json    — weekly_summary.json 的 JSON Schema
```

## 更新时间

| 文件 | 频率 | 时间（UTC） |
|------|------|-------------|
| `reports/YYYY-MM-DD.md` | 周一至周五 | 13:20 |
| `reports/weekly_summary_*.md` | 周日 | 18:00 |
| `dashboard/*.json` | 每次日报/周报运行后 | 13:25 / 18:05 |

## 许可证

### 数据与报告 — **CC BY-NC 4.0**

您可以在**个人、非商业**用途下查看、分享、引用已发布的报告，前提是标注
来源（链接到 `options.laiyanlong.dev`）。商业分发、转售，或用于训练
AI/ML 模型需另外获得书面授权。

### 分析源代码 — **专有（版权所有）**

生成这些报告的源代码存放于私有仓库，不授权公开使用。方法论
（Black-Scholes 模型、CP 评分、OI 聚集分析、时机信号、AI 点评流水线）
属于专有技术。

## 免责声明

报告仅供**教育**与**信息**目的。内容不构成投资建议、买卖证券的要约，或
采用特定策略的推荐。期权交易具有重大亏损风险。在做任何投资决策前，请
咨询合法的财务顾问。

## 获取 App

Options 移动应用（iOS）目前为私人 Beta 阶段。即将在 App Store 上架。

---

© 2026 Yan Long Lai。版权所有。
