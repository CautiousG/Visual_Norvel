# Visual_Norvel — AI 视频改编工作台

多部作品共用的工作台。**路径一律用英文/ASCII**（避免 ffmpeg、剪辑软件、脚本、git 对中文路径的偶发编码 bug）；**文件正文照常用中文**。

## 目录规则（判据一句话）
> **「下一部作品还用得上吗？」用得上 → `_shared/`；换一部就作废或必须重做 → `works/<某部>/`。**

- **共享（一份，反复用）**：方法论、风格模板、提示词片段、音效/BGM、朝代考据、空白模板、工具账号。
- **隔离（每部专属）**：⚠️ 原著文本（版权敏感，必须隔离）、剧本分镜、角色卡与定妆图、生成素材、配音、成片。

## 目录对照

```
Visual_Norvel/
├── README.md                     本文件
├── _shared/                      共享区（跨作品复用）
│   ├── _templates/               空白模板 —— 开新作时整份复制到 works/<新作>/
│   ├── style_presets.txt         风格模板库（写实电影感 / 绘画动画 两套）
│   ├── prompt_snippets.txt       提示词片段（负面词/运镜/天气/景别/打斗三段式）
│   ├── tools/                    本地工具脚本（graph.py 知识图谱、wiki-graph.cmd 封装）
│   ├── tools_and_accounts.md     生成工具、TTS 音色、BGM 来源、额度记录
│   ├── sfx/                      音效库  weapon兵器 / ambient环境 / mood氛围
│   ├── bgm/                      古风 BGM（含来源记录）
│   └── refs/                     考据库，按朝代分  ming明代/(costume服饰 architecture建筑)
└── works/                        作品区（每部一座隔离仓）
    └── heroic_saga/              《英雄志》
        ├── 00_project/           manual.html 本作手册 / README.txt / progress.md
        ├── 01_source_and_script/ ⚠️ 原著文本只存这里，隔离、不外传 / 剧本 / 分镜表
        ├── 02_characters/        角色卡 + 定妆参考图（每人 3 张）
        ├── 03_style_and_scenes/  本作特有场景（考据引用 _shared/refs）
        ├── 04_generated/         raw 全部生成含废片 / picked 挑中的
        ├── 05_audio/             旁白 / 配音（音效、BGM 引用 _shared）
        ├── 06_edit/              剪辑工程 + 字幕
        └── 07_final/             成片（文件名标 PERSONAL_ONLY）
```

## 新建一部作品的步骤
1. 建 `works/<新作英文名>/`，照 `heroic_saga/` 的 00~07 建同样子目录。
2. 把 `_shared/_templates/` 里的空白模板复制进 `00_project/` 与 `01_source_and_script/`。
3. `_shared/style_presets.txt`、`prompt_snippets.txt` 直接抄用，按本作微调。
4. 音效/BGM/考据优先引用 `_shared/`，本作特有的才放进 works 内。

## Backlog（架构提醒）
- **开第二部作品时**：把 `works/heroic_saga/01_source_and_script/` 里通用的 **wiki 规约(`conventions.md`) + `_templates/` + epub 转换脚本(`_convert.py`)** 提炼进 `_shared/`（脚本需参数化：接收 `epub路径 + 输出目录`）。当前故意留在作品内，以便随第一部迭代验证后再固化。
- **知识图谱工具已通用化**：`_shared/tools/graph.py`（从 LLM_wiki 移植、参数化为 `--wiki`）+ `wiki-graph.cmd` 封装。任意作品跑 `tools/wiki-graph.cmd <作品>/.../wiki [--report]` 即在作品根生成 `graph/graph.html`+`graph.json`。类型着色表（`TYPE_COLORS`）已含 character/faction/theme/volume/segment 等，新增作品类型可视需要扩充。

## 🔴 全局红线
所有作品仅限**本地个人欣赏**：不上传（含网盘公开链接、平台「仅自己可见」与草稿箱）、不分享、不变现。成片文件名统一标 `PERSONAL_ONLY`。

## 关于 GitHub 仓库
本仓库为**私有仓**（private-only），用于本人及少量授权协作者同步工作台。**受版权保护的内容一律不入库**（见 `.gitignore`）：
- 各作 `01_source_and_script/source/`（原著全文 epub/txt/md）—— **绝对不上传**。协作者需自行获取 epub 并本地生成，见 [`docs/COLLABORATION.md`](docs/COLLABORATION.md)。
- `04_generated/` / `05_audio/` / `06_edit/` / `07_final/`（生产素材与成片）—— 体量大且属 `PERSONAL_ONLY`。

`wiki/` 消化层（含衍生梗概与逐字金句摘录）虽属衍生内容仍有版权风险，因此仓库仅私有，**禁止转公开**。

## 协作规则（多人参与时）
- 授权协作者：见仓库 Settings → Collaborators。
- 成品**仅授权协作者本地欣赏**，不外传、不发布、不变现——[全局红线](#-全局红线)对每位协作者同样成立。
- 原著文本**不通过仓库/云盘传递**，各自本地获取。
- 生成素材（图/视频）**不入仓库**；`raw/` 各自本地留存，只交换选中的 `picked/` 与旁白/剪辑工程（通过线下或私密渠道）。
- 上手流程见 [`docs/COLLABORATION.md`](docs/COLLABORATION.md)。
