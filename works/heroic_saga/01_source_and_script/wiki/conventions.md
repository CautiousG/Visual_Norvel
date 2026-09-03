# wiki 消化层规约（英雄志）

本层是对 `../source/`（epub + text/ 全文，只读原始）的**消化**，目标服务「小说→AI 视频改编」，不是通用读书笔记。仿 `D:\bt1sd1\sterling_jiang\LLM_wiki` 范式：raw → wiki（index + 分页 + `[[wikilinks]]` + YAML frontmatter）。

## 目录
```
source/            raw（只读）：英雄志.epub + text/vol00-22.md + text/index.md
wiki/
├── conventions.md 本文件（消化规约）
├── index.md       总索引
├── overview.md    全书主线活体综述
├── status.md      ★ 深挖任务追踪器 + 操作日志（每卷深度状态）
├── candidates.md  ⭐ 可改编高光段落清单（评分+定位）→ 选段登记表
├── timeline.md    景泰纪年时间线（按需）
├── volumes/       每卷梗概 volNN.md（导航层）
├── characters/    人物页
├── factions/      势力页
├── locations/     场景/地点页
├── events/        关键事件页
├── themes/        思辨母题页
└── _templates/    各类型页模板
```

## 概念类型（page type）
character 人物 / faction 势力 / location 场景 / event 事件 / theme 母题 / segment 候选段落（暂存 candidates.md）/ volume 卷梗概 / overview / index。
term 名物·招式：优先级低，需要时再建 `terms/`。

## 消化深度分级
- **L0 未读**
- **L1 轻量**：写该卷梗概 volNN.md；把涉及的人物/势力/场景/事件建 **stub 占位页**（只填已知，不臆造）。
- **L2 深挖**：读 `source/text/volNN.md` → 逐章梗概、补全实体页、抽事件、评候选段落，并**精确定位引文**（写明 volNN.md 的章名/段落）。

深挖是**增量**的：用户说"要做第 X 卷 / 某场景 / 某人物"，就把相关范围升到 L2，其余保持 L1/L0。每次深挖后更新 `index.md` 并在 `status.md` 追加日志。

## 架构决策（2026-09-02 review 锁定）
1. **启动层 vs 按需**：启动只做 `overview` + 四主角骨架卡 + `candidates`（candidates 用 **grep 把高光段落定位到卷/章**，不逐卷通读）。**每卷梗概(`volumes/`) / `events/` / `factions/` / 配角卡 一律"深挖某段时按需建"**，不预先铺——对齐手册"只做 1~3 段"，别先修一座书库。
2. **真值边界**：`wiki/characters/` = 原著提炼的理解/参考；`02_characters/` = 生产锁定的定妆卡(prompt+参考图)。后者从前者派生，锁定后**以 02 为准**。人物只建四主角 + 选中段落涉及的配角，不铺全书角色。
3. **Obsidian vault = 每部作品根**(`works/heroic_saga/`)，避免多部间 `[[同名]]` 串味。不引入 `graph/` 与 `tools/`，用 Obsidian 自带关系图。
4. **文件名**：目录英文、笔记中文名（本层不碰媒体工具，`[[链接]]` 可读）。
5. **通用件**(`conventions.md` / `_templates/` / `_convert.py`)通用但**暂留作品内**，第二部开工时再提炼进 `_shared/`（见工作台 README backlog）。

## Frontmatter（每页顶部必带）
```yaml
---
title: 卢云
type: character            # character|faction|location|event|theme|segment|volume|overview|index
aliases: []                # 别名/字号
tags: []
depth: L1                  # L0|L1|L2
video_relevance: high      # high|mid|low  对改视频的价值
sources: [vol02]           # 支撑的卷（volNN）
first_appear: vol02 第一章  # 首次出场（人物/势力/场景）
status: stub               # stub|draft|final
last_updated: 2026-09-02
---
```

## 约定
- **目录名英文，笔记文件名用中文**（如 `characters/卢云.md`）——本层是 markdown/Obsidian，不进 ffmpeg/脚本，中文名让 `[[卢云]]` 链接可读；若日后要全 ASCII，改 slug 即可。
- 交叉引用一律 `[[标题]]`；关键术语首次出现加粗。
- **不臆造**：拿不准的写进各页「待核/待深挖」，标 `status: stub`，深挖时核对 `source/text` 再落实。
- 引文定位格式：`vol05.md › 第三章 XXX`（必要时附首句）。
