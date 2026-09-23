"""Build the FloMo v3 HTML slide deck from story.BEATS.

Output: <out>/index.html + <out>/assets/ (copied media + Inter). Self-contained;
open index.html in any browser. Keys: arrows / space = step or slide, N = notes,
O = overview, Home/End. Run: python video/release/v3/deck.py --out video/release/v3/out/deck
"""
import argparse
import html
import json
import shutil
from pathlib import Path

from PIL import Image

from story import BEATS, MEDIA, TITLE, media_keys

FONTS = Path(__file__).resolve().parents[1] / "fonts"
ARCH_W, ARCH_H = 1603, 720  # figures/fig_arch.png

CSS = """
:root{--ink:#1F2733;--muted:#5B6675;--line:#DFE4E9;--panel:#F6F8FA;--orange:#F09018;--orange-d:#B86600;
--teal:#307890;--teal-d:#245D70;--soft-teal:#EAF3F5;--soft-orange:#FCF1E3;--t1:#A8D6D8;--t2:#65B3B7;--t3:#3D8E92}
@font-face{font-family:Inter;src:url(assets/fonts/Inter-Regular.ttf);font-weight:400}
@font-face{font-family:Inter;src:url(assets/fonts/Inter-Medium.ttf);font-weight:500}
@font-face{font-family:Inter;src:url(assets/fonts/Inter-SemiBold.ttf);font-weight:600}
@font-face{font-family:Inter;src:url(assets/fonts/Inter-Bold.ttf);font-weight:700}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#E9ECEF;font-family:Inter,system-ui,sans-serif;color:var(--ink);overflow:hidden}
#viewport{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
#stage{position:relative;width:1920px;height:1080px;background:#fff;transform-origin:center center;
box-shadow:0 8px 40px rgba(0,0,0,.18);overflow:hidden}
.slide{position:absolute;inset:0;padding:96px 96px 72px;display:none;flex-direction:column}
.slide.active{display:flex}
.body{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;margin:44px 0 18px}
.body>.row{width:100%;justify-content:center}
.pane.fill{align-self:stretch;width:100%}
.hl{font-weight:600;font-size:60px;line-height:1.12;letter-spacing:-.02em;max-width:1560px}
.hl.center{text-align:center;margin:0 auto}
.sub{font-weight:500;font-size:34px;line-height:1.3;color:var(--muted);margin-top:18px;max-width:1500px}
.sub.center{text-align:center;margin-left:auto;margin-right:auto}
.wm{position:absolute;top:56px;right:96px;width:150px}
.num{position:absolute;bottom:40px;right:96px;font-size:20px;color:var(--muted);font-weight:500}
.pane{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.pane video,.pane img{display:block;width:100%;height:100%;object-fit:cover}
.pane img.fit{object-fit:contain;background:#fff}
.lab{font-size:24px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-top:14px;text-align:center}
.lab b{color:var(--ink);font-weight:600}
.cap{align-self:flex-start;max-width:1500px;background:#fff;border:1px solid var(--line);
border-radius:12px;padding:20px 26px;font-size:27px;line-height:1.35;font-weight:500}
.cap.wide{max-width:1728px}
.chip{display:inline-block;font-size:22px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;
padding:8px 14px;border:1px solid var(--line);border-radius:10px;color:var(--ink);background:#fff}
.chip.orange{color:var(--orange-d);border-color:#F4C98A;background:var(--soft-orange)}
.row{display:flex;gap:24px;align-items:flex-start}
.col{display:flex;flex-direction:column;gap:24px}
.badge{position:absolute;top:16px;left:16px;font-size:22px;font-weight:600;padding:6px 14px;border-radius:8px;color:#fff;letter-spacing:.04em}
.badge.success{background:#2A8A4F}.badge.failure{background:#B23A48}
.tag{position:absolute;top:16px;right:16px;font-size:22px;font-weight:600;padding:6px 14px;border-radius:8px;background:rgba(255,255,255,.92);border:1px solid var(--line)}
/* title: one centred group, wordmark / title / accent bar / credits */
.title{position:absolute;left:96px;right:96px;top:50%;transform:translateY(-50%);text-align:center}
.title .wmbig{display:block;width:760px;margin:0 auto 44px}
.title .hl{font-size:60px;max-width:1400px;margin:0 auto}
.title .bar{width:120px;height:4px;border-radius:2px;background:var(--orange);margin:40px auto 0}
.title .c{font-size:26px;font-weight:500;color:var(--muted);margin-top:40px}
/* stats */
.stat{display:flex;align-items:baseline;gap:18px}
.stat .v{font-weight:700;font-size:72px;letter-spacing:-.02em;font-variant-numeric:tabular-nums;min-width:200px;text-align:right}
.stat .l{font-size:28px;font-weight:500;color:var(--muted)}
.stat.first .l{color:var(--ink)}
.statlab{font-size:22px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:10px}
/* table */
table.ood{border-collapse:collapse;width:1728px;font-size:28px}
table.ood th{font-weight:600;color:var(--muted);text-align:center;padding:14px 10px;border-bottom:2px solid var(--line);font-size:24px;text-transform:uppercase;letter-spacing:.05em}
table.ood td{text-align:center;padding:22px 10px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
table.ood th.l,table.ood td.l{text-align:left;padding-left:18px}
table.ood tr.ours td{background:var(--soft-orange);font-weight:600}
table.ood tr.ours td.l{color:var(--orange-d)}
table.ood td.agg{font-weight:600}
table.ood tr.dim td{color:var(--muted)}
/* duel */
.duel{display:flex;align-items:stretch;gap:0;margin-top:40px}
.duel .side{width:560px;height:260px;box-sizing:border-box;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:28px 34px}
.duel .name{font-size:28px;font-weight:600}
.duel .score{font-size:110px;font-weight:700;letter-spacing:-.03em;line-height:1.05;margin:6px 0 10px}
.duel .good .score{color:var(--orange)}.duel .bad .score{color:var(--teal-d)}
.duel .meter{height:18px;border-radius:9px;background:#E3E7EB;overflow:hidden}
.duel .fill{height:100%;border-radius:9px;background:var(--orange)}
.duel .bad .fill{background:var(--teal)}
.duel .vs{width:120px;text-align:center;align-self:center;font-size:30px;font-weight:600;color:var(--muted)}
/* cards */
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:26px 30px;width:420px}
.card .v{font-size:64px;font-weight:700;letter-spacing:-.02em;line-height:1.05}
.card .l{font-size:25px;color:var(--muted);margin-top:8px;line-height:1.3;font-weight:500}
.card.human .v{color:var(--teal-d)}.card.robot .v{color:var(--orange)}
/* insights */
.insight{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:28px 32px;height:640px;display:flex;flex-direction:column}
.insight .big{display:flex;align-items:baseline;gap:16px}
.insight .big b{font-size:84px;font-weight:700;color:var(--orange);letter-spacing:-.03em}
.insight .big span{font-size:28px;font-weight:500;line-height:1.25;max-width:520px}
.insight .fig{flex:1;margin:18px 0;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.insight .fig img{width:100%;height:100%;object-fit:contain;display:block}
/* tasks */
.task{width:560px}
.task .pane{width:560px;height:400px}
.task .name{font-size:32px;font-weight:600;margin-top:18px}
.task .desc{font-size:25px;color:var(--muted);line-height:1.35;margin-top:6px;font-weight:500}
/* spotlight */
.spot{position:relative;overflow:hidden;border-radius:12px;border:1px solid var(--line);background:#fff}
.spot .fig{position:absolute;overflow:hidden}
.spot img{position:absolute;display:block}
.spot svg{position:absolute;inset:0;width:100%;height:100%}
.steplist{position:absolute;top:260px;display:flex;flex-direction:column;gap:18px}
.si{display:flex;gap:16px;align-items:flex-start;visibility:hidden}
.si.on{visibility:visible}
.si .k{flex:none;min-width:40px;text-align:center;font-size:22px;font-weight:600;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:10px;padding:6px 12px;white-space:nowrap}
.si.cur .k{color:var(--orange-d);background:var(--soft-orange);border-color:#F4C98A}
.si .t{font-size:26px;font-weight:500;line-height:1.3;color:var(--muted);padding-top:5px}
.si.cur .t{color:var(--ink)}
/* notes + overview */
#notes{position:absolute;left:0;right:0;bottom:0;background:#1F2733;color:#fff;font-size:22px;line-height:1.45;padding:18px 28px;display:none;max-height:38%;overflow:auto;font-family:Inter,sans-serif}
#notes.show{display:block}
#notes b{color:#F4C98A}
body.overview #viewport{display:none}
#grid{display:none;position:absolute;inset:0;overflow:auto;padding:24px;gap:18px;grid-template-columns:repeat(4,1fr)}
body.overview #grid{display:grid}
#grid .thumb{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;cursor:pointer;aspect-ratio:16/9;position:relative}
#grid .thumb .i{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;pointer-events:none}
#grid .thumb .k{position:absolute;left:8px;bottom:6px;font-size:13px;color:var(--muted);background:rgba(255,255,255,.9);padding:2px 6px;border-radius:4px}
#help{position:absolute;left:16px;bottom:10px;font-size:13px;color:#6b7480;font-family:Inter,sans-serif;animation:hide 1s 6s forwards}
@keyframes hide{to{opacity:0}}
"""

