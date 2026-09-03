#!/usr/bin/env python3
"""构建《英雄志》人物关联图。

数据优先级：characters/_relations.md > 人物卡「人物关系」小节 > 普通 wikilink。
输出：作品根 graph/characters.json、graph/characters.html。
"""

import argparse
import io
import json
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

WIKI_ROOT = Path(".")
KB_ROOT = Path(".")
GRAPH_DIR = Path("graph")
KB_NAME = "作品"


FACTION_COLORS = {
    "朝廷": "#C9A227", "柳门": "#C98A2B", "少林": "#B8860B",
    "九华": "#C77D4F", "华山": "#7BAF5A", "昆仑": "#8E7CC3",
    "怒苍": "#B3372E", "镇国铁卫": "#4A5A6A", "皇族": "#C9A227",
    "西域": "#5A8C6A", "小人物": "#9B9B9B", "平民": "#9B9B9B",
    "default": "#8A9BA8",
}

REL_TYPES = {
    "情感": {"color": "#E85D75", "dashes": False, "keywords": [
        "恋人", "爱人", "痴缠", "情愫", "情债", "妻", "丈夫", "夫妇", "嫁", "娶",
        "私奔", "相思", "相恋", "倾心", "挚爱", "红颜", "继室", "情侣",
    ]},
    "敌意": {"color": "#A93226", "dashes": True, "keywords": [
        "宿敌", "死敌", "大仇", "世仇", "仇敌", "宿仇", "刺杀目标", "敌对", "对立",
        "构陷", "死结", "情敌", "对手", "敌", "仇", "杀", "扳倒", "对峙",
    ]},
    "血缘": {"color": "#C77DFF", "dashes": False, "keywords": [
        "生父", "养父", "母亲", "父亲", "父子", "母子", "祖", "孙", "血脉", "儿子",
        "女儿", "遗孤", "义子", "养母", "养子", "父", "母", "子", "女",
    ]},
    "师承": {"color": "#F2B04C", "dashes": False, "keywords": [
        "师父", "师徒", "授业", "弟子", "传人", "关门", "门下", "师傅", "点拨",
        "师门", "亲传", "之师", "师长",
    ]},
    "恩义": {"color": "#5CA86E", "dashes": False, "keywords": [
        "生死之交", "知己", "恩主", "救命", "莫逆", "故交", "知交", "义救", "义气",
        "恩人", "报恩", "托孤", "旧主", "交心", "之交", "舍身", "互信",
    ]},
    "同袍": {"color": "#5A9BD8", "dashes": False, "keywords": [
        "战友", "同僚", "同袍", "同门", "部属", "属下", "旧部", "麾下", "手下",
        "寨中", "柳门", "同侪", "同行", "同路", "患难", "上下级",
    ]},
    "敌对": {"color": "#8E44AD", "dashes": True, "keywords": [
        "敌对", "怒苍vs正统", "立场敌对",
    ]},
    "死敌": {"color": "#641E16", "dashes": True, "keywords": [
        "死敌", "不死不休",
    ]},
    "恩仇": {"color": "#D68910", "dashes": True, "keywords": [
        "恩仇", "逐子", "恩断义绝",
    ]},
    "悬": {"color": "#7F8C8D", "dashes": True, "keywords": [
        "悬", "待续", "未定",
    ]},
}

KEYWORDS = sorted(
    ((keyword, relation_type)
     for relation_type, info in REL_TYPES.items()
     for keyword in info["keywords"]),
    key=lambda item: -len(item[0]),
)


def set_kb(wiki_path: str) -> None:
    global WIKI_ROOT, KB_ROOT, GRAPH_DIR, KB_NAME
    wiki = Path(wiki_path).resolve()
    if not wiki.is_dir():
        raise SystemExit(f"wiki directory not found: {wiki_path}")
    WIKI_ROOT = wiki
    KB_ROOT = wiki.parent.parent
    GRAPH_DIR = KB_ROOT / "graph"
    KB_NAME = KB_ROOT.name


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def parse_tags(text: str) -> list[str]:
    match = re.search(r"^tags:\s*\[([^\]]*)\]", text, re.MULTILINE)
    return [] if not match else [x.strip() for x in match.group(1).split(",") if x.strip()]


def extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]", text)


