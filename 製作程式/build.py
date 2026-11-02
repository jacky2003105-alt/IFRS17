#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notes.md -> ../index.html

單一內容來源是 notes.md，index.html 是產物，直接改會被覆蓋。
用法：python3 build.py
"""
import html
import json
import re
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC.parent / "index.html"

# ---------------------------------------------------------------- 行內語法

MATH_RE = re.compile(r"\$([^$\n]+)\$")


def mathify(s):
    """$...$ 用一個等寬襯線樣式呈現；沒有外部套件，離線可讀。"""
    return MATH_RE.sub(lambda m: '<span class="m">' + m.group(1) + "</span>", s)


def inline(s):
    s = html.escape(s)
    # 先把行內算式抽出來，避免底下的 ** 與連結規則動到它
    tokens = []

    def stash(m):
        tokens.append('<span class="m">' + m.group(1) + "</span>")
        return f"@@T{len(tokens)-1}@@"

    s = MATH_RE.sub(stash, s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # 第 NN 節 -> 可點的章節連結
    s = re.sub(r"第 (\d\d) 節", r'<a class="xref" href="#s\1">第 \1 節</a>', s)
    for i, t in enumerate(tokens):
        s = s.replace(f"@@T{i}@@", t)
    return s


# ---------------------------------------------------------------- 區塊語法

TAGBOX = {
    "數字｜": ("figurebox", "數字"),
    "面試｜": ("tipbox", "面試這樣講"),
    "陷阱｜": ("trapbox", "常見誤解"),
    "法規｜": ("lawbox", "法規原文"),
}


def table(block):
    rows = [r.strip().strip("|").split("|") for r in block.splitlines()]
    rows = [r for r in rows if not all(re.fullmatch(r"[ :\-]+", c) for c in r)]
    out = ['<div class="table-wrap"><table>']
    for i, r in enumerate(rows):
        tag = "th" if i == 0 else "td"
        out.append("<tr>" + "".join(f"<{tag}>{inline(c.strip())}</{tag}>" for c in r) + "</tr>")
    out.append("</table></div>")
    return "".join(out)


def render(body):
    chunks = []
    qa = None
    for block in body.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue

        if block.startswith("### "):
            chunks.append("<h3>" + inline(block[4:]) + "</h3>")

        elif block.startswith("Q｜"):
            # 面試題：題目 + 中文擬答 + 英文擬答
            parts = {"q": [], "zh": [], "en": []}
            cur = "q"
            for ln in block.split("\n"):
                ln = ln.strip()
                if ln.startswith("Q｜"):
                    cur = "q"; ln = ln[2:].strip()
                elif ln.startswith("中｜"):
                    cur = "zh"; ln = ln[2:].strip()
                elif ln.startswith("英｜"):
                    cur = "en"; ln = ln[2:].strip()
                if ln:
                    parts[cur].append(ln)
            qbody = "".join("<p>" + inline(l) + "</p>" for l in parts["q"])
            zh = "".join("<p>" + inline(l) + "</p>" for l in parts["zh"])
            en = "".join("<p>" + inline(l) + "</p>" for l in parts["en"])
            chunks.append(
                '<div class="qa"><div class="q"><span class="tag">Q</span>' + qbody + "</div>"
                '<div class="ans"><div class="a zh"><span class="tag">中文擬答</span>' + zh + "</div>"
                '<div class="a en"><span class="tag">English</span>' + en + "</div></div></div>"
            )

        elif block[:3] in TAGBOX:
            cls, label = TAGBOX[block[:3]]
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            lines[0] = lines[0][3:].strip()
            inner = "".join("<p>" + inline(l) + "</p>" for l in lines if l)
            chunks.append(f'<div class="{cls}"><span class="tag">{label}</span>{inner}</div>')

        elif block.startswith("> "):
            inner = "<br>".join(inline(l[2:].strip()) for l in block.splitlines())
            chunks.append("<blockquote>" + inner + "</blockquote>")

        elif block.startswith("|"):
            chunks.append(table(block))

        elif block.startswith("- ") or block.startswith("1. "):
            ol = block.startswith("1. ")
            items = []
            for l in block.split("\n"):
                l = l.strip()
                l = re.sub(r"^(?:- |\d+\. )", "", l)
                items.append("<li>" + inline(l) + "</li>")
            chunks.append(("<ol>" if ol else "<ul>") + "".join(items) + ("</ol>" if ol else "</ul>"))

        else:
            chunks.append("<p>" + inline(block) + "</p>")
    return "\n".join(chunks)


# ---------------------------------------------------------------- 組裝

raw = (SRC / "notes.md").read_text(encoding="utf-8")
parts = re.split(r"^## ", raw, flags=re.M)
head = parts[0].strip()
title = re.search(r"^# (.+)$", head, re.M).group(1).strip()

sections = []
for part in parts[1:]:
    line, _, body = part.partition("\n")
    num = line[:2]
    sections.append((num, line.strip(), render(body)))

nav = "".join(f'<option value="#s{n}">{t}</option>' for n, t, _ in sections)
arts = "\n".join(
    f'<article class="unit" id="s{n}"><div class="unit-label">第 {n} 節</div>'
    f"<h2>{inline(t.split('｜', 1)[1] if '｜' in t else t)}</h2>{b}</article>"
    for n, t, b in sections
)

CSS = """
:root{--ink:#17222e;--blue:#1f4e79;--accent:#b4532a;--muted:#5a6672;--line:#dde4ea;--bg:#f3f5f7}
*{box-sizing:border-box}
html{scroll-padding-top:96px}
body{margin:0;color:var(--ink);background:var(--bg);line-height:1.9;font-size:17.5px;
 font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans CJK TC",sans-serif}
header{max-width:1080px;margin:0 auto;padding:56px 44px 30px}
.eyebrow{font-size:12px;letter-spacing:.16em;color:var(--blue);font-weight:650}
h1{font-size:44px;line-height:1.25;margin:16px 0 10px;letter-spacing:.03em}
.lede{color:var(--muted);font-size:16px;max-width:860px}
nav{position:sticky;top:0;z-index:20;background:#fffffff2;backdrop-filter:blur(10px);
 border-block:1px solid var(--line);padding:11px max(16px,calc((100vw - 1024px)/2));
 display:flex;gap:10px;align-items:center;flex-wrap:wrap}
nav label{font-size:13px;white-space:nowrap}
select{flex:1;min-width:0;max-width:620px}
button,select{font:inherit;font-size:13px;color:var(--ink);background:#fff;
 border:1px solid #c3d0db;border-radius:6px;padding:8px 11px}
button{cursor:pointer;white-space:nowrap}
button:hover{background:#eaf1f7}
main{max-width:1080px;margin:28px auto;padding:0 22px}
.unit{background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:34px 42px;margin-bottom:24px;scroll-margin-top:96px;overflow:hidden}
.unit-label{font-size:11px;letter-spacing:.16em;color:var(--blue);font-weight:650}
.unit h2{font-size:26px;line-height:1.45;margin:8px 0 22px}
.unit h3{font-size:17.5px;color:var(--blue);margin:28px 0 10px;padding-top:11px;
 border-top:1px solid var(--line)}
p{margin:13px 0}
ul,ol{margin:13px 0;padding-left:1.4em}
li{margin:6px 0}
strong{font-weight:650}
p strong{background:linear-gradient(transparent 64%,#dbe9f5 64%)}
code{background:#eef2f6;border-radius:4px;padding:1px 5px;font-size:.9em}
.m{font-family:"Latin Modern Math","Cambria Math",Georgia,serif;font-style:italic;
 background:#f6f8fa;border-radius:4px;padding:1px 5px;font-size:1.02em;white-space:nowrap}
.table-wrap{overflow-x:auto;margin:20px 0}
table{border-collapse:collapse;width:100%;font-size:15.5px;line-height:1.75}
th,td{border-bottom:1px solid var(--line);padding:11px 13px;text-align:left;vertical-align:top}
th{background:#eaf1f7;font-weight:650;white-space:nowrap}
tr:nth-child(even) td{background:#fafbfc}
blockquote{margin:18px 0;padding:13px 19px;background:#f4f8fb;border-left:3px solid var(--blue);
 border-radius:0 8px 8px 0;font-size:16px;color:#23445e}
.tag{display:inline-block;font-size:11px;font-weight:650;letter-spacing:.09em;padding:2px 9px;
 border-radius:999px;margin-right:9px;vertical-align:2px;white-space:nowrap}
.figurebox,.tipbox,.trapbox,.lawbox{padding:13px 19px;border-radius:0 8px 8px 0;margin:19px 0}
.figurebox{background:#f2f8f4;border-left:3px solid #3f8f63}
.figurebox .tag{background:#d8ece0;color:#1f6341}
.tipbox{background:#fdf6ee;border-left:3px solid #c08a3e}
.tipbox .tag{background:#f5e3c9;color:#8a5a18}
.trapbox{background:#fdf2f0;border-left:3px solid var(--accent)}
.trapbox .tag{background:#f6dcd4;color:#8e3417}
.lawbox{background:#f1f3f8;border-left:3px solid #5a63a8}
.lawbox .tag{background:#dfe2f0;color:#3c4382}
.figurebox p,.tipbox p,.trapbox p,.lawbox p{margin:7px 0}
.qa{border:1.5px solid #c3d0db;border-radius:10px;margin:22px 0;overflow:hidden}
.qa .q{background:#eef4f9;padding:14px 20px}
.qa .q .tag{background:var(--blue);color:#fff}
.qa .q p{margin:6px 0;font-weight:600}
.qa .ans{padding:4px 20px 12px}
.qa .a{margin:12px 0;padding-left:14px;border-left:2px solid var(--line)}
.qa .a.zh .tag{background:#e3ecf4;color:#1f4e79}
.qa .a.en{font-size:16px}
.qa .a.en .tag{background:#e8e4f0;color:#4d3f7a}
.qa .a.en p{color:#2d3c4a}
.xref{color:var(--blue);text-decoration-style:dotted;text-underline-offset:3px}
a{color:var(--blue);overflow-wrap:anywhere}
.hidden{display:none!important}
footer{text-align:center;color:var(--muted);font-size:13px;padding:26px}
@media(max-width:680px){
 body{font-size:16.5px}
 header{padding:30px 18px 22px} h1{font-size:32px}
 main{padding:0 11px} .unit{padding:22px 18px} .unit h2{font-size:21px}
 nav{padding:9px 11px} select{width:100%;max-width:none}
 .qa .q,.qa .ans{padding-left:14px;padding-right:14px}
}
@media print{nav,header,footer{display:none}body{background:#fff}
 .unit{break-inside:avoid;border:0;padding:0 0 18px}}
"""

JS = """
document.getElementById('jump').onchange=function(){if(this.value)location.hash=this.value};
(function(){
 var hideA=false, hideE=false;
 var bA=document.getElementById('toggleAns'), bE=document.getElementById('toggleEn');
 bA.onclick=function(){hideA=!hideA;bA.textContent=hideA?'顯示擬答':'隱藏擬答（自我測驗）';
  document.querySelectorAll('.qa .ans').forEach(function(e){e.classList.toggle('hidden',hideA)});};
 bE.onclick=function(){hideE=!hideE;bE.textContent=hideE?'顯示英文':'只看中文';
  document.querySelectorAll('.qa .a.en').forEach(function(e){e.classList.toggle('hidden',hideE)});};
})();
"""

doc = f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
<header>
<div class="eyebrow">精算實習 ＋ 研究所面試準備</div>
<h1>{html.escape(title)}</h1>
<p class="lede">{inline(head.split(chr(10))[-1].strip()) if chr(10) in head else ''}</p>
</header>
<nav>
<label for="jump">跳到</label>
<select id="jump"><option value="">— 選一節 —</option>{nav}</select>
<button id="toggleAns">隱藏擬答（自我測驗）</button>
<button id="toggleEn">只看中文</button>
</nav>
<main>
{arts}
</main>
<footer>依公開資料與課堂講義整理；數字與法規以原始來源為準。</footer>
<script>{JS}</script>
</html>
"""

OUT.write_text(doc, encoding="utf-8")
stats = {
    "sections": len(sections),
    "qa": doc.count('class="qa"'),
    "tables": doc.count("<table>"),
    "chars": len(raw),
}
print(json.dumps(stats, ensure_ascii=False))