JS = """
const slides=[...document.querySelectorAll('#stage .slide')];
let cur=0, step=0;
function maxStep(i){const s=slides[i];let m=0;s.querySelectorAll('[data-step]').forEach(e=>{m=Math.max(m,+e.dataset.step)});s.querySelectorAll('.spot').forEach(sp=>{m=Math.max(m,JSON.parse(sp.dataset.rings).length)});return m}
function applyStep(){const s=slides[cur];
 s.querySelectorAll('[data-step]').forEach(e=>{e.classList.toggle('on',+e.dataset.step<=step);e.classList.toggle('cur',+e.dataset.step===step)});
 s.querySelectorAll('[data-only]').forEach(e=>{e.style.display=(+e.dataset.only===step)?'':'none'});
 const sp=s.querySelector('.spot'); if(sp) spot(sp, step);}
function show(i,st){cur=Math.max(0,Math.min(slides.length-1,i));step=st===undefined?0:st;
 slides.forEach((s,k)=>{s.classList.toggle('active',k===cur);s.querySelectorAll('video').forEach(v=>{if(k===cur){v.currentTime=0;v.play().catch(()=>{})}else v.pause()})});
 applyStep(); location.hash='#'+(cur+1); notes.innerHTML=slides[cur].dataset.notes||'';}
function next(){if(step<maxStep(cur)){step++;applyStep()}else if(cur<slides.length-1)show(cur+1)}
function prev(){if(step>0){step--;applyStep()}else if(cur>0)show(cur-1,maxStep(cur-1))}
function fit(){const k=Math.min(innerWidth/1920,innerHeight/1080)*0.98;document.getElementById('stage').style.transform='scale('+k+')'}
function spot(sp,st){const boxes=JSON.parse(sp.dataset.boxes);const ringsBy=JSON.parse(sp.dataset.rings);const revealBy=JSON.parse(sp.dataset.reveal);
 const S=+sp.dataset.scale, ox=+sp.dataset.ox, oy=+sp.dataset.oy; const svg=sp.querySelector('svg'); const all=st>=ringsBy.length;
 let holes='',rings='';
 const box=(n,pad)=>{const b=boxes[n];return [ox+b[0]*S-pad, oy+b[1]*S-pad, (b[2]-b[0])*S+2*pad, (b[3]-b[1])*S+2*pad]};
 if(!all){
  revealBy.slice(0,st+1).flat().forEach(n=>{const[x,y,w,h]=box(n,6);
   holes+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="black"/>`;});
  ringsBy[st].forEach(n=>{const[x,y,w,h]=box(n,10);
   rings+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="none" stroke="#F09018" stroke-width="4"/>`;});}
 const W=sp.clientWidth,H=sp.clientHeight;
 svg.innerHTML=all?'':`<defs><mask id="m${sp.id}"><rect width="${W}" height="${H}" fill="white"/>${holes}</mask></defs>
  <rect width="${W}" height="${H}" fill="white" fill-opacity="0.82" mask="url(#m${sp.id})"/>${rings}`;}
const notes=document.getElementById('notes');
addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();next()}
 else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();prev()}
 else if(e.key==='Home')show(0);else if(e.key==='End')show(slides.length-1);
 else if(e.key==='n'||e.key==='N')notes.classList.toggle('show');
 else if(e.key==='o'||e.key==='O'){document.body.classList.toggle('overview');if(document.body.classList.contains('overview'))buildGrid()}
 else if(e.key==='Escape')document.body.classList.remove('overview')});
addEventListener('resize',fit);
function buildGrid(){const g=document.getElementById('grid');g.innerHTML='';slides.forEach((s,k)=>{const t=document.createElement('div');t.className='thumb';
 const c=s.cloneNode(true);c.classList.add('active');c.querySelectorAll('[data-step]').forEach(e=>e.classList.add('on'));c.querySelectorAll('video').forEach(v=>{v.removeAttribute('autoplay');v.preload='metadata'});
 const i=document.createElement('div');i.className='i';i.appendChild(c);t.appendChild(i);
 const kk=document.createElement('div');kk.className='k';kk.textContent=(k+1)+' '+s.dataset.id;t.appendChild(kk);
 t.onclick=()=>{document.body.classList.remove('overview');show(k)};g.appendChild(t);
 const w=t.clientWidth;i.style.transform='scale('+(w/1920)+')';});}
addEventListener('hashchange',()=>{const h=parseInt(location.hash.slice(1));if(!isNaN(h)&&h-1!==cur)show(h-1)});
fit();const h=parseInt(location.hash.slice(1));show(isNaN(h)?0:h-1);
"""


