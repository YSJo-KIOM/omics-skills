// DEG 기준 탐색 — padj·|log2FC| 기준을 바꾸면 분류·개수·volcano·경로별 막대가 바로 다시 계산된다.
// ctx.v = {padj, fc, show_ns} · ctx.rows = deg 표의 행 (spec 의 "table": "deg")
const {padj, fc, show_ns} = ctx.v;
const cls = r => r.padj != null && r.padj < padj && Math.abs(r.log2FC) >= fc ? (r.log2FC > 0 ? "up" : "down") : "ns";
const g = {up: [], down: [], ns: []};
ctx.rows.forEach((r, i) => g[cls(r)].push(i));
const nUp = g.up.length, nDn = g.down.length, nDeg = nUp + nDn;

ctx.cards([
  {value: nDeg, label: "DEG"},
  {value: nUp, label: "증가", tone: "up"},
  {value: nDn, label: "감소", tone: "down"},
  {value: (100 * nDeg / ctx.rows.length).toFixed(1) + "%", label: "전체 유전자 대비"}
]);

const y = r => -Math.log10(Math.max(r.padj, 1e-300));
const pts = (k, color) => ({
  type: "scatter", mode: "markers", name: k,
  x: g[k].map(i => ctx.rows[i].log2FC), y: g[k].map(i => y(ctx.rows[i])), text: g[k].map(i => ctx.rows[i].gene),
  hovertemplate: "%{text}<br>log2FC %{x:.2f}<br>-log10 padj %{y:.2f}<extra></extra>",
  marker: {size: 6, color, opacity: k === "ns" ? 0.45 : 0.85}
});
const guide = {dash: "dash", width: 1, color: ctx.color("mut")};
ctx.plot("volcano", (show_ns ? [pts("ns", ctx.color("ns"))] : []).concat([pts("up", ctx.color("up")), pts("down", ctx.color("dn"))]), {
  height: 380, xaxis: {title: {text: "log2FC"}}, yaxis: {title: {text: "-log10(padj)"}},
  shapes: [-fc, fc].map(x => ({type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1, line: guide}))
    .concat([{type: "line", xref: "paper", x0: 0, x1: 1, y0: -Math.log10(padj), y1: -Math.log10(padj), line: guide}])
});

// 경로별 DEG 수 (pathways 열은 ";" 로 여러 값)
const per = {};
g.up.concat(g.down).forEach(i => (ctx.rows[i].pathways || "").split(";").filter(Boolean).forEach(p => {
  per[p] = per[p] || {up: 0, down: 0}; per[p][cls(ctx.rows[i])]++;
}));
const names = Object.keys(per).sort();
ctx.plot("pathways", [
  {type: "bar", name: "증가", x: names, y: names.map(p => per[p].up), marker: {color: ctx.color("up")}},
  {type: "bar", name: "감소", x: names, y: names.map(p => per[p].down), marker: {color: ctx.color("dn")}}
], {height: 250, barmode: "stack", yaxis: {title: {text: "DEG 수"}}});

ctx.result(g.up.concat(g.down));                       // "조건에 맞는 행 담기" 버튼이 이 행들을 바구니에 넣는다
ctx.summary(`DEG ${nDeg}개 (증가 ${nUp} · 감소 ${nDn})`);  // "조건 복사"·review Markdown 에 들어간다
