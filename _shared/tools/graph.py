#!/usr/bin/env python3
"""
graph.py — 知识图谱构建与可视化

功能：
  Pass 1（确定性）：解析所有 [[wikilinks]]，构建显式边（confidence=1.0）
  Pass 2（启发式）：基于共享 tags 推断隐式语义边（不调用 LLM，无 API 费用）
  输出：graph/graph.json + graph/graph.html（vis.js 交互可视化）

用法：
  python tools/graph.py [--kb KB] [--no-infer] [--report] [--open]
"""

import json
import io
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import date

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KB_ROOT = Path(__file__).resolve().parent  # fallback, overridden by --wiki
WIKI_ROOT = KB_ROOT / "wiki"
GRAPH_DIR = KB_ROOT / "graph"
KB_NAME = ""  # human-readable name for HTML title


def set_kb(wiki_path: str) -> None:
    global KB_ROOT, WIKI_ROOT, GRAPH_DIR, KB_NAME
    p = Path(wiki_path).resolve()
    if not p.exists():
        print(f"Error: wiki directory not found at {wiki_path}")
        sys.exit(1)
    # 作品根 = wiki 的上级的上级（如 works/heroic_saga/ ← 01_source_and_script/ ← wiki）
    KB_ROOT = p.parent.parent
    WIKI_ROOT = p
    # 图输出到作品根 graph/（避开 01_source_and_script 版权隔离层，可随仓库版本化）
    GRAPH_DIR = KB_ROOT / "graph"
    KB_NAME = KB_ROOT.name


# ─── 数据模型 ─────────────────────────────────────────────────────────────────

def build_page_map() -> dict[str, Path]:
    pages = {}
    for f in WIKI_ROOT.rglob("*.md"):
        # 忽略总索引、日志与模板目录（模板页不入图）
        if f.name in ("index.md", "log.md"):
            continue
        if "_templates" in f.parts:
            continue
        # overview 是关联图枢纽，保留
        pages[f.stem] = f
    return pages


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    return fields


def parse_tags(text: str) -> list[str]:
    m = re.search(r"^tags:\s*\[([^\]]*)\]", text, re.MULTILINE)
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def extract_wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]", text)


# ─── 颜色方案（按页面类型） ────────────────────────────────────────────────────

TYPE_COLORS = {
    "concept": "#4A90D9",
    "source":  "#F5A623",
    "output":  "#7ED321",
    # 英雄志 / Visual_Norvel wiki 类型
    "character": "#E05A73",   # 人物（红粉）
    "faction":   "#C98A2B",   # 势力（金）
    "theme":     "#7B6FD8",   # 母题（紫）
    "volume":    "#4A90D9",   # 卷（蓝）
    "segment":   "#3FAE8C",   # 候选段落（绿）
    "overview":  "#A062C4",   # 综述（紫粉）
    "index":     "#6E8B9F",   # 索引（灰蓝）
    "review":    "#8D6E63",   # 审查（棕）
    "default":   "#9B9B9B",
}

TYPE_SHAPES = {
    "concept": "dot",
    "source":  "square",
    "output":  "triangle",
    # 人物用方块（容易认出）、卷用圆形、其余椭圆
    "character": "square",
    "volume":    "dot",
    "default":   "ellipse",
}


# ─── Pass 1：显式 wikilink 边 ──────────────────────────────────────────────────

def build_explicit_edges(pages: dict[str, Path]) -> list[dict]:
    edges = []
    known = set(pages.keys())
    seen = set()
    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        for link in extract_wikilinks(text):
            target = link.strip()
            if target in known and target != slug:
                key = tuple(sorted([slug, target]))
                if key not in seen:
                    seen.add(key)
                    edges.append({
                        "from": slug, "to": target,
                        "confidence": 1.0, "type": "EXTRACTED"
                    })
    return edges


# ─── Pass 2：tag 共享语义边（启发式，无 API） ──────────────────────────────────

