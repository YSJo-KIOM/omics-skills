// 검증 실험 표본 수 — 두 군 평균 비교의 검정력 (정규 근사). 데이터 없이 조건만으로 계산하는 시뮬레이션형 위젯 예시.
// ctx.v = {d, n, alpha}
const {d, n, alpha} = ctx.v;

function erf(x) {            // Abramowitz–Stegun 7.1.26 (오차 < 1.5e-7)
  const s = Math.sign(x), a = Math.abs(x), t = 1 / (1 + 0.3275911 * a);
  return s * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a));
}
const Phi = x => 0.5 * (1 + erf(x / Math.SQRT2));
function zq(p) {             // 표준정규 분위수 (Acklam 근사)
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const e = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const tail = q => (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((e[0] * q + e[1]) * q + e[2]) * q + e[3]) * q + 1);
  if (p < 0.02425) return tail(Math.sqrt(-2 * Math.log(p)));
  if (p > 1 - 0.02425) return -tail(Math.sqrt(-2 * Math.log(1 - p)));
  const q = p - 0.5, r = q * q;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

const za = zq(1 - alpha / 2);
const power = m => { const k = Math.abs(d) * Math.sqrt(m / 2); return Phi(k - za) + Phi(-k - za); };
const ns = Array.from({length: 49}, (_, i) => i + 2);
const need = ns.find(m => power(m) >= 0.8);
const pw = power(n);

ctx.cards([
  {value: Math.round(100 * pw) + "%", label: `군당 ${n}명일 때 검정력`, tone: pw >= 0.8 ? "good" : "warn"},
  {value: need ? need + "명" : "50명 초과", label: "검정력 80% 에 필요한 군당 표본"}
]);
ctx.plot("curve", [
  {type: "scatter", mode: "lines", x: ns, y: ns.map(power), line: {color: ctx.color("acc"), width: 2}, hovertemplate: "군당 %{x}명 → %{y:.0%}<extra></extra>"},
  {type: "scatter", mode: "markers", x: [n], y: [pw], marker: {size: 12, color: ctx.color("c2")}, hovertemplate: "현재 %{x}명 → %{y:.0%}<extra></extra>"}
], {
  height: 300, showlegend: false,
  xaxis: {title: {text: "군당 표본 수"}}, yaxis: {title: {text: "검정력"}, range: [0, 1.02], tickformat: ".0%"},
  shapes: [{type: "line", xref: "paper", x0: 0, x1: 1, y0: 0.8, y1: 0.8, line: {dash: "dot", width: 1, color: ctx.color("mut")}}]
});
ctx.note("정규 근사라 실제 t 검정보다 1–2명 적게 나온다. 확정 전에는 G*Power 나 <code>pwr::pwr.t.test</code> 로 다시 계산한다.");
ctx.summary(`d=${d}, α=${alpha}, 군당 ${n}명 → 검정력 ${Math.round(100 * pw)}% (80% 에는 군당 ${need || ">50"}명)`);