def esc(s):
    return html.escape(s, quote=True)


def video(src, cls="", extra=""):
    return (f'<video class="{cls}" src="assets/{src}" autoplay muted loop playsinline preload="auto" {extra}></video>')


def pane(inner, w, h, style="", cls=""):
    return f'<div class="pane {cls}" style="width:{w}px;height:{h}px;{style}">{inner}</div>'


def header(b, center=False):
    c = " center" if center else ""
    out = f'<div class="hl{c}">{esc(b["headline"])}</div>'
    if "sub" in b:
        out += f'<div class="sub{c}">{esc(b["sub"])}</div>'
    return out


def caption(b, wide=False):
    if "caption" not in b:
        return ""
    return f'<div class="cap{" wide" if wide else ""}">{esc(b["caption"])}</div>'


def wordmark():
    return '<img class="wm" src="assets/figures/wordmark.png" alt="">'


def body(inner):
    """Content region centred between the header and the caption (render.content_y mirrors it)."""
    return f'<div class="body">{inner}</div>'


def k_title(b):
    credits = f'<div class="c">{esc(b["credits"])}</div>' if b["credits"] else ""
    return (f'<div class="title"><img class="wmbig" src="assets/figures/wordmark.png" alt="FloMo">'
            f'<div class="hl center">{esc(b["headline"])}</div><div class="bar"></div>{credits}</div>')