def build_inferred_edges(pages: dict[str, Path], explicit_pairs: set) -> list[dict]:
    """两个页面共享 ≥2 个 tag，且无显式链接，则推断为隐式相关。"""
    tag_map: dict[str, list[str]] = {}  # slug → tags
    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        tag_map[slug] = parse_tags(text)

    slugs = list(pages.keys())
    edges = []
    seen = set()
    for i, a in enumerate(slugs):
        for b in slugs[i+1:]:
            pair = tuple(sorted([a, b]))
            if pair in explicit_pairs or pair in seen:
                continue
            shared = set(tag_map.get(a, [])) & set(tag_map.get(b, []))
            shared.discard("")
            if len(shared) >= 2:
                seen.add(pair)
                confidence = min(0.9, 0.5 + 0.1 * len(shared))
                edges.append({
                    "from": a, "to": b,
                    "confidence": round(confidence, 2),
                    "type": "INFERRED",
                    "shared_tags": sorted(shared)
                })
    return edges


# ─── 图数据构建 ────────────────────────────────────────────────────────────────

def build_graph(pages: dict[str, Path], infer: bool = True) -> dict:
    nodes = []
    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        ptype = fm.get("type", "default")
        nodes.append({
            "id": slug,
            "label": fm.get("title", slug),
            "type": ptype,
            "summary": fm.get("summary", ""),
            "tags": parse_tags(text),
            "path": str(path.relative_to(KB_ROOT)).replace("\\", "/"),
            "color": TYPE_COLORS.get(ptype, TYPE_COLORS["default"]),
            "shape": TYPE_SHAPES.get(ptype, TYPE_SHAPES["default"]),
        })

    explicit = build_explicit_edges(pages)
    explicit_pairs = {tuple(sorted([e["from"], e["to"]])) for e in explicit}

    inferred = build_inferred_edges(pages, explicit_pairs) if infer else []

    all_edges = explicit + inferred
    # 标注边样式
    for e in all_edges:
        if e["type"] == "EXTRACTED":
            e["color"] = "#4A90D9"
            e["dashes"] = False
            e["width"] = 2
        else:
            e["color"] = "#AAAAAA"
            e["dashes"] = True
            e["width"] = 1

    return {
        "generated": date.today().isoformat(),
        "stats": {
            "nodes": len(nodes),
            "explicit_edges": len(explicit),
            "inferred_edges": len(inferred),
        },
        "nodes": nodes,
        "edges": all_edges,
    }


# ─── vis.js HTML 生成 ──────────────────────────────────────────────────────────

