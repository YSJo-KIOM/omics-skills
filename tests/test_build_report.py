"""Builder self-check: python3 tests/test_build_report.py  (no pytest needed)."""
import json
import pathlib
import re
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parents[1] / "plugins/omics-skills/skills/interactive-report"
sys.path.insert(0, str(SKILL / "scripts"))
import build_report as br  # noqa: E402


def data_of(page):
    return json.loads(re.search(r'id="ir-data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))


def raises(fn, text):
    try:
        fn()
    except br.SpecError as e:
        assert text in str(e), f"expected '{text}' in: {e}"
        return
    raise AssertionError(f"no SpecError ({text})")


# markdown subset
h = br.md("## 결과\n\n- **굵게** 와 *기울임*\n- PMID 25516281 · doi:10.1093/nar/gkv007\n\n| a | b |\n|---|---|\n| 1 | <x> |")
assert "<h2>결과</h2>" in h and "<strong>굵게</strong>" in h and "<em>기울임</em>" in h
assert 'href="https://pubmed.ncbi.nlm.nih.gov/25516281/"' in h and 'href="https://doi.org/10.1093/nar/gkv007"' in h
assert "<table>" in h and "&lt;x&gt;" in h, "raw HTML must be escaped"
assert "snake_case_name" in br.md("snake_case_name"), "underscores inside words are not emphasis"

# column inference + missing values
spec = {"meta": {"title": "t"}, "tabs": [{"title": "요약", "blocks": [{"type": "table", "rows": [
    {"gene_id": 101, "lfc": "1.5", "dir": "up", "p": "NA", "url": "https://x.org/a"},
    {"gene_id": 102, "lfc": "-2", "dir": "down", "p": "1e-3", "url": "https://x.org/b"},
    {"gene_id": 103, "lfc": "Inf", "dir": "up", "p": "0.2", "url": "https://x.org/c"}]}]}]}
d = data_of(br.build(spec))
cols = {c["key"]: c["type"] for c in d["tables"]["table1"]["columns"]}
assert cols == {"gene_id": "text", "lfc": "num", "dir": "cat", "p": "num", "url": "link"}, cols
rows = d["tables"]["table1"]["rows"]
assert rows[0]["p"] is None and rows[2]["lfc"] is None and rows[1]["lfc"] == -2 and rows[0]["gene_id"] == "101"
assert d["tabs"][-1]["title"] == "분석 환경·기타", "environment tab is appended"

# errors point at the problem
raises(lambda: br.build({"meta": {"title": "t"}, "tabs": [{"title": "요약", "blocks": [{"type": "table", "table": "nope"}]}]}), "nope")
raises(lambda: br.build({"meta": {"title": "t"}, "tabs": [{"title": "요약", "blocks": [{"type": "wat"}]}]}), "알 수 없는 블록")
bad_chart = json.loads(json.dumps(spec))
bad_chart["tabs"][0]["blocks"].append({"type": "chart", "table": "table1", "kind": "scatter", "x": "dir", "y": "lfc"})
raises(lambda: br.build(bad_chart), "숫자(num) 열")

# parameter widgets: validation, script embedding, build-time syntax check
wspec = lambda w: {"meta": {"title": "t"}, "tabs": [{"title": "요약", "blocks": [w]}]}
ctl = [{"id": "k", "type": "range", "min": 0, "max": 1, "value": 0.5}]
raises(lambda: br.build(wspec({"type": "widget", "id": "w", "controls": ctl})), "script")
raises(lambda: br.build(wspec({"type": "widget", "id": "w", "controls": [{"id": "k", "type": "range", "min": 1, "max": 1}], "script": "1"})), "min < max")
raises(lambda: br.build(wspec({"type": "widget", "id": "w", "controls": [{"id": "k", "type": "range", "min": 0, "max": 1, "log": True}], "script": "1"})), "min > 0")
page = br.build(wspec({"type": "widget", "id": "w", "controls": ctl + [{"id": "s", "type": "select", "options": [1, 2]}], "script": "ctx.cards([{value: ctx.v.k, label: '</script>'}]);"}))
d = data_of(page)
assert d["has_widgets"] and d["tabs"][0]["blocks"][0]["controls"][1]["value"] == 1 and "plotly" in page
assert 'window.IR_WIDGETS["w"]=function(ctx){' in page and "<\\/script>" in page, "closing tag inside widget code is escaped"
if br.shutil.which("node"):
    raises(lambda: br.build(wspec({"type": "widget", "id": "w", "controls": ctl, "script": "const = ;"})), "문법 오류")

# local = full data, Artifact = top results (explicit tables.<id>.artifact, then automatic size budget)
assert br.test_expr("<0.05", 0.01) and not br.test_expr("<0.05", 0.2) and br.test_expr("abs>=1", -2) and br.test_expr(">0 <5", 3)
assert not br.test_expr(">1", None) and br.test_expr("infl", "Inflammation")
big = [{"g": f"G{i:05d}", "lfc": ((i * 37) % 200 - 100) / 25, "p": ((i * 7919) % 10007) / 10007, "txt": "x" * 60} for i in range(3000)]
bspec = lambda art=None, extra=(): {"meta": {"title": "t"}, "tables": {"d": {"rows": big, "sort": "p", **({"artifact": art} if art else {})}},
                                     "tabs": [{"title": "요약", "blocks": [{"type": "table", "table": "d"}, *extra]}]}
full = data_of(br.build(bspec({"top": 100, "where": {"lfc": "abs>=1"}, "columns": ["lfc", "p"]})))["tables"]["d"]
assert len(full["rows"]) == 3000 and "trim" not in full and len(full["columns"]) == 4, "local build keeps everything"
art = data_of(br.build(bspec({"top": 100, "where": {"lfc": "abs>=1"}, "columns": ["lfc", "p"]}), artifact=True, full_report="/x/full.html"))
D = art["tables"]["d"]
assert len(D["rows"]) == 100 and D["total"] == 3000 and all(abs(r["lfc"]) >= 1 for r in D["rows"])
assert [c["key"] for c in D["columns"]] == ["g", "lfc", "p"], "key column is always kept"
assert [r["p"] for r in D["rows"]] == sorted(r["p"] for r in D["rows"]) and "원본 3,000행" in D["trim"]
info = art["tabs"][-1]["blocks"][-1]
assert info["title"] == "Artifact 판" and ["전체 보고서 (로컬)", "/x/full.html"] in info["rows"]
raises(lambda: br.build(bspec({"columns": ["p"]}, [{"type": "chart", "table": "d", "kind": "histogram", "x": "lfc"}]), artifact=True), "lfc")
page = br.build(bspec(), artifact=True, max_mb=0.15)
D = data_of(page)["tables"]["d"]
assert len(page.encode()) <= 0.15 * 1024 * 1024 and 50 <= len(D["rows"]) < 3000 and any("자동 축소" in w for w in br.WARN), br.WARN
assert [r["p"] for r in D["rows"]] == sorted(r["p"] for r in big)[:len(D["rows"])], "auto cut keeps the top rows by the table sort"
with tempfile.TemporaryDirectory() as tmp:
    sp = pathlib.Path(tmp) / "s.json"
    sp.write_text(json.dumps(bspec({"top": 10})), encoding="utf-8")
    assert br.main([str(sp), "--both"]) == 0
    assert (pathlib.Path(tmp) / "s.html").exists() and "전체 보고서 (로컬)" in (pathlib.Path(tmp) / "s_artifact.html").read_text()

# runtime must survive 100k+ row tables: no argument spreading over row arrays (call-stack overflow, found with 150k rows)
rt = (SKILL / "assets/report.html").read_text()
assert "apply(null" not in rt and not re.search(r"Math\.(min|max)\(\.\.\.", rt), "use loops for min/max over rows"

# both examples build; artifact mode has no document wrapper; plotly only when charts exist
for ex in ("analysis", "literature", "explainer"):
    sp = SKILL / "examples" / ex / "spec.json"
    page = br.build(br.load_spec(sp), sp.parent, sp.name)
    assert page.startswith("<!doctype html>") and "plotly" in page and not br.WARN, (ex, br.WARN)
    art = br.build(br.load_spec(sp), sp.parent, sp.name, artifact=True)
    assert art.lstrip().startswith("<title>") and "<body>" not in art
d = data_of(br.build({"meta": {"title": "t"}, "tabs": [{"title": "요약", "blocks": ["글만"]}]}))
assert not any(b["type"] == "chart" for t in d["tabs"] for b in t["blocks"])

# CLI round trip
with tempfile.TemporaryDirectory() as tmp:
    out = pathlib.Path(tmp) / "r.html"
    assert br.main([str(SKILL / "examples/analysis/spec.json"), "-o", str(out)]) == 0 and out.stat().st_size > 50_000
print("ok")