def k_figure(b):
    fig = b["media"]["figure"]
    return (header(b) + wordmark()
            + body(f'<div class="pane fill"><img class="fit" src="assets/{fig}"></div>')
            + caption(b, wide=True))


def k_pair(b):
    m = b["media"]
    badges = b["badges"] if "badges" in b else [None, None]
    inner = []
    for key, lab, bd in zip([m["left"], m["right"]], b["labels"], badges):
        badge = f'<div class="badge {bd}">{bd.upper()}</div>' if bd else ""
        w, h = (852, 479) if key.startswith("footage/") else (660, 495)
        inner.append(f'<div class="col" style="gap:0">{pane(video(key) + badge, w, h)}<div class="lab">{esc(lab)}</div></div>')
    return header(b) + wordmark() + body(f'<div class="row">{"".join(inner)}</div>') + caption(b, wide=True)


def k_triptych(b):
    m = b["media"]
    cells = []
    for key, lab in zip(m["panes"], b["labels"]):
        cells.append(f'<div class="col" style="gap:0">{pane(video(key), 560, 420)}<div class="lab">{esc(lab)}</div></div>')
    return header(b) + wordmark() + body(f'<div class="row">{"".join(cells)}</div>') + caption(b, wide=True)


SPOT_PAD = 20  # inner margin so the step rings (box + 10 px, 4 px stroke) stay inside the pane


def spot_geom(crop):
    """Spotlight pane: the crop at up to native scale (720 px tall max) inside a SPOT_PAD margin,
    left-aligned; the step list fills the rest.
    Returns (scale, pane_w, pane_h, ox, oy, list_x, list_w). render.k_spotlight uses the same numbers."""
    bw, bh = crop[2] - crop[0], crop[3] - crop[1]
    s = min(1000 / bw, 720 / bh, 1.0)
    pw, ph = round(bw * s) + 2 * SPOT_PAD, round(bh * s) + 2 * SPOT_PAD
    ox = SPOT_PAD - crop[0] * s
    oy = SPOT_PAD - crop[1] * s
    lx = 96 + pw + 40
    return s, pw, ph, ox, oy, lx, 1920 - 96 - lx


