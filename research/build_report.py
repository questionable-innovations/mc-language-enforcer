"""Render report.json into the evidence page (inline SVG charts, theme-variable colours)."""
import json, pathlib, sys

TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:var(--font-sans);color:var(--foreground)}
.wrap{display:flex;flex-direction:column;gap:22px}
h2{font-size:15px;margin:0 0 4px;font-weight:600}
p.lede{margin:0 0 10px;color:var(--muted-foreground);font-size:12.5px;line-height:1.5}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.panel h3{font-size:12.5px;font-weight:600;margin:0 0 2px}
.panel .sub{font-size:11px;color:var(--muted-foreground);margin-bottom:6px}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:11.5px;color:var(--muted-foreground);margin:2px 0 8px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{display:inline-block;width:14px;height:3px;border-radius:2px}
.legend i.sq{width:10px;height:10px;border-radius:3px}
svg text{font-family:var(--font-sans)}
.axis{fill:var(--muted-foreground);font-size:10.5px}
.lbl{fill:var(--foreground);font-size:11.5px}
.val{fill:var(--muted-foreground);font-size:10.5px;font-variant-numeric:tabular-nums}
.grp{fill:var(--muted-foreground);font-size:10.5px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.grid{stroke:var(--border);stroke-width:1}
.hit:hover{opacity:.85}
details{font-size:11.5px;color:var(--muted-foreground);margin-top:4px}
table{border-collapse:collapse;width:100%;font-size:11.5px;margin-top:6px}
th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--border);vertical-align:top}
th{color:var(--muted-foreground);font-weight:600}
td.num{font-variant-numeric:tabular-nums;text-align:right}
.pill{display:inline-block;padding:0 6px;border-radius:999px;font-size:10.5px;border:1px solid var(--border)}
.pill.bad{color:var(--destructive);border-color:var(--destructive)}
.pill.ok{color:var(--success);border-color:var(--success)}
.callout{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:12px 14px;font-size:12.5px;line-height:1.55}
.callout b{font-weight:600}
@media (max-width:600px){.grid2{grid-template-columns:1fr}}
</style></head><body><div class="wrap" id="root"></div>
<script>
const R = __DATA__;
const C = i => `var(--chart-${i})`;
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs={}, parent){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e;}
function h(html){const d=document.createElement('div');d.innerHTML=html;return d.firstElementChild;}
function legend(items, sq){return `<div class="legend">${items.map(([n,c])=>`<span><i class="${sq?'sq':''}" style="background:${c}"></i>${n}</span>`).join('')}</div>`;}

function lineChart(host, {x, series, title, sub}) {
  const W=340,H=190,L=34,Rr=20,T=8,B=24, pw=W-L-Rr, ph=H-T-B;
  const p=h(`<div class="panel"><h3>${title}</h3><div class="sub">${sub}</div></div>`); host.appendChild(p);
  const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,width:'100%',role:'img','aria-label':title},p);
  const xp=i=>L+pw*i/(x.length-1), yp=v=>T+ph*(1-v/100);
  for(const v of [0,25,50,75,100]){el('line',{x1:L,x2:W-Rr,y1:yp(v),y2:yp(v),class:'grid'},svg);const t=el('text',{x:L-6,y:yp(v)+3.5,'text-anchor':'end',class:'axis'},svg);t.textContent=v+'%';}
  x.forEach((lab,i)=>{const t=el('text',{x:xp(i),y:H-6,'text-anchor':'middle',class:'axis'},svg);t.textContent=lab;});
  for(const s of series){
    const pts=s.values.map((v,i)=>v==null?null:[xp(i),yp(v),v,x[i]]).filter(Boolean);
    el('polyline',{points:pts.map(p=>p[0]+','+p[1]).join(' '),fill:'none',stroke:s.color,'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'},svg);
    for(const [px,py,v,xl] of pts){const g=el('g',{class:'hit'},svg);el('circle',{cx:px,cy:py,r:9,fill:'transparent'},g);el('circle',{cx:px,cy:py,r:4,fill:s.color,stroke:'var(--background)','stroke-width':2},g);el('title',{},g).textContent=`${s.name} · ${xl}: ${v.toFixed(1)}%`;}
  }
}