def generate_html(graph: dict) -> str:
    nodes_json = json.dumps(graph["nodes"], ensure_ascii=False)
    edges_json = json.dumps(graph["edges"], ensure_ascii=False)
    stats = graph["stats"]

    kb_label = KB_NAME or "Wiki"
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>{kb_label} 知识图谱</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background: #1a1a2e; color: #eee; display: flex; height: 100vh; }}
  #graph {{ flex: 1; }}
  #sidebar {{
    width: 320px; background: #16213e; padding: 16px; overflow-y: auto;
    border-left: 1px solid #0f3460; display: flex; flex-direction: column; gap: 12px;
  }}
  h2 {{ font-size: 14px; color: #a0c4ff; letter-spacing: 0.05em; }}
  .stat {{ font-size: 12px; color: #888; }}
  .stat b {{ color: #ccc; }}
  #detail {{ font-size: 13px; line-height: 1.6; }}
  #detail .title {{ font-size: 16px; font-weight: bold; color: #fff; margin-bottom: 4px; }}
  #detail .type {{ font-size: 11px; color: #a0c4ff; text-transform: uppercase; margin-bottom: 8px; }}
  #detail .summary {{ color: #ccc; margin-bottom: 10px; }}
  #detail .tags {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }}
  #detail .tag {{
    background: #0f3460; color: #a0c4ff; font-size: 11px;
    padding: 2px 8px; border-radius: 12px;
  }}
  #detail .neighbors h3 {{ font-size: 12px; color: #888; margin-bottom: 6px; }}
  #detail .neighbor-link {{
    display: block; color: #7cc8f8; font-size: 13px;
    cursor: pointer; padding: 3px 0;
    border-bottom: 1px solid #0f3460;
  }}
  #detail .neighbor-link:hover {{ color: #fff; }}
  .legend {{ display: flex; flex-direction: column; gap: 6px; }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  .sq {{ width: 12px; height: 12px; }}
  #filter {{ margin-top: 4px; }}
  #filter label {{ font-size: 12px; display: flex; align-items: center; gap: 6px; cursor: pointer; }}
  #placeholder {{ color: #555; font-size: 13px; text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div>
    <h2>{kb_label} 知识图谱</h2>
    <div class="stat">生成于 {graph["generated"]}</div>
    <div class="stat">
      <b>{stats["nodes"]}</b> 页面 &nbsp;·&nbsp;
      <b>{stats["explicit_edges"]}</b> 显式边 &nbsp;·&nbsp;
      <b>{stats["inferred_edges"]}</b> 推断边
    </div>
  </div>
  <div class="legend">
    <h2>图例</h2>
    <div class="legend-item"><div class="dot" style="background:#4A90D9"></div>概念页面</div>
    <div class="legend-item"><div class="sq" style="background:#F5A623"></div>来源摘要</div>
    <div class="legend-item"><div class="dot" style="background:#7ED321"></div>问答输出</div>
    <div class="legend-item">
      <div style="width:30px;height:2px;background:#4A90D9"></div>显式链接
    </div>
    <div class="legend-item">
      <div style="width:30px;height:2px;background:#aaa;border-top:1px dashed #aaa"></div>推断关联
    </div>
  </div>
  <div id="filter">
    <h2>过滤</h2>
    <label><input type="checkbox" id="hide-inferred"> 隐藏推断边</label>
  </div>
  <div id="detail">
    <div id="placeholder">点击节点查看详情</div>
  </div>
</div>

<script>
const rawNodes = {nodes_json};
const rawEdges = {edges_json};

const nodeMap = {{}};
rawNodes.forEach(n => nodeMap[n.id] = n);

const nodes = new vis.DataSet(rawNodes.map(n => ({{
  id: n.id,
  label: n.label,
  color: {{ background: n.color, border: n.color, highlight: {{ background: "#fff", border: "#fff" }} }},
  shape: n.shape,
  size: 14,
  font: {{ color: "#eee", size: 12 }},
}})));

let currentEdges = rawEdges;
const edges = new vis.DataSet(rawEdges.map((e, i) => ({{
  id: i,
  from: e.from,
  to: e.to,
  color: {{ color: e.color, highlight: "#fff" }},
  dashes: e.dashes,
  width: e.width,
  title: e.type === "INFERRED" ? "推断关联 (共享tags: " + (e.shared_tags||[]).join(", ") + ")" : "显式链接",
}})));

const container = document.getElementById("graph");
const network = new vis.Network(container, {{ nodes, edges }}, {{
  physics: {{ solver: "forceAtlas2Based", forceAtlas2Based: {{ gravitationalConstant: -60 }}, stabilization: {{ iterations: 200 }} }},
  interaction: {{ hover: true, tooltipDelay: 200 }},
}});

network.on("click", params => {{
  if (!params.nodes.length) return;
  const id = params.nodes[0];
  const node = nodeMap[id];
  const neighbors = rawEdges
    .filter(e => e.from === id || e.to === id)
    .map(e => e.from === id ? e.to : e.from)
    .filter((v, i, a) => a.indexOf(v) === i);

  document.getElementById("detail").innerHTML = `
    <div class="title">${{node.label}}</div>
    <div class="type">${{node.type}}</div>
    <div class="summary">${{node.summary || "（无摘要）"}}</div>
    <div class="tags">${{(node.tags||[]).map(t => `<span class="tag">${{t}}</span>`).join("")}}</div>
    <div class="neighbors">
      <h3>关联页面（${{neighbors.length}}）</h3>
      ${{neighbors.map(n => `<span class="neighbor-link" onclick="focusNode('${{n}}')">${{nodeMap[n]?.label || n}}</span>`).join("")}}
    </div>
  `;
}});

function focusNode(id) {{
  network.focus(id, {{ scale: 1.2, animation: true }});
  network.selectNodes([id]);
  network.emit("click", {{ nodes: [id], edges: [] }});
}}

document.getElementById("hide-inferred").addEventListener("change", function() {{
  if (this.checked) {{
    edges.clear();
    edges.add(rawEdges.filter(e => e.type !== "INFERRED").map((e, i) => ({{
      id: i, from: e.from, to: e.to, color: {{ color: e.color }}, dashes: false, width: e.width
    }})));
  }} else {{
    edges.clear();
    edges.add(rawEdges.map((e, i) => ({{
      id: i, from: e.from, to: e.to, color: {{ color: e.color }}, dashes: e.dashes, width: e.width
    }})));
  }}
}});
</script>
</body>
</html>"""


# ─── 图谱健康报告 ──────────────────────────────────────────────────────────────

def build_report(graph: dict, pages: dict[str, Path]) -> str:
    from collections import Counter
    nodes = graph["nodes"]
    edges = graph["edges"]
    stats = graph["stats"]

    # 连接度统计
    degree: dict[str, int] = Counter()
    for e in edges:
        degree[e["from"]] += 1
        degree[e["to"]] += 1

    # 孤立节点（无任何边）
    isolates = [n["id"] for n in nodes if degree.get(n["id"], 0) == 0]

    # hub 节点前 10
    hubs = sorted(nodes, key=lambda n: degree.get(n["id"], 0), reverse=True)[:10]

    # 类型分布
    type_count: dict[str, int] = Counter(n["type"] for n in nodes)

    lines = [
        f"# 图谱健康报告 — {graph['generated']}",
        "",
        "## 统计",
        f"- 节点数：{stats['nodes']}",
        f"- 显式边：{stats['explicit_edges']}",
        f"- 推断边：{stats['inferred_edges']}",
        "",
        "## 节点类型分布",
    ]
    for t, c in sorted(type_count.items()):
        lines.append(f"- {t}：{c}")

    lines += ["", "## Hub 节点（连接度 Top 10）", "| 节点 | 类型 | 连接度 |", "|------|------|--------|"]
    for n in hubs:
        d = degree.get(n["id"], 0)
        lines.append(f"| {n['label']} | {n['type']} | {d} |")

    if isolates:
        lines += ["", "## 孤立节点（无边）"]
        for s in isolates:
            label = next((n["label"] for n in nodes if n["id"] == s), s)
            lines.append(f"- {label} (`{s}`)")
    else:
        lines += ["", "## 孤立节点", "无 ✅"]

    return "\n".join(lines) + "\n"


# ─── 主入口 ────────────────────────────────────────────────────────────────────

def run(infer: bool = True, report: bool = False, open_browser: bool = False):
    GRAPH_DIR.mkdir(exist_ok=True)
    pages = build_page_map()

    if not pages:
        print("❌ wiki/ 中没有页面，请先运行 /wiki-ingest")
        return 1

    print(f"构建图：{len(pages)} 个页面")
    graph = build_graph(pages, infer=infer)

    stats = graph["stats"]
    print(f"  显式边：{stats['explicit_edges']}")
    print(f"  推断边：{stats['inferred_edges']}")

    # 写入 graph.json
    json_path = GRAPH_DIR / "graph.json"
    json_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  → {json_path.relative_to(KB_ROOT)}")

    # 写入 graph.html
    html_path = GRAPH_DIR / "graph.html"
    html_path.write_text(generate_html(graph), encoding="utf-8")
    print(f"  → {html_path.relative_to(KB_ROOT)}")

    # 可选：生成健康报告
    if report:
        report_path = GRAPH_DIR / "graph-report.md"
        report_path.write_text(build_report(graph, pages), encoding="utf-8")
        print(f"  → {report_path.relative_to(KB_ROOT)}")

    print(f"\n✅ 知识图谱已生成，用浏览器打开：\n   {html_path.resolve()}")

    if open_browser:
        import subprocess, platform
        cmd = "start" if platform.system() == "Windows" else ("open" if platform.system() == "Darwin" else "xdg-open")
        subprocess.Popen([cmd, str(html_path.resolve())], shell=(platform.system() == "Windows"))

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="构建知识图谱（从 [[wikilinks]] + 共享 tags）")
    parser.add_argument("--wiki", metavar="PATH", help="wiki 目录（任一，绝对或相对路径，如 works/heroic_saga/01_source_and_script/wiki）")
    parser.add_argument("--no-infer", action="store_true", help="跳过 tag 语义推断，只保留显式边")
    parser.add_argument("--report", action="store_true", help="生成图谱健康报告到 graph/graph-report.md")
    parser.add_argument("--open", action="store_true", help="构建完成后自动打开浏览器")
    args = parser.parse_args()
    if args.wiki:
        set_kb(args.wiki)
    sys.exit(run(infer=not args.no_infer, report=args.report, open_browser=args.open))
