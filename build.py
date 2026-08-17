# -*- coding: utf-8 -*-
"""
Builds index.html and features.csv from roadmap.json.

The page is generated rather than hand-written for one reason: there are 86
features and every one of them carries a dependency list that has to agree with
the stage it sits in. Hand-transcribing that is how a roadmap ends up claiming
an order its own table contradicts.
"""

import csv
import io
import json
import re
from html import escape as esc

ROOT = "C:/Users/D1081493/Desktop/resomap-roadmap"
RM = json.load(io.open(f"{ROOT}/roadmap.json", encoding="utf-8"))

STAGES = RM["stages"]
FEATURES = RM["features"]
BY_ID = {f["id"]: f for f in FEATURES}
TS = ["T0", "T1", "T2", "T3", "T4", "T5"]
ORDER = {t: i for i, t in enumerate(TS)}

# ---------------------------------------------------------------- validation

violations, dangling = [], []
for f in FEATURES:
    for d in f["depends_on"]:
        if d not in BY_ID:
            dangling.append((f["id"], d))
        elif ORDER[BY_ID[d]["t"]] >= ORDER[f["t"]]:
            violations.append((f["id"], d))
assert not violations, f"stage ordering violated: {violations}"
assert not dangling, f"dangling dependency: {dangling}"

# What each feature unblocks — the reverse edge, which is the interesting one
# for a reader asking "why is this so early".
UNBLOCKS = {f["id"]: [] for f in FEATURES}
for f in FEATURES:
    for d in f["depends_on"]:
        UNBLOCKS[d].append(f["id"])

# ------------------------------------------------------------------- cleanup

def fix_maturity(stage, line):
    """
    T0 earns nothing at all, but the schema's lowest rung is 開始驗證, so the
    assembling agent corrected it in prose inside precondition_zh. Reading the
    correction is the reader's job in a data file; on a page it is just a label
    that contradicts the sentence under it. Promote the correction to the label.
    """
    pre = line["precondition_zh"]
    if "列舉值中最低一級" in pre or stage["t"] == "T0":
        pre = re.sub(r"^實際狀態是尚未開始[^：]*：\s*", "", pre)
        return "尚未開始", pre
    return line["maturity"], pre


MATURITY_TONE = {
    "尚未開始": "none",
    "開始驗證": "probe",
    "開始有收入": "start",
    "主要收入": "main",
    "規模化": "scale",
}

STATUS_TONE = {"已完成": "done", "部分完成": "partial", "未開始": "todo"}
ROLE_TONE = {"直接變現": "rev", "變現前提": "pre", "留存": "keep", "無": "neutral"}

# --------------------------------------------------------------- critical path

# Read off critical_path_zh. Each node is placed in the T column it actually
# ships in, so the diagram is a claim the feature table can be checked against
# rather than a decoration.
CHAINS = [
    ("原生能力鏈", ["backend-db", "user-accounts", "native-app-store", "background-location", "in-trip-deals"]),
    ("歸因鏈", ["backend-db", "user-accounts", "server-side-attribution", "postback-reconciliation", "revenue-dashboard"]),
    ("主動性鏈", ["backend-db", "external-data-feeds", "adapt-auto-trigger", "proactivity-rules", "in-trip-deals"]),
    ("規劃鏈", ["backend-db", "poi-database-backend", "itinerary-generator", "stay-gap-booking"]),
    ("變現鏈", ["affiliate-accounts", "real-deep-links", "server-side-attribution", "postback-reconciliation", "revenue-dashboard"]),
]
for label, ids in CHAINS:
    for i in ids:
        assert i in BY_ID, f"critical path names an unknown feature: {i} ({label})"
    for a, b in zip(ids, ids[1:]):
        assert ORDER[BY_ID[a]["t"]] < ORDER[BY_ID[b]["t"]], f"{label}: {a} -> {b} not forward"

# ------------------------------------------------------------------------ CSS

