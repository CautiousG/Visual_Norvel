# 工具与账号（跨作品共用，填一次反复查）

## 本地工具（仓库自带，跨作品共用）
| 用途 | 入口 | 说明 |
|------|------|------|
| 知识图谱（全量） | `tools/wiki-graph.cmd <wiki> [--report]` | 从 wiki 的 `[[wikilinks]]`+tags 生成 `works/<作品>/graph/graph.html`（vis.js 交互图），含卷/母题/候选段全部页面 |
| 人物关联图 | `python tools/character_graph.py --wiki <wiki>` | 只取 character 类型页面；优先读取 `characters/_relations.md` 真值表，生成按关系类型着色、带核心/主线快捷视图的 `works/<作品>/graph/characters.html` |
| 漫画风批量 | `tools/refresh.py` | 刷新全库（LLM_wiki 移植，需时再启用） |

> 用法示例：`tools/wiki-graph.cmd works/heroic_saga/01_source_and_script/wiki --report`
> 注意：`graph.py` 需 Python 3.10+；输出位置固定为 wiki 上级的上级 `graph/`（各作共享，别手改）。

## 生成工具（图生视频优先，保角色一致性）
| 用途 | 工具 | 账号/入口 | 额度/计费 | 备注 |
|------|------|-----------|-----------|------|
| 定妆参考图（文生图） |  |  |  | 锁角色形象用 |
| 图生视频 |  |  |  | 主力，别用纯文生视频 |
| 备用/补镜 |  |  |  |  |

> 动手前先花一两条额度实测各工具当前对「连续动作 / 多人」的极限，再定分镜。

## TTS 旁白
- 平台/音色：____（沉稳中低男声，略沙哑疲惫感最契合）
- 语速：比常规慢 15~20%；关键句前后留 0.5~1s
- ⚠️ 人名地名多音字逐个试听后记在这里：

## BGM / 音效来源
- BGM 来源（个人自用亦记录）：____
- 音效来源：____
- 存放：可复用的进 `_shared/bgm/`、`_shared/sfx/`；本作特有的留在 works 内

## 剪辑 / 调色
- 剪辑软件：____（工程文件 .prproj/.drp 存 works/<作品>/06_edit/）
- 字幕：.srt
