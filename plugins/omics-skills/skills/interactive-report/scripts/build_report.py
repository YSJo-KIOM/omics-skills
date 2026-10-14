#!/usr/bin/env python3
"""Build a single-file interactive HTML report from a JSON (or YAML) spec.

    python3 build_report.py spec.json                 # -> spec.html (standalone, opens in any browser)
    python3 build_report.py spec.json -o out.html --artifact   # body-only page for the claude.ai Artifact tool

Stdlib only (YAML specs need PyYAML). Schema: ../references/spec.md
Python callers can `from build_report import build` and pass a dict.
"""
import argparse
import base64
import csv
import datetime
import html
import io
import json
import math
import mimetypes
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

VERSION = "0.3.1"
HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "report.html"
PLOTLY = '<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.3/plotly.min.js"></script>'
NA = {"", "na", "nan", "null", "none", "n/a", "#n/a", "inf", "-inf", "+inf", "infinity", "-infinity"}
ID_LIKE = re.compile(r"(^|[_.\s])(id|cid|pmid|pmcid|entrez|entrezid|gene_?id|accession|doi|uniprot)$", re.I)
TONES = {"up", "down", "good", "warn", "acc", "mut"}
CHART_KINDS = {"scatter", "bar", "histogram", "box"}
FIELD_TYPES = {"choice", "multi", "text", "textarea", "number"}
CONTROL_TYPES = {"range", "select", "toggle"}
ARTIFACT_MB = 15.0          # claude.ai Artifact page limit is 16 MB; keep a margin
LOCAL_WARN_MB = 150         # a local file has no limit, but very large pages open slowly


class SpecError(Exception):
    pass