CSS = """
*,*::before,*::after{box-sizing:border-box}

:root{
  --bg:#ffffff; --surface:#f7f6f4; --surface-2:#eeece8; --sink:#faf9f7;
  --line:#e5e3df; --line-strong:#d2cfc8;
  --ink:#16150f; --ink-2:#55514a; --ink-3:#767066;
  --brand:#e0530b; --brand-deep:#b8420a; --brand-ink:#ffffff; --brand-wash:#fff2e9;
  --done:#0e7a56; --done-wash:#e7f4ee;
  --partial:#a4530a; --partial-wash:#fdf1e2;
  --todo:#6b6559; --todo-wash:#f0efec;
  --shadow:0 1px 2px rgba(22,21,15,.05);
  --mono:ui-monospace,"SFMono-Regular","Cascadia Mono","Roboto Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",
         "Microsoft JhengHei","Hiragino Sans",Roboto,Arial,sans-serif;
}

/* The un-stamped document is the common case — most readers never touch a
   theme toggle, so the OS query has to carry the dark palette on its own, and
   the :not() guard is what keeps an explicit light choice winning over it. */
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#131210; --surface:#1b1a16; --surface-2:#24221d; --sink:#191814;
    --line:#2d2a24; --line-strong:#3e3a32;
    --ink:#f2f0ea; --ink-2:#b3aea3; --ink-3:#928c80;
    --brand:#ff8140; --brand-deep:#ff8140; --brand-ink:#1a0d04; --brand-wash:#2e1a0c;
    --done:#5cc79a; --done-wash:#12291f;
    --partial:#e0a05a; --partial-wash:#2c2013;
    --todo:#928c80; --todo-wash:#211f1a;
    --shadow:0 1px 2px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  --bg:#131210; --surface:#1b1a16; --surface-2:#24221d; --sink:#191814;
  --line:#2d2a24; --line-strong:#3e3a32;
  --ink:#f2f0ea; --ink-2:#b3aea3; --ink-3:#928c80;
  --brand:#ff8140; --brand-deep:#ff8140; --brand-ink:#1a0d04; --brand-wash:#2e1a0c;
  --done:#5cc79a; --done-wash:#12291f;
  --partial:#e0a05a; --partial-wash:#2c2013;
  --todo:#928c80; --todo-wash:#211f1a;
  --shadow:0 1px 2px rgba(0,0,0,.35);
}

body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:var(--sans); font-size:15.5px; line-height:1.85;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}
.num,td.n,.t-tok{font-variant-numeric:tabular-nums}

.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
.prose{max-width:66ch}

h1,h2,h3,h4{text-wrap:balance;margin:0;line-height:1.3;font-weight:800}
p{margin:0}

/* ------------------------------------------------------------------ masthead */
.mast{padding:72px 0 44px;border-bottom:1px solid var(--line)}
.eyebrow{
  font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);
}
.mast h1{font-size:clamp(30px,5.2vw,46px);letter-spacing:-.02em;margin-top:14px}
.mast .lede{margin-top:18px;font-size:17px;line-height:1.8;color:var(--ink-2);max-width:60ch}
.mast .meta{
  margin-top:28px;display:flex;flex-wrap:wrap;gap:10px 26px;
  font-size:13px;color:var(--ink-3);
}
.mast .meta b{color:var(--ink-2);font-weight:600}

section{padding:56px 0;border-bottom:1px solid var(--line)}
section > .wrap > h2{
  font-size:25px;letter-spacing:-.01em;
  display:flex;align-items:baseline;gap:12px;
}
h2 .idx{
  font-family:var(--mono);font-size:12px;font-weight:600;
  color:var(--brand-deep);letter-spacing:.1em;
}
.sub{margin-top:10px;color:var(--ink-2);font-size:14.5px;max-width:64ch}

/* -------------------------------------------------------------- stage strip */
.strip{
  margin-top:30px;display:grid;gap:2px;
  grid-template-columns:repeat(6,minmax(0,1fr));
  background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;
}
.strip .cell{background:var(--bg);padding:16px 14px 18px;display:flex;flex-direction:column;gap:7px}
.strip .t-tok{
  font-family:var(--mono);font-size:12.5px;font-weight:700;letter-spacing:.06em;color:var(--brand-deep);
}
.strip .nm{font-size:15px;font-weight:700;line-height:1.35}
.strip .cap{font-size:12.5px;line-height:1.6;color:var(--ink-3)}
.strip .cnt{
  margin-top:auto;padding-top:8px;font-family:var(--mono);font-size:11px;color:var(--ink-3);
}

/* --------------------------------------------------------------- rationale */
.rationale p{margin-top:18px;color:var(--ink-2)}
.rationale p:first-child{margin-top:0}
.rationale strong{color:var(--ink);font-weight:700}

.pull{
  margin:30px 0 0;padding:20px 22px;border-left:3px solid var(--brand);
  background:var(--brand-wash);border-radius:0 10px 10px 0;
}
.pull .k{
  font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--brand-deep);font-weight:700;
}
.pull p{margin-top:8px;font-size:15px;color:var(--ink)}

/* ------------------------------------------------------------ chain diagram */
.chains{margin-top:28px;overflow-x:auto;padding-bottom:6px}
.chains-inner{min-width:940px}
.chain-head{
  display:grid;grid-template-columns:104px repeat(6,minmax(0,1fr));gap:0;
  border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:4px;
}
.chain-head span{
  font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--ink-3);
}
.chain-row{
  display:grid;grid-template-columns:104px repeat(6,minmax(0,1fr));
  align-items:center;padding:7px 0;border-bottom:1px solid var(--line);
}
.chain-row:last-child{border-bottom:0}
.chain-row .lbl{font-size:12.5px;font-weight:700;color:var(--ink-2);padding-right:12px}
.node{
  position:relative;margin-right:9px;padding:7px 10px;border-radius:8px;
  background:var(--surface);border:1px solid var(--line);
  font-size:12px;line-height:1.35;color:var(--ink);
}
.node.sink{background:var(--brand-wash);border-color:var(--brand);color:var(--ink);font-weight:700}
.node.root{background:var(--surface-2);border-color:var(--line-strong);font-weight:700}
/* The arrow is drawn from the node it leaves, so a gap in the row is a real
   gap in the chain rather than a stray connector pointing at nothing. */
.node.hasnext::after{
  content:"";position:absolute;right:-9px;top:50%;width:9px;height:1px;
  background:var(--line-strong);
}
.node.hasnext::before{
  content:"";position:absolute;right:-9px;top:50%;transform:translateY(-50%);
  border-left:4px solid var(--line-strong);border-top:3px solid transparent;
  border-bottom:3px solid transparent;
}

/* -------------------------------------------------------------- stage cards */
.stage{padding:60px 0;border-bottom:1px solid var(--line)}
.stage:last-of-type{border-bottom:0}
.stage-head{display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap}
.tbadge{
  flex:0 0 auto;width:66px;height:66px;border-radius:16px;
  background:var(--brand);color:var(--brand-ink);
  display:grid;place-items:center;font-family:var(--mono);font-size:22px;font-weight:700;
  letter-spacing:-.02em;
}
.stage[data-t="T0"] .tbadge{background:var(--surface-2);color:var(--ink-2)}
.stage-head .txt{flex:1 1 320px;min-width:0}
.stage-head h3{font-size:27px;letter-spacing:-.015em}
.stage-head .cap{margin-top:10px;font-size:16px;line-height:1.75;color:var(--ink-2);max-width:62ch}

.blocks{margin-top:26px;display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.block{background:var(--sink);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.block.why{border-left:3px solid var(--brand)}
.block h4{
  font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);font-weight:700;
}
.block p{margin-top:9px;font-size:14px;line-height:1.8;color:var(--ink-2)}
.block.why p{color:var(--ink)}

ul.ticks{margin:9px 0 0;padding:0;list-style:none}
ul.ticks li{
  position:relative;padding-left:18px;margin-top:7px;font-size:13.5px;
  line-height:1.75;color:var(--ink-2);
}
ul.ticks li::before{
  content:"";position:absolute;left:2px;top:.72em;width:5px;height:5px;
  border-radius:50%;background:var(--ink-3);
}

/* ------------------------------------------------------------ revenue lines */
.rev{margin-top:22px;display:grid;gap:10px}
.rev-item{
  background:var(--bg);border:1px solid var(--line);border-radius:12px;
  padding:15px 18px;box-shadow:var(--shadow);
}
.rev-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.rev-top .nm{font-size:15px;font-weight:700}
.rev-item p{margin-top:8px;font-size:13.5px;line-height:1.78;color:var(--ink-2)}
.rev-item .pre{
  margin-top:10px;padding-top:10px;border-top:1px dashed var(--line);
  font-size:13px;color:var(--ink-2);
}
.rev-item .pre b{
  font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);display:block;margin-bottom:4px;font-weight:700;
}

.tag{
  display:inline-block;padding:2.5px 8px;border-radius:999px;
  font-size:11px;font-weight:700;line-height:1.6;white-space:nowrap;
  border:1px solid transparent;
}
.tag.none{background:var(--todo-wash);color:var(--todo);border-color:var(--line)}
.tag.probe{background:var(--partial-wash);color:var(--partial)}
.tag.start{background:var(--done-wash);color:var(--done)}
.tag.main{background:var(--brand-deep);color:var(--brand-ink)}
.tag.scale{background:var(--brand-wash);color:var(--brand-deep);border-color:var(--brand-deep)}
.tag.done{background:var(--done-wash);color:var(--done)}
.tag.partial{background:var(--partial-wash);color:var(--partial)}
.tag.todo{background:var(--todo-wash);color:var(--todo);border-color:var(--line)}
.tag.rev{background:var(--brand-wash);color:var(--brand-deep)}
.tag.pre{background:var(--surface-2);color:var(--ink-2)}
.tag.keep{background:var(--surface-2);color:var(--ink-2)}
.tag.neutral{background:transparent;color:var(--ink-3);border-color:var(--line)}

/* ------------------------------------------------------------------- tables */
.tablewrap{margin-top:22px;overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;min-width:880px;font-size:13.5px}
thead th{
  position:sticky;top:0;background:var(--surface);z-index:1;
  text-align:left;font-weight:700;font-size:11.5px;letter-spacing:.06em;
  color:var(--ink-2);padding:11px 13px;border-bottom:1px solid var(--line-strong);
  white-space:nowrap;
}
tbody td{padding:12px 13px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.65}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--sink)}
td.n{font-family:var(--mono);font-size:12px;color:var(--ink-3);white-space:nowrap}
td.nm{font-weight:700;min-width:112px}
td.one{color:var(--ink-2);min-width:270px}
td.dep{color:var(--ink-3);font-size:12.5px;min-width:200px}
td.dep .none{color:var(--ink-3);opacity:.6}

.stage-features{margin-top:26px}
.stage-features h4{
  font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);font-weight:700;
}
.fgrid{margin-top:12px;display:grid;gap:9px;grid-template-columns:repeat(auto-fill,minmax(268px,1fr))}
.fcard{
  background:var(--bg);border:1px solid var(--line);border-radius:11px;padding:13px 15px;
}
.fcard .top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.fcard .nm{font-size:14px;font-weight:700}
.fcard .eff{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin-left:auto}
.fcard .one{margin-top:6px;font-size:12.5px;line-height:1.7;color:var(--ink-2)}
.fcard .dep{
  margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);
  font-size:12px;line-height:1.7;color:var(--ink-3);
}

/* -------------------------------------------------------------------- risks */
.risks{margin-top:24px;display:grid;gap:12px}
.risk{
  background:var(--sink);border:1px solid var(--line);border-left:3px solid var(--partial);
  border-radius:0 11px 11px 0;padding:15px 18px;font-size:14px;line-height:1.8;color:var(--ink-2);
}

/* --------------------------------------------------------------- disclosure */
.note{
  margin-top:26px;padding:18px 20px;border:1px dashed var(--line-strong);border-radius:12px;
  font-size:13px;line-height:1.85;color:var(--ink-2);background:var(--sink);
}
.note b{color:var(--ink)}

footer{padding:44px 0 64px;font-size:12.5px;color:var(--ink-3);line-height:1.9}
footer a{color:var(--ink-2)}

@media (max-width:820px){
  .strip{grid-template-columns:repeat(2,minmax(0,1fr))}
  .mast{padding:48px 0 34px}
  section,.stage{padding:42px 0}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
}
@media print{
  .chains{overflow:visible}
  section,.stage{break-inside:avoid}
}
"""