def faction_color(faction: str) -> str:
    for name, color in FACTION_COLORS.items():
        if name != "default" and name in faction:
            return color
    return FACTION_COLORS["default"]


def classify_relation(description: str) -> str:
    for keyword, relation_type in KEYWORDS:
        if keyword in description:
            return relation_type
    return "其他"


def collect_characters() -> dict[str, dict]:
    characters = {}
    for path in WIKI_ROOT.rglob("*.md"):
        if "_templates" in path.parts or path.name in {"index.md", "log.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        if frontmatter.get("type") != "character":
            continue
        characters[path.stem] = {
            "path": path,
            "text": text,
            "frontmatter": frontmatter,
            "tags": parse_tags(text),
        }
    return characters


def collect_card_relations(characters: dict[str, dict]) -> dict[tuple[str, str], dict[str, str]]:
    relations = {}
    for source, character in characters.items():
        section = re.search(r"## 人物关系\n(.*?)(?=\n## |\Z)", character["text"], re.DOTALL)
        if not section:
            continue
        for line in section.group(1).splitlines():
            match = re.match(r"^\s*-\s*\[\[([^\]]+)\]\][：:]\s*(.+)$", line)
            if match and match.group(1).strip() in characters:
                target, description = match.group(1).strip(), match.group(2).strip()
                relations[(source, target)] = {"desc": description, "source": "card"}
    return relations


def collect_timeline() -> list[dict]:
    """读取 _relations.md 的「时间轴」区块，返回阶段定义列表。"""
    path = WIKI_ROOT / "characters" / "_relations.md"
    if not path.exists():
        return []
    phase_re = re.compile(r"^|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
    phases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            phases.append({
                "index": int(cells[0]),
                "name": cells[1],
                "range": cells[2],
                "summary": cells[3],
            })
    return phases


def parse_curve(raw: str) -> list[dict]:
    """解析「曲线」列：`1..3:恩义|柳门同僚; 4..7:敌意|情敌; 7:恩仇|逐子` → 分段列表。

    支持 `N..M` 区间与单个 `N`（M=N）两种形式。
    """
    if not raw or raw.strip() in {"", "待续"}:
        return []
    curve = []
    for seg in raw.split(";"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"^\s*(\d+)\s*(?:\.\.\s*(\d+)\s*)?:\s*([^|]+?)\s*(?:\|\s*(.*))?$", seg)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) is not None else start
            curve.append({
                "start": start,
                "end": end,
                "type": m.group(3).strip(),
                "desc": (m.group(4) or "").strip(),
            })
    return curve


def collect_truth_relations(characters: dict[str, dict]) -> dict[tuple[str, str], dict[str, str]]:
    path = WIKI_ROOT / "characters" / "_relations.md"
    if not path.exists():
        return {}
    # 行首以 | 开头且以 | 结尾的表行；用真实单元格切分，但曲线列内部用 | 分隔，需把第 6 列起的重新拼回
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line[1:-1].split("|")]
        if len(cells) < 5:
            continue
        first = cells[0]
        second = cells[1]
        # 只处理 [[...]] 形式的人物对，跳过表头/分隔行
        if not (first.startswith("[[") and first.endswith("]]") and second.startswith("[[") and second.endswith("]]")):
            continue
        first, second = first[2:-2].strip(), second[2:-2].strip()
        if first not in characters or second not in characters or first == second:
            continue
        # 表结构：| A | B | 类型 | 说明 | 证据 | 曲线 |（曲线是第6列=index5）
        # 曲线内部可能含 |（类型|说明），导致 cells 被拆多格，故从 index5 起用 | 拼回
        itype = cells[2].strip()
        desc = cells[3].strip()
        evidence = cells[4].strip()
        curve_raw = "|".join(cells[5:]) if len(cells) > 5 else ""
        curve_raw = curve_raw.strip().strip("`").strip()
        pair = tuple(sorted((first, second)))
        result[pair] = {
            "type": itype,
            "desc": desc,
            "source": "truth",
            "evidence": evidence,
            "curve_raw": curve_raw,
            "curve": parse_curve(curve_raw),
            "from": first,
            "to": second,
        }
    return result