function barChart(host, {rows, series, max=100, unit='%', fmt=v=>v.toFixed(0)+unit, labelW=210}) {
  const rowH=12*series.length+(series.length-1)*2+12, W=700, L=labelW, Rr=46;
  let y=4; const layout=[];
  for(const r of rows){ if(r.group){layout.push({group:r.group,y:y+12});y+=22;continue;} layout.push({...r,y}); y+=rowH; }
  const H=y+18, pw=W-L-Rr;
  const svg=el('svg',{viewBox:`0 0 ${W} ${H}`,width:'100%',role:'img'},host);
  const xs=v=>L+pw*Math.min(v,max)/max;
  for(const f of [0,.25,.5,.75,1]){el('line',{x1:xs(max*f),x2:xs(max*f),y1:0,y2:H-16,class:'grid'},svg);const t=el('text',{x:xs(max*f),y:H-3,'text-anchor':'middle',class:'axis'},svg);t.textContent=fmt(max*f);}
  for(const r of layout){
    if(r.group){const t=el('text',{x:0,y:r.y,class:'grp'},svg);t.textContent=r.group;continue;}
    const t=el('text',{x:0,y:r.y+rowH/2+1,class:'lbl'},svg);t.textContent=r.label;
    series.forEach((s,i)=>{const v=r.values[i]; if(v==null)return; const by=r.y+4+i*14, w=Math.max(xs(v)-L,1.5);
      const g=el('g',{class:'hit'},svg);
      el('path',{d:`M${L},${by} h${Math.max(w-4,0)} a4,4 0 0 1 4,4 v4 a4,4 0 0 1 -4,4 h${-Math.max(w-4,0)} z`,fill:s.color},g);
      const vt=el('text',{x:L+w+5,y:by+9.5,class:'val'},g);vt.textContent=fmt(v)+(r.n?'':'');
      el('title',{},g).textContent=`${r.label} · ${s.name}: ${fmt(v)}${r.n?` (n=${r.n})`:''}`;});
  }
}

const root=document.getElementById('root');
const SHOW=__SHOW__;
const add=(n,node)=>{if(SHOW.includes(n))root.appendChild(node);return node;};
const D=R.durs.filter(d=>d!=='full'), XL=D.map(d=>d+' s');
const LM=[['ecapa','ECAPA (VoxLingua107)',C(3)],['whisper-tiny','Whisper tiny',C(2)],['whisper-small','Whisper small',C(1)]].filter(m=>R.lid[m[0]]);
const sec1=h(`<section><h2>Evidence 1 · Language ID alone is right about natives and wrong about learners</h2><p class="lede">Every clip went through Opus VOIP at 24 kbps (SVC's codec) and was cut to the first N seconds of speech. Flag rule: P(Mandarin) &lt; 0.1. English is caught at 98–100% at every length for every model, so it isn't charted. Learner speech is the problem, and bigger models make it worse.</p>${legend(LM.map(m=>[m[1],m[2]]))}<div class="grid2"></div></section>`);
add(1,sec1); const g2=sec1.querySelector('.grid2');
// points backed by fewer than 20 clips are hidden (the short phrase sets thin out past 2 s)
const pick=(m,s)=>D.map(d=>R.lid[m][s]&&R.lid[m][s][d]&&R.lid[m][s][d][1]>=20?R.lid[m][s][d][0]:null);
lineChart(g2,{x:XL,title:'Native Mandarin wrongly flagged',sub:'FLEURS cmn, 150 speakers · lower is better',series:LM.map(([m,n,c])=>({name:n,color:c,values:pick(m,'cmn_hans_cn')}))});
lineChart(g2,{x:XL,title:'Learner Mandarin wrongly flagged',sub:'anglophone-accent proxy, 120 phrases · lower is better',series:LM.map(([m,n,c])=>({name:n,color:c,values:pick(m,'phr_zh_learner')}))});

const VM=R.verdict_model, V=R.verdict[VM];
const row=(s,label)=>({label:label||R.sets[s],n:V[s]&&V[s].full?V[s].full.n:0,values:V[s]&&V[s].full?[V[s].full.lid_only,V[s].full.two_stage]:[null,null]});
const sec2=h(`<section><h2>Evidence 2 · The second stage protects learners and still catches English</h2><p class="lede">% of whole utterances flagged by <b>${R.model_names[VM]}</b>. Learner sets are proxies: English TTS voices reading respelled or raw pinyin, and real native speech with its tones flattened. The two-stage rule only punishes when the forced English transcript is real, confident English.</p>${legend([['Language ID only',C(3)],['Two-stage verdict',C(1)]],true)}</section>`);
add(2,sec2);
barChart(sec2,{series:[{name:'Language ID only',color:C(3)},{name:'Two-stage verdict',color:C(1)}],rows:[
  {group:'Should pass (lower is better)'},row('cmn_hans_cn'),row('phr_zh_native'),row('fleurs_zh_flat'),row('phr_zh_learner'),row('phr_zh_pinyin'),
  {group:'Should be caught (higher is better)'},row('en_us'),row('phr_en'),row('l2_zh_scripted'),row('l2_zh_spont'),row('ja_jp'),row('ko_kr'),row('vi_vn'),row('es_419'),row('de_de'),row('yue_hant_hk','Cantonese (counts as Chinese)')]});