# --------------------------------------------------------------------- render

def dep_names(f):
    if not f["depends_on"]:
        return '<span class="none">無前置依賴</span>'
    return "、".join(esc(BY_ID[d]["name_zh"]) for d in f["depends_on"])


def clip(text, n=54):
    """Cut at a clause boundary. A hard character count lands mid-phrase, which
    reads as a rendering fault rather than as an abbreviation."""
    if len(text) <= n:
        return text
    head = text[:n]
    cut = max(head.rfind(c) for c in "，、；：")
    return (head[:cut] if cut > n * 0.45 else head) + "…"


def stage_strip():
    out = ['<div class="strip">']
    for s in STAGES:
        n = sum(1 for f in FEATURES if f["t"] == s["t"])
        out.append(
            f'<div class="cell"><span class="t-tok">{s["t"]}</span>'
            f'<span class="nm">{esc(s["name_zh"])}</span>'
            f'<span class="cap">{esc(clip(s["goal_zh"]))}</span>'
            f'<span class="cnt">{n} 項功能</span></div>'
        )
    out.append("</div>")
    return "".join(out)


def chain_diagram():
    out = ['<div class="chains"><div class="chains-inner">']
    out.append('<div class="chain-head"><span></span>' + "".join(f"<span>{t}</span>" for t in TS) + "</div>")
    for label, ids in CHAINS:
        cells = {ORDER[BY_ID[i]["t"]]: i for i in ids}
        last_col = max(cells)
        row = [f'<div class="chain-row"><div class="lbl">{esc(label)}</div>']
        for col in range(6):
            fid = cells.get(col)
            if not fid:
                row.append("<div></div>")
                continue
            cls = "node"
            if col == min(cells):
                cls += " root"
            if col == last_col:
                cls += " sink"
            if col < last_col:
                cls += " hasnext"
            row.append(f'<div class="{cls}">{esc(BY_ID[fid]["name_zh"])}</div>')
        row.append("</div>")
        out.append("".join(row))
    out.append("</div></div>")
    return "".join(out)


