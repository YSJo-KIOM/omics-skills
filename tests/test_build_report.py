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

# both examples build; artifact mode has no document wrapper; plotly only when charts exist
for ex in ("analysis", "literature"):
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
