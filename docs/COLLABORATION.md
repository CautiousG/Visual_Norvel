# 协作者上手指南

欢迎加入 Visual_Norvel 工作台。**先读这份**，5 分钟就能开工。

---

## 0. 你要先接受的红线（无例外）

这是版权敏感项目——原著仍在著作权保护期。加入即接受：

- **只本地个人欣赏**：不上传（含网盘公开链接、平台"仅自己可见"、草稿箱）、不分享给项目组之外、不变现。
- **成片文件名统一标 `PERSONAL_ONLY_DO_NOT_DISTRIBUTE`**。
- **原著文本、生成素材、成片一律不入 git**，不发群、不发朋友圈。
- 如果哪天你觉得想给别人看——先跟发起人商量，不要单方面破规。

不接受这些请立刻退出，别 clone。

---

## 1. 环境准备

**必装：**
- Git for Windows（自带 Bash）
- Python 3.10+（用来跑 epub 转换脚本）
- VS Code 或 Obsidian（后者对 `wiki/` 里的 `[[双链]]` 有原生支持，强烈推荐）

**第一次配置 git（跑一次即可）：**
```bash
git config --global core.quotepath false    # 中文文件名正常显示，别是 8 进制
git config --global user.name  "你的名字"
git config --global user.email "你的GitHub邮箱"
```

## 2. Clone 仓库

```bash
git clone https://github.com/CautiousG/Visual_Norvel.git
cd Visual_Norvel
```

Clone 下来后 `works/heroic_saga/01_source_and_script/source/` 是**空的**——这是故意的，原著全文不入库。下一步你自己补。

## 3. 补齐原著（每个协作者各自做，一次即可）

```bash
# 1) 自己找一份 英雄志.epub，放到：
#    works/heroic_saga/01_source_and_script/source/英雄志.epub

# 2) 解压 epub 到脚本约定的临时目录 _tmp_epub/：
cd works/heroic_saga/01_source_and_script
mkdir -p _tmp_epub
unzip -q "source/英雄志.epub" -d _tmp_epub    # Git Bash 自带 unzip
                                              # 或用资源管理器右键"解压到 _tmp_epub"

# 3) 跑转换脚本：
python _convert.py

# 应看到 "卷数: 23  总字数: 3,320,904" 之类输出
# 然后 source/text/vol00-22.md + index.md 就都有了
```

**验证：**
```bash
ls source/text/       # 应看到 24 个 .md
```

`_tmp_epub/` 已在 `.gitignore` 排除，跑完不用删也没关系。

## 4. 熟悉产出

**先看这三个，就懂全书状态：**
- `works/heroic_saga/00_project/manual.html` — 制作手册（浏览器打开）
- `works/heroic_saga/01_source_and_script/wiki/overview.md` — 全书主线综述
- `works/heroic_saga/01_source_and_script/wiki/candidates.md` — ⭐ 160 段候选段落评分表 + 首支建议

**wiki 索引：**
- `wiki/index.md` — 总入口
- `wiki/status.md` — 消化深度追踪 + 操作日志
- `wiki/conventions.md` — 消化规约
- `wiki/volumes/vol00-22.md` — 每卷梗概（含逐章）
- `wiki/characters/` — 四主角深挖 + 配角索引
- `wiki/themes/` — 7 个思辨母题（含原文金句）

## 5. 分工与协作原则

**避免撞车的三条铁律：**
1. **按段落/角色切工作**——你做卢云段、他做秦仲海段，天然不同文件。
2. **`works/heroic_saga/00_project/progress.md` 是唯一状态板**——谁在做什么写这里，别只在群里讲。
3. **每次 push 前先 `git pull`**——冲突了别硬合，找发起人看。

**Git 日常：**
```bash
git pull                          # 干活前
# ... 编辑 ...
git status                        # 看动了啥
git add -A
git commit -m "简明说明本次改动"
git push
```

## 6. 什么能入库，什么不能

| 类别 | 能入库？ | 说明 |
|------|:-------:|------|
| `wiki/` 消化笔记 | ✅ | 梗概、人物页、母题、候选清单 |
| `_shared/` 模板与提示词库 | ✅ | 通用件 |
| `00_project/manual.html`、`progress.md` | ✅ | 项目文档 |
| `02_characters/` 角色卡（文字部分） | ✅ | 定妆卡文本 + 提示词 |
| **原著全文** `source/英雄志.epub`、`source/text/` | ❌ | 已在 `.gitignore` |
| **参考图/生成图/视频** `04_generated/` `07_final/` | ❌ | 各自本地，只交换 `picked/` |
| **配音/BGM/音效素材文件** `05_audio/*.wav .mp3` | ❌ | 已在 `.gitignore` |
| **剪辑工程** `06_edit/*.prproj .drp` | ❌ | 太大，各自本地 |
| **账号/API key** | ❌ | 见下节 |

不确定的东西——**先别 push，问一下**。传上去删掉也留在 git 历史里。

## 7. 敏感文件（重要）

- `_shared/tools_and_accounts.md` 目前**不含**真实账号。如果你要填自己的 API key / 付费账号，**别提交那次改动**：
  ```bash
  # 本地复制一份带私密信息的副本，用带 .local 的名字（已 gitignore）：
  cp _shared/tools_and_accounts.md _shared/tools_and_accounts.local.md
  # 编辑 .local.md 填你的密钥；仓库里的原文件保持模板状态
  ```

- 任何时候看到自己 commit 里 accidentally 带上了 epub、密钥、大图——**立刻停手告诉发起人**，别自己 push 上去再删（git 历史里还在）。

## 8. 生成素材怎么交换

`04_generated/raw/`（每镜头 3~10 次抽卡）体量会到几十 GB，**不上仓库**。方案：

- **`raw/` 各自本地**——你在自己机器上抽，选中的搬进 `picked/`。
- **`picked/` 通过线下或私密渠道交换**（U 盘 / 私密聊天）——不用公开云盘链接。
- **旁白 wav、剪辑工程** 同上处理。
- **`wiki/`、剧本、分镜表** 走 git 就够了，文字量小。

## 9. 遇到问题

- Git 冲突、脚本报错、消化笔记不确定——**先记在 `progress.md` 或群里说，别硬改**。
- 中文文件名在 git 里显示成 `\350\213\261...`——回头看第 1 节配 `core.quotepath false`。
- Windows 上 `python` 命令找不到：装完 Python 勾选 "Add to PATH"，或者用 `py _convert.py`。

祝顺利。
