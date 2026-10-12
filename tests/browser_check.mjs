// Browser check for the interactive-report runtime (needs google-chrome + Node >= 22 for built-in WebSocket).
// Build the examples first, then:
//   node tests/browser_check.mjs "file:///abs/out/analysis.html#deg" analysis
//   node tests/browser_check.mjs "file:///abs/out/literature.html" literature
import { spawn } from "node:child_process";
const [, , url, which] = process.argv;
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu", `--remote-debugging-port=${port}`,
  `--user-data-dir=${process.env.TMPDIR || "/tmp"}/ir-cdp-${port}`, "about:blank"], {stdio: "ignore"});
const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0; const pending = new Map(); const errors = [];
for (let k = 0; k < 50; k++) { try { const r = await fetch(`http://127.0.0.1:${port}/json`); const t = (await r.json()).find(x => x.type === "page"); if (t) { ws = new WebSocket(t.webSocketDebuggerUrl); break; } } catch {} await sleep(200); }
await new Promise(r => ws.addEventListener("open", r));
ws.addEventListener("message", e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map(a => a.value).join(" ")); });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });
const ev = async (expr) => { const r = await send("Runtime.evaluate", {expression: `(async()=>{${expr}})()`, awaitPromise: true, returnByValue: true}); if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description); return r.result.result.value; };
await send("Runtime.enable"); await send("Page.enable");
await send("Page.navigate", {url}); await sleep(3500);
const H = `const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],w=ms=>new Promise(r=>setTimeout(r,ms));
const fire=(el,t)=>el.dispatchEvent(new Event(t,{bubbles:true}));const cnt=el=>el.closest('.tblock').querySelector('.cnt').textContent;`;
const checks = [];
const ok = (name, cond, info) => { checks.push([cond ? "PASS" : "FAIL", name, info]); };
if (which === "analysis") {
  let r = await ev(H + `const sec=$('#sec-deg'),pad=sec.querySelectorAll('.cf')[2];pad.value='<0.01';fire(pad,'input');await w(400);
    const c1=cnt(pad);const dir=sec.querySelector('.cs');dir.value='up';fire(dir,'change');await w(400);
    const pills=[...sec.querySelectorAll('tbody tr td:nth-child(6) .pill')].map(p=>p.textContent);
    const gd=sec.querySelector('.chart');await w(400);const npts=gd.data?gd.data.reduce((s,t)=>s+(t.name==='선택됨'?0:t.x.length),0):-1;
    return {c1,c2:cnt(pad),pills:[...new Set(pills)],npts};`);
  const n2 = +r.c2.match(/필터 결과 (\d+)/)[1];
  ok("padj<0.01 filter narrows rows", /필터 결과 (\d+)/.exec(r.c1)[1] < 400, r.c1);
  ok("direction=up dropdown keeps only up", r.pills.length === 1 && r.pills[0] === "up", r.pills.join(","));
  ok("volcano redraws with table filter", r.npts === n2, `points=${r.npts} rows=${n2}`);
  r = await ev(H + `const sec=$('#sec-deg');sec.querySelector('[data-a="add"]').click();await w(300);
    return {bk:$('#ir-bkn').textContent,sel:sec.querySelectorAll('tbody tr.sel').length,shown:sec.querySelectorAll('tbody tr').length};`);
  ok("'보이는 행 담기' fills basket", +r.bk === n2 && r.sel === r.shown, JSON.stringify(r));
  r = await ev(H + `const sec=$('#sec-deg');sec.querySelector('[data-a="reset"]').click();await w(300);const c0=cnt(sec.querySelector('.cf'));
    const s=sec.querySelectorAll('.rmin')[0];s.value=2;fire(s,'input');await w(400);const vals=[...sec.querySelectorAll('tbody tr td:nth-child(2)')].map(t=>parseFloat(t.textContent));
    return {c0,c1:cnt(s),min:Math.min(...vals)};`);
  ok("reset restores 400 rows", /전체 400/.test(r.c0) && /필터 결과 400/.test(r.c0), r.c0);
  ok("log2FC slider min=2 filters", r.min >= 2, `min shown=${r.min} ${r.c1}`);
  r = await ev(H + `const sec=$('#sec-deg');sec.querySelector('[data-a="reset"]').click();await w(300);const th=sec.querySelectorAll('tr.hrow th')[1];th.click();await w(200);th.click();await w(300);
    const v=[...sec.querySelectorAll('tbody tr td:nth-child(2)')].slice(0,5).map(t=>parseFloat(t.textContent));const e=sec.querySelectorAll('.cf')[1];e.value='abs>=3';fire(e,'input');await w(400);
    const a=[...sec.querySelectorAll('tbody tr td:nth-child(2)')].map(t=>Math.abs(parseFloat(t.textContent)));return {v,amin:Math.min(...a),n:a.length};`);
  ok("header click sorts descending", r.v.every((x, i, A) => i === 0 || A[i - 1] >= x), r.v.join(","));
  ok("expression abs>=3 works", r.amin >= 3 && r.n > 0, `n=${r.n} min|x|=${r.amin}`);
  r = await ev(H + `$$('#ir-nav button').find(b=>b.textContent==='다음 단계').click();await w(300);const sec=$('#sec-next');
    sec.querySelector('input[type=radio][value=top10]').click();const ta=sec.querySelector('.rv-f textarea');ta.value='GAPDH 대신 ACTB';fire(ta,'input');
    sec.querySelector('input[type=checkbox][value=tf]').click();await w(400);sec.querySelector('[data-a="gen"]').click();await w(100);
    const md=sec.querySelector('.rv-out textarea').value;return {md,hash:location.hash,stored:Object.keys(localStorage).filter(k=>k.includes('review')).length};`);
  ok("review markdown has choice + desc", r.md.includes("**선정 방식**: padj 상위 10개 — 효과가 가장 확실한 것부터"), r.md.split("\n").slice(0, 12).join(" | "));
  ok("review markdown has textarea quote", r.md.includes("  > GAPDH 대신 ACTB"));
  ok("review markdown has multi option", r.md.includes("전사인자 활성 (decoupleR)"));
  ok("review markdown includes basket table", /## 관심 항목 \(선택 바구니 \d+행\)/.test(r.md) && r.md.includes("| gene | log2FC |"));
  ok("unanswered field marked 미정", r.md.includes("**중심 축**: (미정)"));
  ok("tab switch updates hash", r.hash === "#next", r.hash);
  ok("review state autosaved", r.stored >= 1, `keys=${r.stored}`);
  r = await ev(H + `$$('#ir-nav button').find(b=>b.textContent==='기능 분석').click();await w(800);const gd=$('#sec-function .chart');
    return {bars:gd.data?gd.data[0].y.length:-1,textpos:gd.data?gd.data[0].textposition:null,lazy:$$('#sec-function .chart').map(c=>!!c.data)};`);
  ok("bar chart drawn lazily on tab show, top 15", r.bars === 15, JSON.stringify(r));
  ok("chart inside closed <details> not drawn yet", r.lazy[1] === false, JSON.stringify(r.lazy));
  r = await ev(H + `$('#ir-basket [data-a="clear"]').click();await w(100);$('#ir-basket [data-a="clear"]').click();await w(300);return $('#ir-bkn').textContent;`);
  ok("basket clear needs two clicks and empties", r === "0", r);
} else {
  const r = await ev(H + `$$('#ir-nav button').find(b=>b.textContent==='근거 표').click();await w(300);const sec=$('#sec-evidence');
    const sels=sec.querySelectorAll('.cs');const kw=sels[sels.length-1];kw.value='count';fire(kw,'change');await w(300);
    const tools=[...sec.querySelectorAll('tbody tr td:first-child')].map(t=>t.textContent);
    const links=[...sec.querySelectorAll('tbody a')].map(a=>a.href);sec.querySelector('tbody tr').click();await w(200);
    return {tools,links,bk:$('#ir-bkn').textContent,year:sec.querySelector('tbody tr td:nth-child(3)').textContent};`);
  ok("multi-value keyword dropdown (sep) filters", JSON.stringify(r.tools.sort()) === JSON.stringify(["DESeq2", "edgeR"]), r.tools.join(","));
  ok("PMID/DOI link templates", r.links.some(h => h === "https://pubmed.ncbi.nlm.nih.gov/25516281/") && r.links.some(h => h === "https://doi.org/10.1186/s13059-014-0550-8"), r.links.slice(0, 4).join(" "));
  ok("row click adds to basket", r.bk === "1", r.bk);
  ok("year renders without separator", /^\d{4}$/.test(r.year), r.year);
}
ok("no page JS errors", errors.length === 0, errors.join(" || "));
checks.forEach(c => console.log(c[0], c[1], c[2] ? "— " + c[2] : ""));
ws.close(); chrome.kill(); process.exit(checks.some(c => c[0] === "FAIL") ? 1 : 0);
