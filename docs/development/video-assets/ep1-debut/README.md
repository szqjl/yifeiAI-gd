# 视频素材 · 第 1 期「掼蛋AI诞生到首秀」

横屏 **16:9（1920×1080）**，面向不懂 AI 的观众。

## 快速开始（打开幻灯片）

README 里 Ctrl+单击 `slides.html` 在 Cursor 里**常常打不开**（会在编辑器里预览或链接失效）。请用下面任一方式：

| 方式 | 操作 |
|------|------|
| **推荐** | 资源管理器中双击同目录下的 **`OPEN_SLIDES.bat`** → 用默认浏览器打开 |
| 资源管理器 | 进入本文件夹，**双击 `slides.html`** |
| 浏览器地址栏 | 粘贴：`file:///D:/guandanscore/YiFeiAI-GD/docs/development/video-assets/ep1-debut/slides.html` |
| Cursor 侧栏 | 在文件树点 **`slides.html`** → 右键 → **Reveal in File Explorer** → 双击打开 |

打开后：

1. **F11** 全屏
2. **→ / ← / 空格** 翻页（共 **16** 页）
3. 录屏分辨率：**1920×1080**

## 文件清单

| 文件 | 用途 |
|------|------|
| [`slides.html`](file:///D:/guandanscore/YiFeiAI-GD/docs/development/video-assets/ep1-debut/slides.html) | **主素材**：16 页幻灯片（浏览器打开，勿依赖 Ctrl+单击） |
| [`OPEN_SLIDES.bat`](file:///D:/guandanscore/YiFeiAI-GD/docs/development/video-assets/ep1-debut/OPEN_SLIDES.bat) | 一键用浏览器打开 slides.html |
| [`images/cover-ep1-debut.png`](images/cover-ep1-debut.png) | B 站封面 / 片头定帧 |
| [`images/card-score-ep1.png`](images/card-score-ep1.png) | 首秀成绩单（**3 局**） |
| [`images/compare-knowledge-random.png`](images/compare-knowledge-random.png) | 知识库 vs 随机策略 |

**Canvas 数据看板**（IDE 侧边打开后录屏）：

[guandan-ai-ep1-debut.canvas.tsx](file:///C:/Users/Jennifer/.cursor/projects/d-guandanscore-YiFeiAI-GD/canvases/guandan-ai-ep1-debut.canvas.tsx)

## 幻灯片目录

| 页 | 标题 |
|----|------|
| 1 | 封面 |
| 2 | 是不是真 AI 在打 |
| 3 | 从「双上计分王」说起 |
| 4 | 我以为：喂知识就会 |
| 5 | 转折：要先能上桌 |
| 6 | 11-21 第一次 Git |
| 7 | 客户端架构（简图） |
| 8 | 一局怎么出牌 |
| 9 | 11-24 首秀 |
| 10 | 战绩 victoryNum |
| 11 | 能力评分 |
| 12 | 出牌习惯（牌型占比） |
| 13 | 随机决策六行代码 |
| 14 | 知识库 vs 首秀现实 |
| 15 | 时间轴总览 |
| 16 | 里程碑与下期 |

## 数据真源

- [`../../AI首秀分析报告.md`](../../AI首秀分析报告.md)（Git 原文为 10 局；本视频素材按 **3 局** 展示）
- Git：`9fdc5f1`（立项）、`2d3dda1`（v0.1 首秀）
- 代码：`src/communication/basic_client.py`

## 还需你实拍

- 双上计分王小程序界面（5–10 秒）
- （可选）四客户端连离线服批跑，证明「真 AI 在打」
