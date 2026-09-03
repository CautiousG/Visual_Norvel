# -*- coding: utf-8 -*-
# 把解压后的 epub 章节 HTML 按 spine 顺序转成分卷 markdown + 索引
import os, re, html
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
EPUB = os.path.join(BASE, "_tmp_epub")
OPF  = None
for root, _, files in os.walk(EPUB):
    for f in files:
        if f.endswith(".opf"):
            OPF = os.path.join(root, f)
OPF_DIR = os.path.dirname(OPF)
OUT = os.path.join(BASE, "source", "text")
os.makedirs(OUT, exist_ok=True)

opf = open(OPF, encoding="utf-8").read()
# manifest: id -> href
manifest = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', opf))
manifest.update(dict((i, h) for h, i in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', opf)))
# spine order
spine = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)

class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.head = None; self.paras = []
        self._buf = []; self._tag = None
    def handle_starttag(self, tag, attrs):
        if tag in ("h1","h2","h3","h4","p"):
            self._tag = tag; self._buf = []
    def handle_data(self, data):
        if self._tag: self._buf.append(data)
    def handle_endtag(self, tag):
        if tag == self._tag:
            txt = html.unescape("".join(self._buf))
            txt = re.sub(r"\s+", " ", txt).strip()   # 归一化空白，保留词间单空格
            if tag in ("h1","h2","h3","h4"):
                if txt and self.head is None: self.head = txt
            elif tag == "p" and txt:
                self.paras.append(txt)
            self._tag = None; self._buf = []

VOL_RE = re.compile(r"第[一二三四五六七八九十百零〇\d]+卷")
def parse(path):
    e = Extract(); e.feed(open(path, encoding="utf-8").read())
    return e.head or "", e.paras

vols = []            # list of dict(title, chapters=[(chtitle, paras, id)])
cur = {"title": "卷首（封面·楔子）", "id": "vol00", "chapters": []}
vols.append(cur)

for idref in spine:
    href = manifest.get(idref)
    if not href: continue
    path = os.path.normpath(os.path.join(OPF_DIR, href))
    if not os.path.exists(path): continue
    head, paras = parse(path)
    base = os.path.basename(path)
    if base in ("coverpage.html",) or head in ("封面","总目录","目录"):
        continue
    if VOL_RE.match(head):                          # 卷分隔页（标题为「第X卷…」，正文是迷你目录，丢弃）
        cur = {"title": head, "id": "vol%02d" % len(vols), "chapters": []}
        vols.append(cur)
        continue
    if not paras and not head:
        continue
    cur["chapters"].append((head or base, paras))

# 丢掉空卷
vols = [v for v in vols if v["chapters"]]

# 写分卷 md
index_lines = ["# 《英雄志》全文索引", "",
               "> 由 source/英雄志.epub 转换。仅本地自用，勿传播。", "",
               "| 卷 | 文件 | 章数 | 约字数 |", "|----|------|------|--------|"]
total_chars = 0
for i, v in enumerate(vols):
    fn = "vol%02d.md" % i
    lines = ["# " + v["title"], ""]
    vchars = 0
    for chtitle, paras in v["chapters"]:
        lines.append("## " + chtitle); lines.append("")
        for p in paras:
            lines.append(p); lines.append("")
        vchars += sum(len(p) for p in paras)
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write("\n".join(lines))
    total_chars += vchars
    index_lines.append("| %s | %s | %d | %s |" %
                       (v["title"], fn, len(v["chapters"]), format(vchars, ",")))

index_lines += ["", "**合计约 %s 字，%d 卷。**" % (format(total_chars, ","), len(vols))]
# 每卷章节明细
index_lines += ["", "## 章节明细"]
for i, v in enumerate(vols):
    index_lines.append("")
    index_lines.append("### %s  (vol%02d.md)" % (v["title"], i))
    for chtitle, _ in v["chapters"]:
        index_lines.append("- " + chtitle)
open(os.path.join(OUT, "index.md"), "w", encoding="utf-8").write("\n".join(index_lines))

print("卷数:", len(vols), " 总字数:", format(total_chars, ","))
for i, v in enumerate(vols):
    print("  vol%02d  %-16s 章数 %d" % (i, v["title"], len(v["chapters"])))