# ---------------------------------------------------------------- markdown (small subset)
def _inline(s):
    keep = []

    def stash(h):
        keep.append(h)
        return f"\x00{len(keep) - 1}\x00"

    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{m.group(1)}</code>"), s)

    def link(m):
        url = html.unescape(m.group(2)).strip()
        if not re.match(r"^(https?://|#|mailto:)", url):
            return m.group(0)
        return stash(f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{m.group(1)}</a>')

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"(?<![\w/])(https?://[^\s<)]+)", lambda m: stash(f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>'), s)
    s = re.sub(r"\bPMID:?\s?(\d{5,9})\b", lambda m: stash(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{m.group(1)}/" target="_blank" rel="noopener">PMID {m.group(1)}</a>'), s)
    s = re.sub(r"\bdoi:\s?(10\.\d{4,9}/[^\s<]+[^\s<.,;)])", lambda m: stash(f'<a href="https://doi.org/{m.group(1)}" target="_blank" rel="noopener">doi:{m.group(1)}</a>'), s, flags=re.I)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def md(text):
    """Markdown subset -> HTML: headings, paragraphs, -/1. lists, > quotes, ``` code, pipe tables, inline marks.
    Raw HTML is escaped on purpose; use an `html` block for markup."""
    if not text:
        return ""
    lines, out, i = str(text).replace("\r\n", "\n").split("\n"), [], 0
    para = []

    def flush():
        if para:
            out.append("<p>" + _inline(" ".join(x.strip() for x in para)) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if st.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        if not st:
            flush()
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            flush()
            lvl = min(max(len(m.group(1)), 2), 4)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            flush()
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(st)
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")
            i = j
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", st):
            flush()
            ordered = bool(re.match(r"^\d", st))
            items, j = [], i
            while j < len(lines) and re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[j]):
                items.append(re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", lines[j]))
                j += 1
                while j < len(lines) and lines[j].startswith("  ") and lines[j].strip() and not re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[j]):
                    items[-1] += " " + lines[j].strip()
                    j += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
            i = j
            continue
        if st.startswith(">"):
            flush()
            q, j = [], i
            while j < len(lines) and lines[j].strip().startswith(">"):
                q.append(lines[j].strip()[1:].strip())
                j += 1
            out.append("<blockquote>" + md("\n".join(q)) + "</blockquote>")
            i = j
            continue
        para.append(ln)
        i += 1
    flush()
    return "".join(out)


# ---------------------------------------------------------------- tables
def _num(s):
    """'1e-5' -> 1e-05, '3' -> 3, else None. Infinite/NaN count as missing."""
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    t = str(s).strip()
    return int(v) if re.fullmatch(r"[-+]?\d+", t) and abs(v) < 2 ** 53 else v


def read_rows(path):
    text = path.read_text(encoding="utf-8-sig")
    first = text.split("\n", 1)[0]
    delim = "\t" if path.suffix.lower() in (".tsv", ".tab", ".txt") or "\t" in first else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    if rows and None in rows[0]:
        raise SpecError(f"{path}: 일부 행의 열 수가 머리행보다 많습니다 (구분자 확인)")
    return rows


def _is_missing(v):
    return v is None or (isinstance(v, float) and not math.isfinite(v)) or (isinstance(v, str) and v.strip().lower() in NA)


def prepare_table(tid, t, base, cat_max, artifact=False):
    if "source" in t:
        p = (base / t["source"]).resolve()
        if not p.exists():
            raise SpecError(f"표 '{tid}': 파일이 없습니다 — {p}")
        rows = read_rows(p)
    elif "rows" in t:
        rows = t["rows"]
        if rows and isinstance(rows[0], list):
            if not t.get("header"):
                raise SpecError(f"표 '{tid}': rows 가 리스트의 리스트면 header 가 필요합니다")
            rows = [dict(zip(t["header"], r)) for r in rows]
    else:
        raise SpecError(f"표 '{tid}': source(파일) 또는 rows(인라인) 중 하나가 필요합니다")
    if not rows:
        raise SpecError(f"표 '{tid}': 행이 없습니다")
    all_keys = list(dict.fromkeys(k for r in rows for k in r.keys()))
    given = t.get("columns")
    labels = t.get("labels", {})
    specs = []
    for c in (given or all_keys):
        c = {"key": c} if isinstance(c, str) else dict(c)
        if "key" not in c:
            raise SpecError(f"표 '{tid}': columns 항목에 key 가 없습니다 — {c}")
        if c["key"] not in all_keys:
            raise SpecError(f"표 '{tid}': 열 '{c['key']}' 이 데이터에 없습니다. 있는 열: {', '.join(all_keys[:30])}")
        c.setdefault("label", labels.get(c["key"], c["key"]))
        specs.append(c)
    keys = [c["key"] for c in specs]
    out = [{k: (None if _is_missing(r.get(k)) else r.get(k)) for k in keys} for r in rows]
    for c in specs:
        k = c["key"]
        vals = [r[k] for r in out if r[k] is not None]
        nums = [v if isinstance(v, (int, float)) and not isinstance(v, bool) else _num(v) for v in vals]
        numeric = bool(vals) and all(n is not None for n in nums)
        typ = c.get("type")
        if typ is None:
            strs = [str(v) for v in vals]
            uniq = set(strs)
            if numeric and not (ID_LIKE.search(k) and all(isinstance(n, int) for n in nums)):
                typ = "num"
            elif strs and all(re.match(r"^https?://", s) for s in strs):
                typ = "link"
            elif strs and len(uniq) <= cat_max and len(uniq) < len(strs) and max(map(len, uniq)) <= 40:
                typ = "cat"
            else:
                typ = "text"
            c["type"] = typ
        if typ not in ("num", "cat", "text", "link"):
            raise SpecError(f"표 '{tid}' 열 '{k}': type 은 num/cat/text/link 중 하나여야 합니다 ({typ})")
        if typ == "num":
            if not numeric:
                bad = next(v for v, n in zip(vals, nums) if n is None)
                raise SpecError(f"표 '{tid}' 열 '{k}': num 인데 숫자가 아닌 값이 있습니다 (예: {bad!r})")
            for r in out:
                if r[k] is not None:
                    r[k] = r[k] if isinstance(r[k], (int, float)) and not isinstance(r[k], bool) else _num(r[k])
        else:
            for r in out:
                if r[k] is not None and not isinstance(r[k], str):
                    r[k] = str(r[k]).lower() if isinstance(r[k], bool) else (str(int(r[k])) if isinstance(r[k], float) and r[k].is_integer() else str(r[k]))
            if "wrap" not in c and vals and (sum(len(str(v)) for v in vals) / len(vals) > 50 or max(len(str(v)) for v in vals) > 120):
                c["wrap"] = True
        if c.get("badges"):
            bad = {v for v in c["badges"].values() if v not in TONES}
            if bad:
                raise SpecError(f"표 '{tid}' 열 '{k}': badges 톤은 {sorted(TONES)} 중 하나 ({bad})")
        if c.get("tip"):
            c["tip"] = str(c["tip"])
    key = t.get("key", keys[0])
    if key not in keys:
        raise SpecError(f"표 '{tid}': key 열 '{key}' 이 columns 에 없습니다")
    seen = [r[key] for r in out]
    if len(set(seen)) < len(seen):
        WARN.append(f"표 '{tid}': key 열 '{key}' 값이 중복됩니다 — 바구니·내보내기는 행 단위로 동작하지만 목록에서 구분이 어렵습니다")
    sort = t.get("sort")
    if isinstance(sort, str):
        sort = {"key": sort.lstrip("-"), "desc": sort.startswith("-")}
    if sort and sort["key"] not in keys:
        raise SpecError(f"표 '{tid}': sort 열 '{sort['key']}' 이 없습니다")
    D = {"id": tid, "title": t.get("title", tid), "key": key, "columns": specs, "rows": out, "sort": sort}
    cfg = t.get("artifact")
    if cfg is not None:
        cfg = _artifact_cfg(tid, cfg, keys)
        if artifact:
            D = shrink_table(D, cfg)
    return D


def _artifact_cfg(tid, cfg, keys):
    """tables.<id>.artifact = {top, sort, where, columns}: how the Artifact copy keeps the top results."""
    if not isinstance(cfg, dict) or set(cfg) - {"top", "sort", "where", "columns"}:
        raise SpecError(f"표 '{tid}': artifact 는 top / sort / where / columns 를 가진 객체입니다")
    cfg = dict(cfg)
    if "top" in cfg and not (isinstance(cfg["top"], int) and cfg["top"] > 0):
        raise SpecError(f"표 '{tid}': artifact.top 은 양의 정수")
    if isinstance(cfg.get("sort"), str):
        cfg["sort"] = {"key": cfg["sort"].lstrip("-"), "desc": cfg["sort"].startswith("-")}
    for k in ([cfg["sort"]["key"]] if cfg.get("sort") else []) + list(cfg.get("where") or {}) + list(cfg.get("columns") or []):
        if k not in keys:
            raise SpecError(f"표 '{tid}': artifact 에 쓴 열 '{k}' 이 없습니다")
    return cfg


def test_expr(expr, v):
    """Same grammar as the page's numeric filter: '<0.05', '>=1', 'abs>=1', '>0 <5'; otherwise substring match."""
    parts = [x for x in re.split(r"\s+|&+", str(expr).strip()) if x]
    ms = [re.fullmatch(r"(abs|\|x\|)?\s*(>=|<=|>|<|==|=|!=)\s*(-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)", x, re.I) for x in parts]
    if parts and all(ms):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        ops = {">": float.__gt__, "<": float.__lt__, ">=": float.__ge__, "<=": float.__le__, "!=": float.__ne__, "=": float.__eq__, "==": float.__eq__}
        return all(ops[m.group(2)](float(abs(v) if m.group(1) else v), float(m.group(3))) for m in ms)
    return str(expr).strip().lower() in ("" if v is None else str(v)).lower()


def sorted_rows(rows, sort):
    if not sort:
        return list(rows)
    k = sort["key"]
    have = [r for r in rows if r.get(k) is not None]
    have.sort(key=lambda r: (0, r[k], "") if isinstance(r[k], (int, float)) else (1, 0, str(r[k])), reverse=bool(sort.get("desc")))
    return have + [r for r in rows if r.get(k) is None]


def _sort_text(sort):
    return f"{sort['key']} {'내림차순' if sort.get('desc') else '오름차순'} 상위 " if sort else "앞쪽 "


def shrink_table(D, cfg):
    total, rows = len(D["rows"]), D["rows"]
    for col, expr in (cfg.get("where") or {}).items():
        rows = [r for r in rows if test_expr(expr, r.get(col))]
    sort = cfg.get("sort") or D.get("sort")
    rows = sorted_rows(rows, sort)
    if cfg.get("top"):
        rows = rows[:cfg["top"]]
    cols = D["columns"]
    if cfg.get("columns"):
        keep = set(cfg["columns"]) | {D["key"]}
        cols = [c for c in cols if c["key"] in keep]
        rows = [{c["key"]: r[c["key"]] for c in cols} for r in rows]
    if len(rows) == total and len(cols) == len(D["columns"]):
        return D
    how = " · ".join([f"{c} {e}" for c, e in (cfg.get("where") or {}).items()] + ([f"{_sort_text(sort)}{len(rows):,}행"] if len(rows) < total else []))
    return {**D, "columns": cols, "rows": rows, "total": total, "how": how or "열 일부만", "asort": sort,
            "trim": f"Artifact 판: 원본 {total:,}행 중 {how or '전체'}만 들어 있습니다" + (f" (열 {len(cols)}/{len(D['columns'])}개)" if len(cols) < len(D["columns"]) else "") + ". 전체 결과는 로컬 보고서에서 보세요."}


# ---------------------------------------------------------------- blocks
WARN = []


def _sid(s):
    s = re.sub(r"[^A-Za-z0-9._~-]+", "-", str(s)).strip("-")
    return s or "x"


def embed_image(src, base):
    if re.match(r"^(data:|https?://)", src):
        if src.startswith("http"):
            WARN.append(f"그림 {src}: 외부 URL 은 Artifact 에서 차단됩니다 — 파일로 내려받아 넣으세요")
        return src
    p = (base / src).resolve()
    if not p.exists():
        raise SpecError(f"그림 파일이 없습니다 — {p}")
    data = p.read_bytes()
    if len(data) > 3 * 1024 * 1024:
        WARN.append(f"그림 {p.name}: {len(data) / 1e6:.1f} MB — 해상도를 낮추거나 PNG 를 압축하세요")
    mime = "image/svg+xml" if p.suffix.lower() == ".svg" else (mimetypes.guess_type(p.name)[0] or "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(data).decode()


class Ctx:
    def __init__(self, spec, base, artifact=False):
        self.spec, self.base, self.tables, self.n_inline, self.widgets, self.artifact = spec, base, {}, 0, {}, artifact
        self.cat_max = int(spec.get("cat_max", 12))
        for tid, t in (spec.get("tables") or {}).items():
            self.tables[_sid(tid)] = prepare_table(_sid(tid), t, base, self.cat_max, artifact)

    def table_ref(self, b, where):
        if isinstance(b.get("table"), str):
            tid = _sid(b["table"])
            if tid not in self.tables:
                raise SpecError(f"{where}: 표 '{b['table']}' 이 tables 에 없습니다. 있는 표: {', '.join(self.tables) or '(없음)'}")
            return tid
        if "source" in b or "rows" in b:
            self.n_inline += 1
            tid = _sid(b.get("id") or f"table{self.n_inline}")
            if tid in self.tables:
                raise SpecError(f"{where}: 표 id '{tid}' 가 중복됩니다")
            self.tables[tid] = prepare_table(tid, b, self.base, self.cat_max, self.artifact)
            return tid
        raise SpecError(f"{where}: table(표 id) 또는 source/rows 가 필요합니다")


def block(b, ctx, where):
    if isinstance(b, str):
        return {"type": "html", "html": md(b)}
    b = dict(b)
    typ = b.get("type")
    common = {k: b[k] for k in ("title", "level") if k in b}
    if b.get("intro"):
        common["intro"] = md(b["intro"])
    if typ == "md":
        return {**common, "type": "html", "html": md(b.get("text", ""))}
    if typ == "html":
        return {**common, "type": "html", "html": b.get("html", "")}
    if typ == "code":
        return {**common, "type": "html", "html": "<pre><code>" + html.escape(b.get("text", "")) + "</code></pre>"}
    if typ == "cards":
        items = b.get("items") or []
        for it in items:
            if "value" not in it or "label" not in it:
                raise SpecError(f"{where}: cards 항목에는 value 와 label 이 필요합니다")
            if it.get("tone") and it["tone"] not in TONES:
                raise SpecError(f"{where}: cards tone 은 {sorted(TONES)} 중 하나")
        return {**common, "type": "cards", "items": [{k: (str(v) if k == "value" else v) for k, v in it.items()} for it in items]}
    if typ == "callout":
        tone = b.get("tone", "note")
        if tone not in ("note", "warn", "good", "tip"):
            raise SpecError(f"{where}: callout tone 은 note/warn/good/tip")
        return {"type": "callout", "tone": tone, "title": b.get("title", ""), "html": md(b.get("text", ""))}
    if typ == "kv":
        rows = b.get("rows") or [[k, v] for k, v in (b.get("data") or {}).items()]
        return {**common, "type": "kv", "code": bool(b.get("code")), "rows": [[str(x) if x is not None else "" for x in r] for r in rows]}
    if typ == "glossary":
        return {**common, "type": "glossary", "items": [[str(t), str(d)] for t, d in b.get("items", [])]}
    if typ == "figure":
        if b.get("images"):
            imgs = b["images"]
        elif b.get("src"):
            imgs = [{"src": b["src"], "caption": b.get("caption", ""), "alt": b.get("alt", "")}]
        else:
            raise SpecError(f"{where}: figure 에는 src 또는 images 가 필요합니다")
        out = {**common, "type": "figure", "images": [{**im, "src": embed_image(im["src"], ctx.base)} for im in imgs]}
        if b.get("images") and b.get("caption"):
            out["caption"] = b["caption"]
        if b.get("min_width"):
            out["min_width"] = b["min_width"]
        return out
    if typ == "table":
        inline = "source" in b or "rows" in b      # inline tables carry their own sort (handled in prepare_table)
        tid = ctx.table_ref(b, where)
        out = {**common, "type": "table", "table": tid, **{k: b[k] for k in ("height", "page") if k in b}}
        if "sort" in b and not inline:
            s = b["sort"]
            out["sort"] = {"key": s.lstrip("-"), "desc": s.startswith("-")} if isinstance(s, str) else s
            if out["sort"]["key"] not in {c["key"] for c in ctx.tables[tid]["columns"]}:
                raise SpecError(f"{where}: sort 열 '{out['sort']['key']}' 이 표 '{tid}' 에 없습니다")
        if "title" not in out:
            out["title"] = ctx.tables[tid]["title"]
        return out
    if typ == "chart":
        if b.get("data"):
            return {**common, "type": "chart", "data": b["data"], "layout": b.get("layout", {}), "height": b.get("height", 420)}
        tid = ctx.table_ref(b, where)
        kind = b.get("kind")
        if kind not in CHART_KINDS:
            raise SpecError(f"{where}: chart kind 는 {sorted(CHART_KINDS)} 중 하나 (또는 data/layout 으로 plotly 직접 지정)")
        cols = {c["key"]: c for c in ctx.tables[tid]["columns"]}
        for k in {"scatter": ["x", "y"], "bar": ["x"], "histogram": ["x"], "box": ["y"]}[kind]:
            if not b.get(k):
                raise SpecError(f"{where}: {kind} 차트에는 '{k}' 열이 필요합니다")
        for name in [b.get(k) for k in ("x", "y", "color", "label")] + list(b.get("hover", [])):
            if name and name not in cols:
                raise SpecError(f"{where}: 열 '{name}' 이 표 '{tid}' 에 없습니다 (차트는 표에 넣은 열만 쓸 수 있습니다)")
        must_num = {"scatter": ["x", "y"], "histogram": ["x"], "box": ["y"], "bar": ["y"]}[kind]
        for k in must_num:
            if b.get(k) and cols[b[k]]["type"] != "num":
                raise SpecError(f"{where}: {kind} 의 {k}='{b[k]}' 는 숫자(num) 열이어야 합니다")
        keep = ("kind", "x", "y", "color", "label", "hover", "size", "log_x", "log_y", "x_transform", "y_transform", "x_label", "y_label",
                "lines", "colors", "top", "horizontal", "bins", "height", "dragmode", "layout", "title_in_plot")
        return {**common, "type": "chart", "table": tid, **{k: b[k] for k in keep if k in b}}
    if typ == "review":
        if not b.get("id") or not b.get("items"):
            raise SpecError(f"{where}: review 에는 id 와 items 가 필요합니다")
        items = []
        for it in b["items"]:
            fields = []
            for f in it.get("fields") or [{"id": "verdict", "label": "판정", "type": "choice", "options": [{"v": "go", "l": "진행"}, {"v": "hold", "l": "보류"}, {"v": "drop", "l": "제외"}]},
                                          {"id": "note", "label": "메모", "type": "textarea"}]:
                if f.get("type", "choice") not in FIELD_TYPES:
                    raise SpecError(f"{where}: review 필드 type 은 {sorted(FIELD_TYPES)} 중 하나")
                f = {"type": "choice", **f}
                if f["type"] in ("choice", "multi"):
                    f["options"] = [o if isinstance(o, dict) else {"v": str(o), "l": str(o)} for o in f.get("options", [])]
                    if not f["options"]:
                        raise SpecError(f"{where}: '{it.get('id')}.{f.get('id')}' 선택지(options)가 비어 있습니다")
                fields.append(f)
            items.append({"id": _sid(it["id"]), "title": it.get("title", it["id"]), "desc": md(it.get("desc", "")), "md_desc": it.get("md_desc", ""), "fields": fields})
        out = {**common, "type": "review", "id": _sid(b["id"]), "items": items}
        for k in ("md_title", "md_intro", "include_basket", "basket_cols"):
            if k in b:
                out[k] = b[k]
        return out
    if typ == "widget":
        return widget_block(b, ctx, where, common)
    if typ == "details":
        return {"type": "details", "summary": b.get("summary") or b.get("title", "자세히"), "open": bool(b.get("open")),
                "blocks": [block(x, ctx, f"{where} > details[{k}]") for k, x in enumerate(b.get("blocks", []))]}
    raise SpecError(f"{where}: 알 수 없는 블록 type '{typ}' (md, html, code, cards, callout, kv, glossary, figure, table, chart, widget, review, details)")


def widget_block(b, ctx, where, common):
    """Parameter widget: controls -> page-side compute function (script) -> live cards/plots."""
    wid = _sid(b.get("id") or "")
    if not b.get("id"):
        raise SpecError(f"{where}: widget 에는 id 가 필요합니다")
    if wid in ctx.widgets:
        raise SpecError(f"{where}: widget id '{wid}' 가 중복됩니다")
    controls, ids = [], set()
    for c in b.get("controls") or []:
        c = dict(c)
        t = c.setdefault("type", "range")
        cid = c.get("id")
        if not cid or cid in ids:
            raise SpecError(f"{where}: control 마다 고유한 id 가 필요합니다 ({cid!r})")
        ids.add(cid)
        if t not in CONTROL_TYPES:
            raise SpecError(f"{where}: control '{cid}' type 은 {sorted(CONTROL_TYPES)} 중 하나")
        if t == "range":
            lo, hi = c.get("min"), c.get("max")
            if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (lo, hi)) or lo >= hi:
                raise SpecError(f"{where}: range '{cid}' 에는 min < max 인 숫자가 필요합니다")
            if c.get("log") and lo <= 0:
                raise SpecError(f"{where}: range '{cid}' 가 log 이면 min > 0 이어야 합니다")
            c.setdefault("value", lo)
            if not (isinstance(c["value"], (int, float)) and lo <= c["value"] <= hi):
                raise SpecError(f"{where}: range '{cid}' value {c['value']!r} 가 [{lo}, {hi}] 밖입니다")
        elif t == "select":
            c["options"] = [o if isinstance(o, dict) else {"v": o, "l": str(o)} for o in c.get("options") or []]
            if not c["options"]:
                raise SpecError(f"{where}: select '{cid}' 의 options 가 비어 있습니다")
            c.setdefault("value", c["options"][0]["v"])
            if c["value"] not in [o["v"] for o in c["options"]]:
                raise SpecError(f"{where}: select '{cid}' value {c['value']!r} 가 options 에 없습니다")
        else:
            c["value"] = bool(c.get("value", False))
        controls.append(c)
    if not controls:
        raise SpecError(f"{where}: widget '{wid}' 의 controls 가 비어 있습니다")
    if b.get("script_file"):
        p = (ctx.base / b["script_file"]).resolve()
        if not p.exists():
            raise SpecError(f"{where}: script_file 이 없습니다 — {p}")
        code = p.read_text(encoding="utf-8")
    elif b.get("script"):
        code = "\n".join(b["script"]) if isinstance(b["script"], list) else b["script"]
    else:
        raise SpecError(f"{where}: widget '{wid}' 에는 script 또는 script_file 이 필요합니다 (render(ctx) 함수의 본문)")
    out = {**common, "type": "widget", "id": wid, "controls": controls}
    if b.get("table"):
        if not isinstance(b["table"], str):
            raise SpecError(f"{where}: widget 의 table 은 tables 에 정의한 표 id 여야 합니다")
        out["table"] = ctx.table_ref(b, where)
    ctx.widgets[wid] = code
    return out


def widget_js(widgets):
    """Each widget script becomes a plain function in an inline <script> (no eval: works under strict CSP)."""
    js = "window.IR_WIDGETS={};\n" + "".join(
        f"window.IR_WIDGETS[{json.dumps(k)}]=function(ctx){{\n{code}\n}};\n" for k, code in widgets.items())
    js = re.sub(r"</(script)", r"<\\/\1", js, flags=re.I)
    node = shutil.which("node")
    if not node:
        if widgets:
            WARN.append("node 가 없어 위젯 스크립트 문법 검사를 건너뜁니다 — 브라우저에서 '위젯 오류' 표시를 확인하세요")
        return js
    for k, code in widgets.items():
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write("(function(ctx){\n" + code + "\n});\n")
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
        pathlib.Path(f.name).unlink()
        if r.returncode != 0:
            msg = "\n".join(l for l in r.stderr.splitlines() if l.strip() and not l.startswith("Node.js"))[:800]
            raise SpecError(f"widget '{k}' 스크립트 문법 오류 (줄 번호는 스크립트 첫 줄을 2로 셈):\n{msg}")
    return js


def env_blocks(spec, spec_name, ctx):
    e = spec.get("environment") or {}
    bl = []
    sw = e.get("software")
    if sw:
        rows = [[k, v] for k, v in sw.items()] if isinstance(sw, dict) else [[x.get("name"), x.get("version", ""), x.get("note", "")] if isinstance(x, dict) else list(x) for x in sw]
        bl.append({"type": "kv", "title": "소프트웨어·패키지", "rows": rows})
    if e.get("parameters"):
        bl.append({"type": "kv", "title": "분석 파라미터", "data": e["parameters"]})
    if e.get("data"):
        bl.append({"type": "kv", "title": "데이터·파일", "code": True,
                   "rows": [[d.get("desc", ""), d.get("path", "")] if isinstance(d, dict) else list(d) for d in e["data"]]})
    if e.get("reproduce"):
        bl.append({"type": "code", "title": "재현 방법", "text": e["reproduce"]})
    if e.get("notes"):
        bl.append({"type": "md", "title": "한계·주의", "text": e["notes"]})
    gl = spec.get("glossary") or e.get("glossary")
    if gl:
        bl.append({"type": "glossary", "title": "용어", "items": gl})
    n_rows = sum(len(t["rows"]) for t in ctx.tables.values())
    bl.append({"type": "kv", "title": "보고서 정보", "rows": [
        ["생성 시각", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["생성 도구", f"interactive-report build_report.py v{VERSION}"],
        ["spec 파일", spec_name],
        ["포함 표", f"{len(ctx.tables)}개 · {n_rows:,}행"],
        ["브라우저 저장", "선택 바구니와 검토 선택은 이 브라우저에만 저장됩니다 (다른 사람·기기와 공유되지 않음). 필터는 저장되지 않습니다"],
    ]})
    return bl


def build(spec, base=".", spec_name="(dict)", artifact=False, max_mb=ARTIFACT_MB, full_report=None):
    """spec dict -> HTML string. Raises SpecError on invalid input; warnings collect in WARN.
    artifact=True: body-only page for the Artifact tool; tables follow tables.<id>.artifact and, if the page is still
    over max_mb, the largest tables are cut to their top rows automatically (with a warning)."""
    WARN.clear()
    base = pathlib.Path(base)
    meta = dict(spec.get("meta") or {})
    if not meta.get("title"):
        raise SpecError("meta.title 이 필요합니다")
    meta.setdefault("date", datetime.date.today().isoformat())
    tabs_in = spec.get("tabs") or []
    if not tabs_in:
        raise SpecError("tabs 가 비어 있습니다")
    ctx = Ctx(spec, base, artifact)
    tabs, ids = [], set()
    for k, t in enumerate(tabs_in):
        tid = _sid(t.get("id") or f"tab{k + 1}")
        if tid in ids:
            raise SpecError(f"탭 id '{tid}' 가 중복됩니다")
        ids.add(tid)
        if not t.get("title"):
            raise SpecError(f"탭 '{tid}': title 이 필요합니다")
        blocks = [block(b, ctx, f"탭 '{t['title']}' 블록 {i + 1}") for i, b in enumerate(t.get("blocks") or [])]
        if not blocks:
            WARN.append(f"탭 '{t['title']}' 이 비어 있습니다")
        if len(blocks) > 14:
            WARN.append(f"탭 '{t['title']}' 블록이 {len(blocks)}개 — 탭을 나누거나 details 로 접으세요")
        tabs.append({"id": tid, "title": t["title"], "role": t.get("role", ""), "blocks": blocks})
    first = tabs[0]
    if first["role"] != "summary" and not re.search(r"요약|개요|summary|overview", first["title"], re.I):
        WARN.append(f"첫 탭 '{first['title']}' 이 요약 탭이 아닙니다 — role: \"summary\" 로 표시하거나 요약 탭을 맨 앞에 두세요")
    env = [block(b, ctx, "분석 환경 탭") for b in env_blocks(spec, spec_name, ctx)]
    last = tabs[-1]
    if last["role"] == "environment" or re.search(r"환경|environment|methods?|방법", last["title"], re.I):
        last["blocks"] += env
        env_tab = last
    else:
        env_tab = {"id": "env" if "env" not in ids else "env-info", "title": "분석 환경·기타", "role": "environment", "blocks": env}
        tabs.append(env_tab)
    if len(tabs) > 10:
        WARN.append(f"탭이 {len(tabs)}개 — 8개 이하로 묶는 것을 권장합니다")
    kinds = {b["type"] for t in tabs for b in _walk(t["blocks"])}
    head, body = TEMPLATE.read_text(encoding="utf-8").split("<!--IR-BODY-->")
    head = head.replace("%%TITLE%%", html.escape(meta["title"])).replace("%%PLOTLY%%", PLOTLY if kinds & {"chart", "widget"} else "")
    body = body.replace("%%WIDGETS%%", widget_js(ctx.widgets))
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    def assemble():
        data = {"meta": meta, "tabs": tabs, "tables": ctx.tables, "has_widgets": "widget" in kinds, "build": stamp}
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
        return head + body.replace("%%DATA%%", payload)

    page = assemble()
    if artifact:
        limit = max_mb * 1024 * 1024
        for _ in range(30):                      # cut the largest table toward the budget until the page fits
            size = len(page.encode())
            if size <= limit:
                break
            sizes = {tid: len(json.dumps(D["rows"], ensure_ascii=False, separators=(",", ":")).encode()) for tid, D in ctx.tables.items()}
            if not sizes or max(len(D["rows"]) for D in ctx.tables.values()) <= 50:
                raise SpecError(f"Artifact 판이 {size / 1e6:.1f} MB 로 한도({max_mb:g} MB)를 넘습니다. 표를 줄여도 안 되므로 그림 해상도·개수를 줄이세요")
            tid = max(sizes, key=sizes.get)
            D, nb = ctx.tables[tid], sizes[tid]
            keep = max(50, int(len(D["rows"]) * max(0.05, (nb - (size - limit) * 1.05) / nb)))
            if keep >= len(D["rows"]):
                keep = len(D["rows"]) // 2
            total = D.get("total", len(D["rows"]))
            srt = D.get("asort") or D.get("sort")
            rows = sorted_rows(D["rows"], srt)[:keep]
            how = (D.get("how", "") + " · " if D.get("how") and "상위" not in D.get("how", "") else "") + f"{_sort_text(srt)}{keep:,}행 (용량 자동 축소)"
            ctx.tables[tid] = {**D, "rows": rows, "total": total, "how": how,
                               "asort": srt, "trim": f"Artifact 판: 원본 {total:,}행 중 {how}만 들어 있습니다. 전체 결과는 로컬 보고서에서 보세요."}
            WARN.append(f"Artifact 용량 한도로 표 '{tid}' 를 {total:,} → {keep:,}행으로 자동 축소했습니다"
                        + ("" if srt else " (정렬 기준이 없어 앞쪽 행 유지)") + f" — spec 에 tables.{tid}.artifact.top 을 정하면 직접 고를 수 있습니다")
            page = assemble()
        cut = [D for D in ctx.tables.values() if D.get("trim")]
        if cut or full_report:
            env_tab["blocks"].append({"type": "kv", "title": "Artifact 판", "code": False, "rows":
                [[D["title"], f"원본 {D['total']:,}행 → {len(D['rows']):,}행 ({D['how']})"] for D in cut]
                + ([["전체 보고서 (로컬)", full_report]] if full_report else [])})
            page = assemble()
        if len(page.encode()) > limit:
            raise SpecError(f"Artifact 판이 {len(page.encode()) / 1e6:.1f} MB 로 한도({max_mb:g} MB)를 넘습니다")
    else:
        page = ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
                + page.replace(head, head + "</head><body>\n", 1) + "</body></html>\n")
        if len(page.encode()) > LOCAL_WARN_MB * 1024 * 1024:
            WARN.append(f"로컬 보고서가 {len(page.encode()) / 1e6:.0f} MB — 브라우저에서 열 때 느릴 수 있습니다. 쓰지 않는 열을 빼세요")
    return page

def _walk(blocks):
    for b in blocks:
        yield b
        if b["type"] == "details":
            yield from _walk(b["blocks"])


def load_spec(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError:
            raise SpecError("YAML spec 은 PyYAML 이 필요합니다 (pip install pyyaml) — 또는 JSON 으로 쓰세요")
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise SpecError(f"{path}: JSON 문법 오류 — {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="spec(JSON/YAML) -> 단일 파일 interactive HTML 보고서")
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", help="출력 경로 (기본: spec 과 같은 이름의 .html, --artifact 면 _artifact.html)")
    ap.add_argument("--artifact", action="store_true", help="Artifact 게시용만: 본문만, 표는 tables.<id>.artifact 기준으로 축소, 한도 이하")
    ap.add_argument("--both", action="store_true", help="로컬 전체판(<이름>.html) + Artifact 축소판(<이름>_artifact.html) 함께")
    ap.add_argument("--max-mb", type=float, default=ARTIFACT_MB, help=f"Artifact 판 크기 상한 MB (기본 {ARTIFACT_MB:g})")
    a = ap.parse_args(argv)
    sp = pathlib.Path(a.spec)
    full_out = pathlib.Path(a.out) if a.out and not a.artifact else sp.with_suffix(".html")
    art_out = pathlib.Path(a.out) if a.out and a.artifact else full_out.with_name(full_out.stem + "_artifact.html")
    jobs = ([(full_out, False)] if not a.artifact else []) + ([(art_out, True)] if a.artifact or a.both else [])
    try:
        spec = load_spec(sp)
        for out, art in jobs:
            page = build(spec, sp.parent, sp.name, art, a.max_mb, str(full_out.resolve()) if art and a.both else None)
            out.write_text(page, encoding="utf-8")
            print(f"작성: {out} ({len(page.encode()) / 1024:,.0f} KB, {'Artifact 축소판 — 게시용' if art else '로컬 전체판'})")
            for w in WARN:
                print(f"경고: {w}")
    except SpecError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
