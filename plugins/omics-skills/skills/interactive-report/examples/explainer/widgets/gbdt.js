// GBDT 원리 — 트리 수 M, 학습률 η, 트리 깊이를 바꾸면 적합 곡선·잔차·손실 곡선이 바로 다시 계산된다.
// 1차원 회귀(제곱오차): F_m = F_{m-1} + η·h_m, h_m 은 잔차 r = y − F_{m-1} 에 맞춘 회귀나무.
const {M, eta, depth} = ctx.v;
const S = ctx.state;

if (!S.data) {                       // 시드 고정 합성 데이터: 완만한 곡선 + x = 6.5 의 계단 + 잡음
  let s = 7;
  const rnd = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const f = x => Math.sin(0.9 * x) + (x > 6.5 ? 1.6 : 0);
  const make = n => Array.from({length: n}, () => { const x = 10 * rnd(); return {x, y: f(x) + 0.35 * gauss()}; }).sort((a, b) => a.x - b.x);
  S.data = {train: make(80), test: make(300), f};
}
const {train, test, f} = S.data;

if (S.key !== eta + "|" + depth) {   // η·깊이가 바뀔 때만 트리 100개를 새로 만든다. M 은 앞에서부터 잘라 쓴다.
  const xs = train.map(p => p.x);
  const fit = (idx, r, d) => {        // 정렬된 index 에서 SSE 가 가장 줄어드는 분할점을 찾는다
    const tot = idx.reduce((a, i) => a + r[i], 0), tot2 = idx.reduce((a, i) => a + r[i] * r[i], 0), n = idx.length;
    if (d === 0 || n < 4) return {v: tot / n};
    let best = null, sl = 0, sl2 = 0;
    for (let k = 1; k < n; k++) {
      const v = r[idx[k - 1]]; sl += v; sl2 += v * v;
      if (k < 2 || n - k < 2 || xs[idx[k]] === xs[idx[k - 1]]) continue;
      const sse = (sl2 - sl * sl / k) + ((tot2 - sl2) - (tot - sl) ** 2 / (n - k));
      if (!best || sse < best.sse) best = {sse, k};
    }
    if (!best) return {v: tot / n};
    return {t: (xs[idx[best.k - 1]] + xs[idx[best.k]]) / 2, l: fit(idx.slice(0, best.k), r, d - 1), r: fit(idx.slice(best.k), r, d - 1)};
  };
  const pred = (node, x) => node.v !== undefined ? node.v : pred(x < node.t ? node.l : node.r, x);
  const base = train.reduce((a, p) => a + p.y, 0) / train.length;
  const F = train.map(() => base), Ft = test.map(() => base), trees = [], resid = [], lossTr = [], lossTe = [];
  const mse = (ps, Fs) => ps.reduce((a, p, i) => a + (p.y - Fs[i]) ** 2, 0) / ps.length;
  const all = train.map((_, i) => i);
  for (let m = 0; m < 100; m++) {
    const r = train.map((p, i) => p.y - F[i]);
    const tree = fit(all, r, depth);
    trees.push(tree); resid.push(r);
    train.forEach((p, i) => { F[i] += eta * pred(tree, p.x); });
    test.forEach((p, i) => { Ft[i] += eta * pred(tree, p.x); });
    lossTr.push(mse(train, F)); lossTe.push(mse(test, Ft));
  }
  Object.assign(S, {key: eta + "|" + depth, trees, resid, base, pred, lossTr, lossTe});
}
const {trees, resid, base, pred, lossTr, lossTe} = S;

const grid = Array.from({length: 401}, (_, i) => i * 0.025);
const FM = grid.map(x => { let v = base; for (let k = 0; k < M; k++) v += eta * pred(trees[k], x); return v; });
const best = lossTe.indexOf(Math.min(...lossTe)) + 1;

ctx.cards([
  {value: M, label: "트리 수 M"},
  {value: lossTr[M - 1].toFixed(3), label: "학습 MSE"},
  {value: lossTe[M - 1].toFixed(3), label: "검증 MSE", tone: M > best * 1.5 && lossTe[M - 1] > lossTe[best - 1] * 1.05 ? "warn" : ""},
  {value: "m = " + best, label: "검증 MSE 가 가장 낮은 지점", note: "early stopping 이 고를 트리 수"}
]);