def k_spotlight(b, boxes):
    m = b["media"]
    crop = boxes[b["crop"]]
    s, pw, ph, ox, oy, lx, lw = spot_geom(crop)
    rings = [r for r, _, _ in b["steps"]]
    reveal = [rv for _, rv, _ in b["steps"]]
    lst = "".join(f'<div class="si" data-step="{i}"><div class="k">{i + 1}</div><div class="t">{esc(t)}</div></div>'
                  for i, (_, _, t) in enumerate(b["steps"]))
    return (header(b) + wordmark()
            + f'<div class="spot" id="sp_{b["id"]}" style="position:absolute;left:96px;top:260px;width:{pw}px;height:{ph}px" '
              f'data-scale="{s:.5f}" data-ox="{ox:.2f}" data-oy="{oy:.2f}" '
              f"data-boxes='{json.dumps(boxes)}' data-rings='{json.dumps(rings)}' data-reveal='{json.dumps(reveal)}'>"
              f'<div class="fig" style="left:{SPOT_PAD}px;top:{SPOT_PAD}px;width:{(crop[2] - crop[0]) * s:.2f}px;height:{(crop[3] - crop[1]) * s:.2f}px">'
              f'<img src="assets/{m["figure"]}" style="left:{-crop[0] * s:.2f}px;top:{-crop[1] * s:.2f}px;width:{ARCH_W * s:.2f}px;height:{ARCH_H * s:.2f}px"></div>'
              f'<svg></svg></div>'
            + f'<div class="steplist" style="left:{lx}px;width:{lw}px">{lst}</div>')


def k_pair_cards(b):
    m = b["media"]
    panes = "".join(
        f'<div class="col" style="gap:0">{pane(video(k), 620, 465)}<div class="lab" style="font-size:21px">{esc(lab)}</div></div>'
        for k, lab in zip([m["left"], m["right"]], b["labels"]))
    cards = "".join(
        f'<div class="card {cls}"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div></div>'
        for (v, l), cls in zip(b["cards"], ["human", "robot"]))
    return (header(b) + wordmark()
            + body(f'<div class="row" style="gap:28px">{panes}<div class="col" style="gap:24px;height:465px">{cards}</div></div>')
            + caption(b, wide=True))


def k_tasks(b):
    cells = []
    for key, (name, desc) in zip(b["media"]["clips"], b["tasks"]):
        cells.append(f'<div class="task">{pane(video(key), 560, 400)}<div class="name">{esc(name)}</div><div class="desc">{esc(desc)}</div></div>')
    chip = f'<div><span class="chip orange">{esc(b["chip"])}</span></div>'
    return (header(b) + wordmark()
            + body(f'<div class="col" style="gap:20px;width:100%">{chip}<div class="row">{"".join(cells)}</div></div>')
            + caption(b, wide=True))


def fig_pane(key):
    """Figure pane size: 520 tall for landscape figures, 680 for portrait; width follows the aspect."""
    fw, fh = Image.open(MEDIA / key).size
    h = 680 if fh > fw else 520
    return min(1000, round(h * fw / fh)), h


def k_chart_fig(b):
    stats = "".join(
        f'<div class="stat{" first" if i == 0 else ""}"><div class="v" style="color:{c}">{esc(v)}</div><div class="l">{esc(l)}</div></div>'
        for i, (v, l, c) in enumerate(b["stats"]))
    pw, ph = fig_pane(b["media"]["figure"])
    return (header(b) + wordmark()
            + body(f'<div class="row" style="gap:40px;align-items:center">'
                   f'<div class="pane" style="width:{pw}px;height:{ph}px"><img class="fit" src="assets/{b["media"]["figure"]}"></div>'
                   f'<div class="col" style="gap:10px;width:640px"><div class="statlab">{esc(b["stat_label"])}</div>{stats}</div></div>')
            + caption(b, wide=True))