def stage_section(s):
    t = s["t"]
    feats = [f for f in FEATURES if f["t"] == t]
    o = [f'<section class="stage" data-t="{t}" id="{t}"><div class="wrap">']
    o.append(
        f'<div class="stage-head"><div class="tbadge">{t}</div><div class="txt">'
        f'<h3>{esc(s["name_zh"])}</h3>'
        f'<p class="cap">{esc(s["headline_capability_zh"])}</p></div></div>'
    )

    o.append('<div class="blocks">')
    o.append(f'<div class="block why"><h4>為什麼是這一階</h4><p>{esc(s["why_here_zh"])}</p></div>')
    o.append(f'<div class="block"><h4>這一階要做到</h4><p>{esc(s["goal_zh"])}</p></div>')
    o.append(f'<div class="block"><h4>過關條件</h4><p>{esc(s["gate_zh"])}</p></div>')
    metrics = "".join(f"<li>{esc(m)}</li>" for m in s["proof_metrics_zh"])
    o.append(f'<div class="block"><h4>驗證指標</h4><ul class="ticks">{metrics}</ul></div>')
    o.append("</div>")

    o.append(f'<div class="block" style="margin-top:18px"><h4>商業模式</h4><p>{esc(s["business_model_zh"])}</p></div>')

    if s["revenue_lines"]:
        o.append('<div class="rev">')
        for ln in s["revenue_lines"]:
            mat, pre = fix_maturity(s, ln)
            o.append(
                f'<div class="rev-item"><div class="rev-top">'
                f'<span class="nm">{esc(ln["name_zh"])}</span>'
                f'<span class="tag {MATURITY_TONE[mat]}">{mat}</span></div>'
                f'<p>{esc(ln["mechanism_zh"])}</p>'
                f'<div class="pre"><b>要成立必須先為真</b>{esc(pre)}</div></div>'
            )
        o.append("</div>")

    o.append(f'<div class="stage-features"><h4>{t} 的 {len(feats)} 項功能</h4><div class="fgrid">')
    for f in feats:
        o.append(
            f'<div class="fcard"><div class="top">'
            f'<span class="nm">{esc(f["name_zh"])}</span>'
            f'<span class="tag {STATUS_TONE[f["status_today"]]}">{f["status_today"]}</span>'
            f'<span class="eff">{f["effort"]}</span></div>'
            f'<p class="one">{esc(f["one_line_zh"])}</p>'
            f'<div class="dep">依賴 · {dep_names(f)}</div></div>'
        )
    o.append("</div></div>")
    o.append("</div></section>")
    return "".join(o)