const pts = {color: ctx.color("ink"), size: 5, opacity: 0.55};
ctx.plot("fit", [
  {type: "scatter", mode: "markers", name: "학습 데이터", x: train.map(p => p.x), y: train.map(p => p.y), marker: pts, hovertemplate: "x %{x:.2f}<br>y %{y:.2f}<extra></extra>"},
  {type: "scatter", mode: "lines", name: "참 함수", x: grid, y: grid.map(f), line: {color: ctx.color("mut"), dash: "dot", width: 1}, hoverinfo: "skip"},
  {type: "scatter", mode: "lines", name: `F_${M}(x)`, x: grid, y: FM, line: {color: ctx.color("c2"), width: 2.5}, hovertemplate: "F(x) %{y:.2f}<extra></extra>"}
], {height: 290, xaxis: {title: {text: "x"}}, yaxis: {title: {text: "y"}}, legend: {orientation: "h", y: 1.12}});

const r = resid[M - 1];             // M 번째 트리가 학습한 잔차 = y − F_{M−1}
ctx.plot("residual", [
  {type: "scatter", mode: "markers", name: `잔차 r = y − F_${M - 1}`, x: train.map(p => p.x), y: r, marker: {color: ctx.color("c4"), size: 5}, hovertemplate: "r %{y:.2f}<extra></extra>"},
  {type: "scatter", mode: "lines", name: `h_${M}(x): 잔차에 맞춘 트리`, x: grid, y: grid.map(x => pred(trees[M - 1], x)), line: {color: ctx.color("c3"), dash: "dash", width: 2}, hovertemplate: "h(x) %{y:.2f}<extra></extra>"}
], {height: 230, yaxis: {title: {text: "잔차"}, zeroline: true}, legend: {orientation: "h", y: 1.18},
    shapes: [{type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: {color: ctx.color("edge"), width: 1}}]});

const ms = Array.from({length: 100}, (_, i) => i + 1);
ctx.plot("loss", [
  {type: "scatter", mode: "lines", name: "학습", x: ms, y: lossTr, line: {color: ctx.color("c1")}},
  {type: "scatter", mode: "lines", name: "검증", x: ms, y: lossTe, line: {color: ctx.color("c5")}}
], {height: 220, xaxis: {title: {text: "트리 수 m"}}, yaxis: {title: {text: "MSE"}, rangemode: "tozero"}, legend: {orientation: "h", y: 1.2},
    shapes: [{type: "line", x0: M, x1: M, yref: "paper", y0: 0, y1: 1, line: {color: ctx.color("c2"), dash: "dash", width: 1}}]});

const tips = [];
if (eta >= 0.8) tips.push(depth > 1 ? "η 가 크고 트리가 깊으면 트리 몇 개로 학습 데이터를 거의 다 맞추지만 잡음까지 따라간다 — 아래 곡선에서 검증 MSE 가 일찍 바닥을 찍고 다시 오른다."
                         : "η 가 커도 깊이 1(stump)은 한 번에 계단 하나만 더하는 약한 학습기라 과적합이 느리다. 깊이를 2–3 으로 올려 비교해 보자.");
if (eta <= 0.1) tips.push("η 가 작으면 트리가 많이 필요하지만 검증 MSE 의 최저점이 조금 더 낮다 — 실무에서 작은 η + early stopping 을 쓰는 이유.");
tips.push(depth === 1 ? "깊이 1(stump)은 분할 하나짜리 트리라 F 가 계단 하나씩 쌓인다. 변수 하나라 상호작용은 없다."
                      : `깊이 ${depth} 트리는 한 번에 계단 여러 개를 만든다. 변수가 여럿이면 이 깊이가 상호작용 차수가 된다.`);
ctx.note("<ul>" + tips.map(t => "<li>" + t + "</li>").join("") + "</ul>");
ctx.summary(`M=${M}, η=${eta}, 깊이 ${depth} → 학습 MSE ${lossTr[M - 1].toFixed(3)}, 검증 MSE ${lossTe[M - 1].toFixed(3)} (검증 최소 m=${best})`);