def k_table(b):
    head = "".join(f'<th>{esc(c)}</th>' for c in b["columns"])
    rows = []
    for name, per, agg, sr, tp in b["rows"]:
        ours = name == "FloMo"
        cls = "ours" if ours else ("dim" if "no human" in name else "")
        cells = "".join(f'<td>{esc(x)}</td>' for x in per)
        rows.append(f'<tr class="{cls}"><td class="l">{esc(name)}</td>{cells}<td class="agg">{esc(agg)}</td>'
                    f'<td class="agg">{sr}</td><td>{tp}</td></tr>')
    table = (f'<table class="ood"><thead><tr><th class="l">Method</th>{head}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>')
    return header(b) + wordmark() + body(table) + caption(b, wide=True)


def k_duel(b):
    (v1, n1), (v2, n2) = b["duel"]
    duel = (f'<div class="statlab">{esc(b["duel_label"])}</div>'
            f'<div class="duel" style="margin-top:8px"><div class="side good"><div class="name">{esc(n1)}</div><div class="score">{esc(v1)}</div>'
            f'<div class="meter"><div class="fill" style="width:{int(v1[:-1])}%"></div></div></div>'
            f'<div class="vs">vs</div><div class="side bad"><div class="name">{esc(n2)}</div><div class="score">{esc(v2)}</div>'
            f'<div class="meter"><div class="fill" style="width:{int(v2[:-1])}%"></div></div></div></div>')
    m = b["media"]
    panes = "".join(
        f'<div class="col" style="position:absolute;left:1376px;top:{344 + i * 345}px;gap:0">{pane(video(k), 380, 285)}'
        f'<div class="lab" style="font-size:20px">{esc(lab)}</div></div>'
        for i, (k, lab) in enumerate(zip([m["left"], m["right"]], b["labels"])))
    return (header(b) + wordmark()
            + f'<div style="position:absolute;left:96px;top:485px;width:1240px">{duel}</div>' + panes  # cards centred on the video stack (344-974)
            + caption(b, wide=True))


def k_insights(b):
    m = b["media"]
    cards = []
    for key, (big, txt) in zip([m["left"], m["right"]], b["insights"]):
        cards.append(f'<div class="insight"><div class="big"><b>{esc(big)}</b><span>{esc(txt)}</span></div>'
                     f'<div class="fig"><img src="assets/{key}"></div></div>')
    return header(b) + wordmark() + body(f'<div class="row" style="gap:32px">{"".join(cards)}</div>')


KINDS = dict(title=k_title, figure=k_figure, pair=k_pair, triptych=k_triptych, pair_cards=k_pair_cards,
             tasks=k_tasks, chart_fig=k_chart_fig, table=k_table, duel=k_duel, insights=k_insights)


def build(out):
    out = Path(out)
    assets = out / "assets"
    (assets / "fonts").mkdir(parents=True, exist_ok=True)
    for f in FONTS.glob("Inter-*.ttf"):
        shutil.copy2(f, assets / "fonts" / f.name)
    copied = []
    for k in media_keys() + ["figures/wordmark.png"]:
        src = MEDIA / k
        if not src.exists():
            raise FileNotFoundError(src)
        dst = assets / k
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)
        copied.append(k)
    boxes = json.loads((MEDIA / "figures/arch_boxes.json").read_text())
    slides = []
    for i, b in enumerate(BEATS):
        body = k_spotlight(b, boxes) if b["kind"] == "spotlight" else KINDS[b["kind"]](b)
        notes = esc(f"{b['id']} ({b['dur']:.0f} s in the video). " + b["notes"])
        slides.append(f'<section class="slide k-{b["kind"]}" data-id="{b["id"]}" data-notes="{notes}">{body}'
                      f'<div class="num">{i + 1} / {len(BEATS)}</div></section>')
    page = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>FloMo — {esc(TITLE)}</title>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>'
            f'<body><div id="viewport"><div id="stage">{"".join(slides)}</div></div>'
            f'<div id="grid"></div><div id="notes"></div>'
            f'<div id="help">&larr; &rarr; step / slide &middot; N notes &middot; O overview &middot; #n deep link</div>'
            f'<script>{JS}</script></body></html>')
    (out / "index.html").write_text(page)
    print(f"wrote {out / 'index.html'} ({len(BEATS)} slides, {len(copied)} assets)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    build(ap.parse_args().out)