def full_table():
    o = ['<div class="tablewrap"><table><thead><tr>']
    for h in ["階段", "功能", "領域", "一句話", "今天的狀態", "依賴哪些功能", "為何不能更早", "變現角色", "工量"]:
        o.append(f"<th>{h}</th>")
    o.append("</tr></thead><tbody>")
    for f in sorted(FEATURES, key=lambda x: (ORDER[x["t"]], x["domain_zh"], x["name_zh"])):
        o.append(
            f'<tr><td class="n">{f["t"]}</td>'
            f'<td class="nm">{esc(f["name_zh"])}</td>'
            f'<td class="n">{esc(f["domain_zh"])}</td>'
            f'<td class="one">{esc(f["one_line_zh"])}</td>'
            f'<td><span class="tag {STATUS_TONE[f["status_today"]]}">{f["status_today"]}</span></td>'
            f'<td class="dep">{dep_names(f)}</td>'
            f'<td class="dep">{esc(f["why_it_must_wait_zh"])}</td>'
            f'<td><span class="tag {ROLE_TONE[f["revenue_role"]]}">{f["revenue_role"]}</span></td>'
            f'<td class="n">{f["effort"]}</td></tr>'
        )
    o.append("</tbody></table></div>")
    return "".join(o)


def paras(text):
    return "".join(f"<p>{esc(p.strip())}</p>" for p in text.split("\n") if p.strip())