def build_graph() -> dict:
    characters = collect_characters()
    card_relations = collect_card_relations(characters)
    truth_relations = collect_truth_relations(characters)
    candidates = set(truth_relations)
    for source, relation in card_relations:
        candidates.add(tuple(sorted((source, relation))))
    for source, character in characters.items():
        for target in extract_wikilinks(character["text"]):
            if target in characters and target != source:
                candidates.add(tuple(sorted((source, target))))

    edges = []
    for first, second in sorted(candidates):
        truth = truth_relations.get((first, second))
        forward = card_relations.get((first, second), {}).get("desc", "")
        backward = card_relations.get((second, first), {}).get("desc", "")
        if truth:
            edges.append({
                "from": truth["from"], "to": truth["to"],
                "type": truth["type"], "desc": truth["desc"],
                "source": "truth", "dir_desc": forward, "rev_desc": backward,
                "evidence": truth.get("evidence", ""),
                "curve": truth.get("curve", []),
                "curve_raw": truth.get("curve_raw", ""),
            })
            continue
        description = " / ".join(x for x in (forward, backward) if x)
        edges.append({
            "from": first, "to": second, "type": classify_relation(description),
            "desc": description, "source": "card" if description else "wikilink",
            "dir_desc": forward, "rev_desc": backward,
        })

    nodes = []
    for slug, character in characters.items():
        frontmatter = character["frontmatter"]
        nodes.append({
            "id": slug,
            "label": frontmatter.get("title", slug),
            "tags": character["tags"],
            "is_protagonist": "主角" in character["tags"],
            "color": faction_color(frontmatter.get("faction", "")),
            "path": str(character["path"].relative_to(KB_ROOT)).replace("\\", "/"),
        })

    return {
        "generated": date.today().isoformat(),
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "type_count": dict(Counter(edge["type"] for edge in edges)),
            "source_count": dict(Counter(edge["source"] for edge in edges)),
        },
        "nodes": nodes,
        "edges": edges,
    }


def generate_html(graph: dict) -> str:
    nodes_json = json.dumps(graph["nodes"], ensure_ascii=False)
    edges_json = json.dumps(graph["edges"], ensure_ascii=False)
    relation_json = json.dumps({
        name: {"color": info["color"], "dashes": info["dashes"]}
        for name, info in REL_TYPES.items()
    }, ensure_ascii=False)
    timeline = collect_timeline()
    timeline_json = json.dumps(timeline, ensure_ascii=False)
    html = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>__TITLE__</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