const st=R.stream[VM];
sec2.appendChild(h(`<div class="callout"><b>Mid-sentence cut-off</b> (checks at 2 s, 3 s, end): English speech is cut by 2 s in <b>${st.en_us.cut_by_2s}%</b> of utterances and by 3 s in <b>${st.en_us.cut_by_3s}%</b>; <b>${st.en_us.cut_pct}%</b> are caught by the end. Across all three checks, native Mandarin is wrongly cut in <b>${st.cmn_hans_cn.cut_pct}%</b> and toneless Mandarin in <b>${st.fleurs_zh_flat.cut_pct}%</b>.</div>`));

const lat=R.latency, LMOD=[...new Set(lat.map(r=>r.model))];
if(lat.length){
const getL=(m,dev,c)=>{const r=lat.find(r=>r.model===m&&r.device===dev&&r.compute===c);return r?parseFloat(r.lid_ms)+parseFloat(r.dual_decode_ms):null;};
const sec3=h(`<section><h2>Evidence 3 · Whisper small fits a GTX 1080; CPU-only servers drop to base</h2><p class="lede">Median time to fully judge one 3-second utterance (language ID plus both forced decodes). Most Mandarin stops after language ID (about a quarter of the total). Measured on an RTX 3090 in <b>float32</b>, the precision a GTX 1080 runs well. The 1080 bar is an estimate: 3.5× the 3090 float32 time, from the cards' FP32 throughput and memory-bandwidth ratios. CPU is 4 threads, int8.</p>${legend([['RTX 3090 float32 (measured)',C(1)],['GTX 1080 (estimated)',C(3)],['CPU 4 threads int8 (measured)',C(2)]],true)}</section>`);
add(3,sec3);
const lmax=Math.max(...LMOD.map(m=>Math.max(getL(m,'cuda','float32')*3.5,getL(m,'cpu','int8')||0)));
const cap=Math.ceil(lmax/500)*500;
barChart(sec3,{max:cap,unit:' ms',fmt:v=>Math.round(v)+' ms',labelW:150,series:[{name:'RTX 3090 float32',color:C(1)},{name:'GTX 1080 est.',color:C(3)},{name:'CPU int8',color:C(2)}],
  rows:LMOD.map(m=>({label:R.model_names[m],values:[getL(m,'cuda','float32'),getL(m,'cuda','float32')*3.5,getL(m,'cpu','int8')]}))});
}

const ex=R.examples;
const sec4=h(`<section><h2>What the second stage actually sees</h2><p class="lede">${R.model_names[VM]}, whole utterances. The same two transcripts become the in-game feedback: pinyin for Mandarin, a "try saying…" hint for English.</p>
<table><thead><tr><th>Set</th><th class="num">P(zh)</th><th>Forced English decode</th><th>Forced Mandarin decode</th><th>Verdict</th></tr></thead><tbody>
${ex.map(e=>`<tr><td>${R.sets[e.set]}</td><td class="num">${e.p_zh.toFixed(2)}</td><td>${e.en_text||'—'}</td><td>${e.zh_text||'—'}</td><td>${e.flag?'<span class="pill bad">cut</span>':'<span class="pill ok">pass</span>'}</td></tr>`).join('')}
</tbody></table></section>`);
add(4,sec4);
</script></body></html>"""

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    data["verdict_model"] = sys.argv[3]
    show = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [1, 2, 3, 4]
    data["model_names"] = {
        "ecapa": "ECAPA (VoxLingua107)", "whisper-tiny": "Whisper tiny", "whisper-base": "Whisper base",
        "whisper-small": "Whisper small", "whisper-medium": "Whisper medium",
        "whisper-turbo": "Whisper large-v3-turbo", "whisper-large-v3": "Whisper large-v3",
    }
    pathlib.Path(sys.argv[2]).write_text(TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__SHOW__", json.dumps(show)))