counts = {t: sum(1 for f in FEATURES if f["t"] == t) for t in TS}
done = sum(1 for f in FEATURES if f["status_today"] == "已完成")
partial = sum(1 for f in FEATURES if f["status_today"] == "部分完成")

HTML = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ResoMap 產品路線圖 T0–T5</title>
<style>{CSS}</style>
</head>
<body>

<header class="mast"><div class="wrap">
  <div class="eyebrow">ResoMap · 產品路線圖 · 內部文件</div>
  <h1>從一支不需要伺服器的 Demo，<br>到每一塊錢都對得回一次點擊</h1>
  <p class="lede">
    這份路線圖不是把功能分成六桶。它是把 {len(FEATURES)} 個功能的依賴圖拓撲排序之後，
    在自然斷開的位置切下去——一個功能只會落在「它所有前置都已經存在」的最早那一階。
    所以順序不是偏好，是物理限制。
  </p>
  <div class="meta">
    <span><b>{len(FEATURES)}</b> 項功能</span>
    <span>今天已完成 <b>{done}</b> 項、部分完成 <b>{partial}</b> 項</span>
    <span>依賴檢查 <b>0</b> 違規 · <b>0</b> 斷鏈</span>
    <span>切法依據 <b>依賴性</b>，不是時間</span>
  </div>
</div></header>

<section><div class="wrap">
  <h2><span class="idx">01</span>六個階段</h2>
  <p class="sub">T0 是既成事實，由程式碼盤點讀出，不是計畫。T1 之後每一階都是「前一階存在了才做得出來」。</p>
  {stage_strip()}
</div></section>

<section><div class="wrap">
  <h2><span class="idx">02</span>為什麼這樣拆</h2>
  <div class="prose rationale">{paras(RM["split_rationale_zh"])}</div>
</div></section>

<section><div class="wrap">
  <h2><span class="idx">03</span>關鍵路徑</h2>
  <p class="sub">
    每個節點畫在它真正出貨的那一階。這不是一條七段的主鏈——是三條並行的鏈共用同一個根，
    在 T4／T5 交會。第四條是規劃鏈，第五條是變現鏈，後者的第一節是行政不是工程。
  </p>
  {chain_diagram()}
  <div class="prose rationale" style="margin-top:26px">{paras(RM["critical_path_zh"])}</div>
</div></section>

<section style="border-bottom:0;padding-bottom:0"><div class="wrap">
  <h2><span class="idx">04</span>逐階段</h2>
  <p class="sub">每一階都先回答「為什麼是這一階」，再談做什麼、怎麼算過關、怎麼賺錢、拿什麼證明。</p>
</div></section>

{''.join(stage_section(s) for s in STAGES)}

<section><div class="wrap">
  <h2><span class="idx">05</span>這個切法最容易在哪裡出錯</h2>
  <p class="sub">寫在這裡是因為這些問題不會因為沒寫就消失，而且其中兩條會直接改變路線圖的形狀。</p>
  <div class="risks">
    {''.join(f'<div class="risk">{esc(r)}</div>' for r in RM["risks_zh"])}
  </div>
</div></section>

<section><div class="wrap">
  <h2><span class="idx">06</span>完整功能表</h2>
  <p class="sub">
    {len(FEATURES)} 項全列。「依賴哪些功能」那一欄是這份文件的骨架——
    表裡每一列的依賴，階段一定都比它自己早。同樣的內容有一份 features.csv，可直接匯入試算表或 Notion。
  </p>
  {full_table()}