:root{--ink:#171c24;--panel:#202832;--panel-2:#26313d;--paper:#e9dfca;--muted:#9da8b0;--line:#394654;--vermilion:#d96555;--gold:#d2a85c;--blue:#91b7cb}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Noto Serif SC","Source Han Serif SC","STSong",Georgia,serif;background:var(--ink);color:var(--paper);display:flex;height:100vh;overflow:hidden}
#graph{flex:1;position:relative;min-width:0;background:radial-gradient(ellipse at 48% 45%,#283744 0%,#18222c 46%,#11171e 100%)}
#graph:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.13;background-image:linear-gradient(rgba(216,196,157,.2) 1px,transparent 1px),linear-gradient(90deg,rgba(216,196,157,.2) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,black,transparent 88%)}
#graph-head{position:absolute;z-index:2;top:24px;left:30px;pointer-events:none;max-width:440px}
#graph-head .eyebrow{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.22em;color:var(--vermilion);font-size:11px;margin-bottom:8px}
#graph-head h1{font-size:25px;font-weight:600;letter-spacing:.08em;color:#f1e7d2;text-shadow:0 2px 18px #0d1319;margin-bottom:6px}
#graph-head p{font-size:13px;color:#b8c1c4;letter-spacing:.04em}
#graph-head .seal{display:inline-block;margin-left:9px;color:var(--vermilion);border:1px solid var(--vermilion);padding:2px 5px;font-size:10px;letter-spacing:.1em;vertical-align:3px}
#sidebar{width:370px;background:linear-gradient(145deg,#202a34,#182029);padding:20px 18px;overflow-y:auto;border-left:1px solid #3b4650;display:flex;flex-direction:column;gap:14px;box-shadow:-18px 0 45px rgba(4,8,12,.24)}
#sidebar::-webkit-scrollbar{width:7px}#sidebar::-webkit-scrollbar-thumb{background:#46515b;border-radius:4px}
.section{border-top:1px solid var(--line);padding-top:12px}.section:first-child{border-top:0;padding-top:0}
h2{font-size:12px;color:var(--gold);letter-spacing:.18em;margin-bottom:9px;font-weight:600}.stat{font-size:13px;color:var(--muted)}.stat b{color:var(--paper)}
.kicker{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:10px;color:#75818a;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px}.line{height:3px;width:26px;border-radius:2px}.dot{width:12px;height:12px;border-radius:50%;border:1px solid #666}.sq{width:12px;height:12px;border:1px solid #666}.legend-item{display:flex;align-items:center;gap:8px;font-size:13px;color:#c9c9c1;margin:5px 0}
.view-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}.view-btn{border:1px solid #455360;background:#26323e;color:#d8d1c2;border-radius:3px;padding:9px 8px;cursor:pointer;font-family:inherit;font-size:12px;transition:.18s;text-align:left}.view-btn:hover,.view-btn.active{background:#604039;border-color:var(--vermilion);color:#fff1dc}.view-btn.active:before{content:"◆ ";color:#f18a78}
#filter{font-size:13px;display:grid;grid-template-columns:1fr 1fr;column-gap:12px}#filter label{display:flex;align-items:center;gap:6px;cursor:pointer;padding:4px 0;color:#c4c9c6}#filter input{accent-color:var(--vermilion)}
#typecount,#sourcecount{font-size:12px;color:#aab1b3;line-height:1.9}.metric-row{display:flex;justify-content:space-between;border-bottom:1px dotted #3c4851;padding:4px 0}.metric-row b{color:var(--paper);font-weight:500}
#search{width:100%;border:1px solid #46535e;background:#141b22;color:var(--paper);border-radius:3px;padding:9px 10px;font-family:inherit;font-size:13px;outline:0}#search:focus{border-color:var(--gold);box-shadow:0 0 0 2px rgba(210,168,92,.12)}
.toolbar-btn{border:0;background:transparent;color:#9da8b0;font-family:inherit;cursor:pointer;font-size:12px;padding:3px 0}.toolbar-btn:hover{color:#f0d7a5}
#detail{font-size:14px;line-height:1.75;background:rgba(10,14,18,.25);border-left:2px solid var(--vermilion);padding:12px 13px;min-height:74px}#detail .title{font-size:20px;font-weight:600;color:#f5e7ce;letter-spacing:.06em}#detail .type{font-size:12px;color:var(--gold);margin:4px 0 8px}#detail .rel{color:#d5d1c8;cursor:pointer}#detail .rel:hover{color:#fff}.rel-desc{color:#93a5a8;font-size:12px}#placeholder{color:#69767b;text-align:center;margin-top:12px;font-size:13px}
#sourcecount .stamp{color:var(--vermilion);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px}
#time-slider{width:100%;accent-color:var(--vermilion);cursor:pointer;margin:6px 0 8px}.time-label{font-size:14px;font-weight:600;color:#f0d7a5;letter-spacing:.04em}.time-desc{font-size:12px;color:#9fb0b6;line-height:1.6;margin-top:5px;border-left:2px solid #3b4650;padding-left:9px}.time-note{font-size:11px;color:#b96a5a;margin-top:6px;letter-spacing:.02em}
@media(max-width:900px){#sidebar{width:320px}#graph-head{left:18px}#graph-head h1{font-size:21px}}
</style></head><body>
<div id="graph"><div id="graph-head"><div class="eyebrow">HEROIC SAGA · CHARACTER DOSSIER</div><h1>人物关联图 <span class="seal">核心关系</span></h1><p>点击一名人物，查看其关系脉络与证据说明</p></div></div><aside id="sidebar">
<div class="section"><div class="kicker">Current dossier</div><h2>人物档案</h2><div class="stat"><b style="font-size:20px" id="stat-n">0</b> 人物 <span style="color:#58656d">·</span> <b style="font-size:20px" id="stat-e">0</b> 条核心关系</div></div>
<div class="section"><div class="kicker">Timeline · 剧情时间轴</div><h2>七大节点</h2><input type="range" id="time-slider" min="1" max="7" step="1" value="7"><div class="time-label" id="time-label">阶段 7 · 兵临城下·未完结</div><div class="time-desc" id="time-desc"></div></div>
<div class="section"><h2>关系来源</h2><div id="sourcecount"></div></div><div class="section"><h2>关系类型</h2><div id="typecount"></div></div>
<div class="section"><h2>快捷视图</h2><div class="view-grid"><button class="view-btn" data-view="all" onclick="applyView('all')">全部核心关系</button><button class="view-btn" data-view="main" onclick="applyView('main')">四主角核心图</button><button class="view-btn" data-view="anger" onclick="applyView('anger')">怒苍线</button><button class="view-btn" data-view="iron" onclick="applyView('iron')">镇国铁卫线</button></div></div>
<div class="section"><h2>查找人物</h2><input id="search" type="search" placeholder="输入人物名…" autocomplete="off"><button class="toolbar-btn" id="clear-focus">清除选中 / 恢复全图</button></div>
<div class="section"><h2>显示筛选</h2><div id="filter"></div></div>
<div class="section"><h2>人物节点图例</h2><div class="legend-item"><div class="dot" style="background:#C9A227"></div>朝廷 / 皇族</div><div class="legend-item"><div class="dot" style="background:#B3372E"></div>怒苍</div><div class="legend-item"><div class="dot" style="background:#8E7CC3"></div>昆仑</div><div class="legend-item"><div class="dot" style="background:#7BAF5A"></div>华山 / 九华</div><div class="legend-item"><div class="dot" style="background:#4A5A6A"></div>镇国铁卫</div><div class="legend-item"><div class="dot" style="background:#5A8C6A"></div>西域</div><div class="legend-item"><div class="sq" style="background:#fff"></div>主角（方形大节点）</div></div>
<div class="section"><h2>关系线图例</h2><div id="rel-legend"></div></div><div id="detail"><div id="placeholder">点击人物查看核心关系</div></div>
</aside><script>
const rawNodes=__NODES__, rawEdges=__EDGES__, REL=__REL__, TIMELINE=__TIMELINE__; const nodeMap={}; rawNodes.forEach(n=>nodeMap[n.id]=n);
const CORE_TYPES=new Set(["情感","敌意","血缘","师承","恩义","同袍","敌对","死敌","恩仇","悬"]);
let currentPhase=7;
// 某条边在某阶段的类型/说明（有曲线按曲线，无曲线默认全部阶段一致）
function edgeAt(e, phase){
  if(e.curve && e.curve.length){
    const seg=e.curve.find(s=>phase>=s.start&&phase<=s.end);
    return seg ? {type:seg.type, desc:(seg.desc||e.desc||"")} : null;
  }
  return {type:e.type, desc:e.desc||"", fallback:true};
}
function reloadForPhase(phase){
  currentPhase=phase;
  const ids=viewIds(activeView);
  const checked=new Set([...document.querySelectorAll(".f-rel:checked")].map(x=>x.dataset.t));
  const truthOnly=document.getElementById("only-truth")?document.getElementById("only-truth").checked:false;
  const cur=rawEdges.map(e=>({e,at:edgeAt(e,phase)})).filter(x=>x.at);
  const visible=cur.filter(({e,at})=>checked.has(at.type)&&(!truthOnly||e.source==="truth")&&(!ids||(ids.has(e.from)&&ids.has(e.to))));
  return {all:cur, visible};
}
function renderForPhase(phase, keepFocus){
  const {visible}=reloadForPhase(phase);
  edges.clear();
  edges.add(visible.map(({e,at},i)=>Object.assign({id:i,from:e.from,to:e.to},edgeProps(at))));
  if(!keepFocus){ const ids=viewIds(activeView); rawNodes.forEach(n=>nodes.update({id:n.id,hidden:!!ids&&!ids.has(n.id)})); }
  fitAfter();
}
const MAIN_IDS=new Set(["卢云","伍定远","杨肃观","秦仲海","顾倩兮","言二娘","银川公主","阿秀"]);
const ANGER_IDS=new Set(["秦仲海","言二娘","韩毅","方子敬","阿秀"]);
const IRON_IDS=new Set(["杨肃观","顾倩兮","艳婷","天绝僧","琼武川","琼芳","帅金藤","苏颖超"]);
rawNodes.sort((a,b)=>(b.is_protagonist?1:0)-(a.is_protagonist?1:0));
const nodes=new vis.DataSet(rawNodes.map(n=>({id:n.id,label:n.label,color:{background:n.color,border:n.color,highlight:{background:"#fff",border:"#fff"}},shape:n.is_protagonist?"square":"dot",size:n.is_protagonist?26:15,font:{color:"#eee",size:n.is_protagonist?17:13,bold:n.is_protagonist},borderWidth:n.is_protagonist?3:1})));
function edgeProps(e){const t=REL[e.type]||{color:"#667",dashes:false};return{color:{color:t.color,highlight:"#fff"},dashes:!!t.dashes,width:(e.type==="情感"||e.type==="敌意")?2.6:1.5,label:e.type==="其他"?"":e.type,font:{size:12,color:t.color,strokeWidth:4,strokeColor:"#12151c",align:"middle"},title:(e.desc||"关联")+"（hover）",arrows:""};}
const edges=new vis.DataSet(); const network=new vis.Network(document.getElementById("graph"),{nodes,edges},{physics:{solver:"forceAtlas2Based",forceAtlas2Based:{gravitationalConstant:-180,springLength:160,springConstant:.05,damping:.32},stabilization:{iterations:300,fit:true}},interaction:{hover:true,tooltipDelay:120,navigationButtons:true,keyboard:true}});
let activeView="all";
function viewIds(view){return view==="main"?MAIN_IDS:view==="anger"?ANGER_IDS:view==="iron"?IRON_IDS:null;}
function visibleEdges(phase){return reloadForPhase(phase||currentPhase).visible;}
function applyView(view){activeView=view;const ids=viewIds(view);rawNodes.forEach(n=>nodes.update({id:n.id,hidden:!!ids&&!ids.has(n.id)}));renderEdges();}
function renderEdges(){renderForPhase(currentPhase, false);}
function updateTimeDisplay(){const t=TIMELINE.find(x=>x.index===currentPhase);if(!t)return;document.getElementById("time-label").textContent=`阶段 ${t.index} · ${t.name}`;const desc=`<div class="time-desc">${t.summary}</div>${currentPhase===7?'<div class="time-note">⚠ 原著连载至此处「大变将至」，未完结</div>':''}`;document.getElementById("time-desc").innerHTML=desc;document.getElementById("time-slider").value=currentPhase;}
function showStats(){document.getElementById("stat-n").textContent=rawNodes.length;document.getElementById("stat-e").textContent=rawEdges.filter(e=>CORE_TYPES.has(e.type)&&e.source==="truth").length;const tc={};rawEdges.forEach(e=>tc[e.type]=(tc[e.type]||0)+1);const order=relOrder();document.getElementById("typecount").innerHTML=order.filter(t=>tc[t]).map(t=>`<span style="color:${(REL[t]||{}).color}">● ${t} ${tc[t]}</span>`).join(" &nbsp; ");const sc={};rawEdges.forEach(e=>sc[e.source]=(sc[e.source]||0)+1);document.getElementById("sourcecount").innerHTML=`真值表 ${sc.truth||0} · 人物卡 ${sc.card||0} · 普通提及 ${sc.wikilink||0}`;document.getElementById("rel-legend").innerHTML=order.filter(t=>REL[t]).map(t=>'<div class="legend-item"><div class="line" style="background:'+REL[t].color+';'+(REL[t].dashes?'border-top:2px dashed '+REL[t].color+';background:transparent;':'')+'"></div>'+t+'</div>').join("");const defaultChecked=new Set(["情感","敌意","血缘","师承","恩义","同袍","敌对","死敌","恩仇"]);document.getElementById("filter").innerHTML=order.filter(t=>REL[t]&&t!=="其他").map(t=>`<label><input type="checkbox" class="f-rel" data-t="${t}" ${defaultChecked.has(t)?"checked":""}> ${t}</label>`).join("")+`<label><input type="checkbox" id="only-truth" checked> 只看关系真值表</label>`;document.querySelectorAll("#filter input").forEach(x=>x.addEventListener("change",renderEdges));applyView("all");updateTimeDisplay();}
function relOrder(){return ["情感","敌意","血缘","师承","恩义","同袍","敌对","死敌","恩仇","悬","其他"];}
function focusNode(id){network.focus(id,{scale:1.25,animation:true});network.selectNodes([id]);network.emit("click",{nodes:[id],edges:[]});}
document.getElementById("clear-focus").addEventListener("click",()=>{network.unselectAll();displayDetail(null);showAllNodes();});
document.getElementById("time-slider").addEventListener("input",e=>{currentPhase=parseInt(e.target.value,10);updateTimeDisplay();renderEdges();});
function showAllNodes(){const ids=viewIds(activeView);rawNodes.forEach(n=>nodes.update({id:n.id,hidden:!!ids&&!ids.has(n.id)}));renderEdges();}
function displayDetail(node){if(!node){document.getElementById("detail").innerHTML=`<div id="placeholder">点击人物查看核心关系</div>`;return;}const phase=currentPhase;const rels=rawEdges.map(e=>({e,at:edgeAt(e,phase)})).filter(({e,at})=>at&&e.source==="truth"&&(e.from===node.id||e.to===node.id));const lines=rels.map(({e,at})=>{const other=e.from===node.id?e.to:e.from,t=REL[at.type]||{};return`<span class="rel" onclick="focusNode('${other}')">${nodeMap[other]?.label||other} <i style="color:${t.color}">（${at.type}：${at.desc||""}）</i></span><div class="rel-desc">${at.desc||""}${e.curve&&e.curve.length?' · 随剧情变化':'（全书一致）'}</div>`}).join("");document.getElementById("detail").innerHTML=`<div class="title">${node.label}</div><div class="type">${node.is_protagonist?"主角":"配角"} · 阶段${phase} 真值关系 ${rels.length} 人</div><div style="margin-top:8px">${lines||"（此阶段无真值关系）"}</div>`;}
function applyFocus(id){const phase=currentPhase;const focusEdges=rawEdges.filter(e=>e.from===id||e.to===id).map(e=>{const at=edgeAt(e,phase);if(!at)return null;const other=e.from===id?e.to:e.from,t=REL[at.type]||{};return{from:e.from,to:e.to,type:at.type,desc:at.desc,source:e.source,color:t.color,dashes:!!t.dashes,label:at.type==="其他"?"":at.type,title:(at.desc||"关联")+"（hover）"};}).filter(Boolean);edges.clear();edges.add(focusEdges.map((e,i)=>Object.assign({id:i,from:e.from,to:e.to},edgeProps(e))));rawNodes.forEach(n=>nodes.update({id:n.id,hidden:!n.is_protagonist&&n.id!==id&&!focusEdges.some(e=>e.from===n.id||e.to===n.id)}));network.focus(id,{scale:1.35,animation:true});}
document.getElementById("search").addEventListener("input",e=>{const q=e.target.value.trim();if(!q){showAllNodes();return;}const match=rawNodes.find(n=>n.label.includes(q));if(match)applyFocus(match.id);});
network.on("click",params=>{if(!params.nodes.length){displayDetail(null);network.unselectAll();showAllNodes();return;}const id=params.nodes[0],node=nodeMap[id];displayDetail(node);applyFocus(id);});
showStats();
</script></body></html>'''
    return (html.replace("__TITLE__", f"{KB_NAME} · 人物关联图")
                .replace("__NODES__", nodes_json)
                .replace("__EDGES__", edges_json)
                .replace("__REL__", relation_json)
                .replace("__TIMELINE__", timeline_json))


def main() -> int:
    parser = argparse.ArgumentParser(description="构建人物关联图")
    parser.add_argument("--wiki", required=True, help="wiki 目录")
    parser.add_argument("--open", action="store_true", help="生成后打开浏览器")
    args = parser.parse_args()
    set_kb(args.wiki)
    graph = build_graph()
    GRAPH_DIR.mkdir(exist_ok=True)
    (GRAPH_DIR / "characters.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    (GRAPH_DIR / "characters.html").write_text(generate_html(graph), encoding="utf-8")
    print(f"人物关联图：{graph['stats']['nodes']} 人 / {graph['stats']['edges']} 条关系")
    print(f"类型分布：{graph['stats']['type_count']}")
    print(f"来源分布：{graph['stats']['source_count']}")
    print(f"→ {GRAPH_DIR / 'characters.html'}")
    if args.open:
        opener = "start" if platform.system() == "Windows" else ("open" if platform.system() == "Darwin" else "xdg-open")
        subprocess.Popen([opener, str(GRAPH_DIR / "characters.html")], shell=platform.system() == "Windows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