</div></section>

<section style="border-bottom:0"><div class="wrap">
  <h2><span class="idx">07</span>本文件的誠實界線</h2>
  <div class="note">
    <p><b>ResoMap 目前與 Klook、KKday、Booking.com、Agoda、Trip.com 皆無任何合作關係。</b>
    這份文件裡所有「聯盟」都是指向各平台的<b>公開聯盟計畫申請</b>——需要逐一送審、可能被拒，
    不是合作、不是策略聯盟、更不是獨家。</p>
    <p style="margin-top:12px">Demo 裡的價格、播放數、成交與佣金全部是標示過的示意值。
    第一筆真實佣金是 T2 的<b>結果</b>而不是里程碑：能不能發生取決於 T1 的送件是否通過，
    本階可被驗收的只有「外導連結真的帶得動追蹤碼」。</p>
    <p style="margin-top:12px">單位經濟已經算出來放在 T3，並且刻意寫成<b>可以被推翻的形式</b>：
    每趟期望佣金 E ＝ 時機數 × 外導點擊率 A × 平台成交率 B × 平均訂單 C × 分潤率 D。
    A、B、C、D 今天全部是猜測，分別要到 T2、T3、T4 才量得到。</p>
  </div>
</div></section>

<footer><div class="wrap">
  ResoMap 產品路線圖 · 依賴排序版 · 內部文件，未經授權請勿外流<br>
  T0 內容由程式碼盤點讀出，非自述；依賴圖經三輪對抗式檢查，階段順序 0 違規。
</div></footer>

</body>
</html>
"""

io.open(f"{ROOT}/index.html", "w", encoding="utf-8", newline="\n").write(HTML)

# Artifact publishing supplies its own <!doctype>/<html>/<head>/<body>, so that
# variant carries only the title, the stylesheet and the page content. Sliced out
# of the same string rather than maintained separately — two copies of an 88KB
# page is two copies that drift.
_body = HTML.split("<body>", 1)[1].rsplit("</body>", 1)[0]
ARTIFACT = f"<title>ResoMap 路線圖 T0–T5</title>\n<style>{CSS}</style>\n{_body}"
io.open(f"{ROOT}/artifact.html", "w", encoding="utf-8", newline="\n").write(ARTIFACT)

# ---------------------------------------------------------------------- CSV

with io.open(f"{ROOT}/features.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow([
        "T 階段", "功能 ID", "功能名稱", "領域", "一句話說明", "今天的狀態",
        "依賴功能 ID", "依賴功能名稱", "為何不能更早", "做完之後解鎖什麼",
        "前提條件", "變現角色", "工量", "被哪些功能依賴",
    ])
    for f in sorted(FEATURES, key=lambda x: (ORDER[x["t"]], x["domain_zh"], x["name_zh"])):
        w.writerow([
            f["t"], f["id"], f["name_zh"], f["domain_zh"], f["one_line_zh"], f["status_today"],
            " | ".join(f["depends_on"]) or "",
            " | ".join(BY_ID[d]["name_zh"] for d in f["depends_on"]) or "",
            f["why_it_must_wait_zh"], f["unlocks_zh"], f["needs_zh"],
            f["revenue_role"], f["effort"],
            " | ".join(BY_ID[u]["name_zh"] for u in UNBLOCKS[f["id"]]) or "",
        ])

with io.open(f"{ROOT}/stages.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["T 階段", "名稱", "解鎖的能力", "目標", "過關條件", "為什麼是這一階",
                "商業模式", "收入線", "驗證指標", "功能數"])
    for s in STAGES:
        lines = []
        for ln in s["revenue_lines"]:
            mat, pre = fix_maturity(s, ln)
            lines.append(f'[{mat}] {ln["name_zh"]}：{ln["mechanism_zh"]}（前提：{pre}）')
        w.writerow([
            s["t"], s["name_zh"], s["headline_capability_zh"], s["goal_zh"], s["gate_zh"],
            s["why_here_zh"], s["business_model_zh"], "\n".join(lines),
            "\n".join(s["proof_metrics_zh"]), counts[s["t"]],
        ])

print("built")
print(" index.html   ", len(HTML), "chars")
for t in TS:
    print(f"   {t}: {counts[t]} features")
print(" features.csv  86 rows")
print(" stages.csv     6 rows")
