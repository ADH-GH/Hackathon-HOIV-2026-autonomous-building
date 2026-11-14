"""The dashboard page: HTML, CSS and JavaScript in one string. No external requests."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
__FONTS__
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2310141c'/%3E%3Ccircle cx='32' cy='32' r='21' fill='%23508cdc' fill-opacity='.22'/%3E%3Ccircle cx='32' cy='32' r='11' fill='%23508cdc'/%3E%3C/svg%3E">
<title>__TITLE__</title>
<style>
/* Dark control-room look: deep background, layered panels, monospace figures, small caps labels.
   Dark is the default; a light theme is available through the toggle. Fonts fall back to the system's
   unless the page was built with --web-fonts. */
/* Colours and fonts follow the project's showcase page (hoiv-hackathon-2026.lovable.app), so both look like one product. */
:root{--bg:oklch(19% .022 258);--panel:oklch(23.5% .024 258);--raise:oklch(28.5% .025 258);--ink:oklch(95% .008 250);--ink2:oklch(82% .014 252);--mute:oklch(70% .018 253);
--line:oklch(32% .025 258);--grid:oklch(27.5% .022 258);--series:oklch(65.8% .128 251);--ref:oklch(70% .018 253);--accent:oklch(65.8% .128 251);--onaccent:oklch(16% .02 258);
--glow:oklch(65.8% .128 251 / .18);--mark:oklch(78% .14 80);--band:oklch(70% .14 155 / .12);
--crit:oklch(70% .19 22);--high:oklch(78% .14 80);--med:oklch(84% .1 105);--low:oklch(70% .018 253);--auto:oklch(70% .14 155);--appr:oklch(78% .14 80);--cons:oklch(70% .19 22);--ours:oklch(65.8% .128 251);
--mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:"IBM Plex Sans",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;--display:"Sora",ui-sans-serif,system-ui,-apple-system,sans-serif}
:root[data-theme="light"]{--bg:oklch(97% .005 250);--panel:#ffffff;--raise:oklch(95% .008 250);--ink:oklch(20% .02 258);--ink2:oklch(40% .02 255);--mute:oklch(52% .02 255);--line:oklch(87% .01 255);--grid:oklch(92% .008 255);
--series:oklch(52% .15 251);--ref:oklch(55% .02 255);--accent:oklch(52% .15 251);--onaccent:#ffffff;--glow:oklch(52% .15 251 / .14);--mark:oklch(58% .14 70);--band:oklch(60% .14 155 / .12);
--crit:oklch(52% .2 25);--high:oklch(55% .14 65);--med:oklch(50% .1 95);--low:oklch(50% .02 255);--auto:oklch(50% .14 155);--appr:oklch(55% .14 65);--cons:oklch(52% .2 25);--ours:oklch(52% .15 251)}
*{box-sizing:border-box}
html{color-scheme:dark}:root[data-theme="light"]{color-scheme:light}
body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
h1,h2,h3,h4{font-family:var(--display);letter-spacing:-.01em}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header{padding:12px 48px 0;max-width:1536px;margin:32px auto 0}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.kicker{font:500 12.5px/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.kicker::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--glow);margin-right:10px;vertical-align:1px}
h1{margin:22px 0 13px;font:600 38px/1.1 var(--display);letter-spacing:-.02em}
.sub{color:var(--mute);font-size:12.5px;margin-top:5px;overflow-wrap:anywhere}
.hlink{display:inline-flex;align-items:center;height:36px;font:600 14px/1 var(--sans);color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:0 14px;margin-right:6px;vertical-align:top}
.hlink[hidden]{display:none}
footer{line-height:1.6}footer a{color:var(--ink2)}
#theme{height:36px;font:600 14px/1 var(--sans);color:var(--ink);background:transparent;border:1px solid var(--line);border-radius:8px;padding:0 14px;cursor:pointer}
#theme:hover{background:var(--raise)}
.hbox{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px 20px 16px}
.top>div:first-child{flex:1 1 0;min-width:0}.top>div:last-child{flex:none;white-space:nowrap}
/* One row of boxes is both the figures and the navigation: each box opens its view, the active one is marked. */
nav{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:8px;margin-top:16px}
nav button{display:flex;flex-direction:column;justify-content:flex-start;align-items:stretch;text-align:left;min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:9px 10px 10px;cursor:pointer;color:var(--ink);font:inherit}
nav button:hover{background:var(--raise);border-color:var(--mute)}
nav button.on{background:var(--raise);border-color:var(--accent);box-shadow:inset 0 -3px 0 var(--accent)}
nav button b{display:block;font:500 28px/1.1 var(--mono);letter-spacing:-.02em;color:var(--series);white-space:nowrap}
nav button i{display:block;white-space:nowrap;font:500 10.5px/1.3 var(--mono);font-style:normal;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin-top:6px}
nav button span{display:block;font:500 12px/1.3 var(--sans);letter-spacing:-.01em;color:var(--ink2);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav button.on span{color:var(--ink)}
nav button small{display:block;font-size:11px;line-height:1.35;color:var(--mute);margin-top:3px}
@media (max-width:1320px){nav{gap:6px}nav button{padding:8px 7px 9px}nav button span{font-size:11px;letter-spacing:-.02em}nav button b,.tiles .tile b,.duo .tiles .tile b{font-size:24px}}
@media (max-width:1100px){nav{grid-auto-columns:112px;overflow-x:auto;scrollbar-width:thin;padding-bottom:4px}}
#brief{height:36px;font:600 14px/1 var(--sans);color:var(--onaccent);background:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:0 14px;cursor:pointer;margin-right:8px}
#brief.live{background:transparent;color:var(--ink);border-color:var(--line)}
#brief[hidden]{display:none}
/* Emergency view: covers the whole dashboard and shows one case only */
#emg{position:fixed;inset:0;z-index:20;background:var(--bg);display:none;overflow:auto;padding:28px 48px 140px}
#emg.on{display:block}
#emg .e-in{max-width:1100px;margin:0 auto}
#emg .e-bar{border:1px solid var(--crit);border-radius:8px;background:color-mix(in srgb,var(--crit) 12%,var(--panel));padding:18px 20px;display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}
#emg .e-eyebrow{font:500 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--crit)}
#emg h1{font:600 30px/1.15 var(--display);letter-spacing:-.01em;margin:8px 0 0}
#emg .e-line{font:500 15px/1.4 var(--sans);color:var(--ink);margin-top:8px}
#emg .e-line b{color:var(--crit)}
#emg .e-sim{font-size:12.5px;color:var(--ink2);margin-top:4px}
#emg button{height:36px;font:600 14px/1 var(--sans);color:var(--ink);background:transparent;border:1px solid var(--line);border-radius:8px;padding:0 14px;cursor:pointer;white-space:nowrap}
#emg .e-facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px}
#emg .e-fact{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;min-width:0}
#emg .e-fact span{display:block;font:500 10.5px/1.3 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
#emg .e-fact b{display:block;font:500 17px/1.3 var(--sans);margin-top:5px;overflow-wrap:anywhere}
#emg .e-sec{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 20px;margin-top:12px}
#emg .e-sec h2{font:600 16px/1.2 var(--display);margin:0 0 8px}
#emg .e-sec p{margin:0;font-size:15px;line-height:1.5;color:var(--ink)}
#emg .e-sec li{font-size:14px;line-height:1.5;color:var(--ink2);margin:3px 0}
#emg .e-sec ul{margin:0;padding-left:18px}
#emg .e-sec li code{font:400 12.5px/1.5 var(--mono);color:var(--ink2);overflow-wrap:anywhere}
@media (max-width:760px){#emg{padding:16px 16px 160px}#emg .e-facts{grid-template-columns:repeat(2,minmax(0,1fr))}#emg h1{font-size:23px}}
#vbox{position:fixed;right:16px;bottom:16px;width:min(380px,calc(100vw - 32px));background:var(--panel);border:1px solid var(--accent);border-radius:8px;padding:12px 14px;z-index:30;display:none}
#vbox.on{display:block}
#vbox .st{font:500 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
#vbox .cap{margin-top:8px;font-size:13px;max-height:170px;overflow:auto;color:var(--ink2)}
#vbox .cap p{margin:4px 0}#vbox .cap p.me{color:var(--ink)}
#vbox small{display:block;margin-top:8px;color:var(--mute);font-size:11px}
.vctl{display:flex;align-items:center;gap:10px;margin-top:10px}
.vctl label{font-size:12.5px;color:var(--ink2)}
#ptt{flex:1;height:44px;font:600 14px/1 var(--sans);border-radius:8px;border:1px solid var(--accent);background:transparent;color:var(--ink);cursor:pointer;user-select:none;-webkit-user-select:none;touch-action:none}
#ptt.down{background:var(--accent);color:var(--onaccent)}
#emgBtn{flex:1;height:36px;font:600 14px/1 var(--sans);border-radius:8px;border:1px solid var(--crit);background:transparent;color:var(--crit);cursor:pointer}
#ptt:disabled{opacity:.45;cursor:default}
.vtype{display:flex;gap:6px;margin-top:8px}
.vtype input{flex:1;min-width:0;height:36px;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:0 10px}
.vtype button{height:36px;font:600 14px/1 var(--sans);color:var(--ink);background:transparent;border:1px solid var(--line);border-radius:8px;padding:0 12px;cursor:pointer}
.wrap{max-width:1536px;margin:0 auto;padding:12px 48px 20px}
.tiles{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:8px}
@media (max-width:1100px){.tiles{grid-auto-flow:row;grid-template-columns:repeat(auto-fit,minmax(120px,1fr))}}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:9px 10px 10px;min-width:0}
.tile b{display:block;font:500 28px/1.1 var(--mono);letter-spacing:-.02em;color:var(--series);white-space:nowrap}
.tile span{display:block;font:500 10.5px/1.35 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin-top:6px;overflow-wrap:anywhere}
.tile small{display:block;font-size:11px;line-height:1.35;color:var(--mute);margin-top:3px}
.card .tiles .tile{background:var(--panel)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:20px;margin-top:12px;min-width:0}
.card h2{margin:0 0 4px;font:600 18px/1.3 var(--display);letter-spacing:-.01em;color:var(--ink)}
.card p.note{margin:0 0 12px;color:var(--mute);font-size:14px}
.split{display:grid;grid-template-columns:minmax(270px,370px) 1fr;gap:12px;align-items:start}
@media (max-width:820px){.split{grid-template-columns:1fr}}
.list{background:var(--panel);border:1px solid var(--line);border-radius:8px;max-height:80vh;overflow:auto}
@media (max-width:820px){.list{max-height:38vh}}
.list .tools{padding:10px 12px;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink2);position:sticky;top:0;background:var(--panel);z-index:1}
.row{padding:10px 12px;border-bottom:1px solid var(--grid);cursor:pointer}
.row:hover{background:var(--raise)}
.row.on{background:var(--raise);box-shadow:inset 3px 0 0 var(--accent)}
.row .t{font:400 11.5px/1.3 var(--mono);color:var(--mute)}
.row .a{font-weight:600;margin-top:2px;overflow-wrap:anywhere}
.tag{display:inline-block;font:500 11px/1.8 var(--mono);letter-spacing:.04em;border:1px solid currentColor;border-radius:6px;padding:0 8px;margin:3px 4px 0 0;white-space:nowrap}
.tag.p-critical::before,.tag.p-high::before,.tag.p-medium::before,.tag.p-low::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:5px;vertical-align:1px}
.p-critical{color:var(--crit)}.p-high{color:var(--high)}.p-medium{color:var(--med)}.p-low{color:var(--low)}
.l-autonomous{color:var(--auto)}.l-human_approval{color:var(--appr)}.l-approval_and_consent{color:var(--cons)}
.tag.plain{color:var(--ink2);background:var(--raise);border-color:var(--line)}
.detail .hero{margin-top:0}
.detail .hero h3{margin:0;font:600 22px/1.2 var(--display);letter-spacing:-.01em;overflow-wrap:anywhere}
.chain{display:grid;gap:8px;margin-top:8px}
.step{border:1px solid var(--line);border-left:3px solid var(--ours);border-radius:8px;padding:14px 16px;background:var(--raise);min-width:0}
.step .h{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.step .h b{font:600 16px/1.2 var(--display);letter-spacing:-.01em;text-transform:capitalize}
.step .h time{font:400 11.5px/1 var(--mono);color:var(--mute)}
.step p{margin:7px 0 0;overflow-wrap:anywhere}
.step .k{font:500 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin-top:12px}
.step pre{margin:4px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 var(--mono);color:var(--ink2)}
.step .v{margin-top:4px;color:var(--ink2)}
.msg{margin-top:8px;padding:9px 11px;border-radius:8px;background:var(--panel);border:1px dashed var(--line)}
.check{border:1px dashed var(--mute);border-radius:8px;padding:9px 12px;margin-top:12px;font-size:13.5px;color:var(--ink2)}
.check b{color:var(--ink)}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:12px;color:var(--ink2);margin:2px 0 6px}
.legend i{display:inline-block;width:18px;height:0;border-top:2px solid var(--series);vertical-align:middle;margin-right:6px}
.legend i.ref{border-top:2px dashed var(--ref)}
.legend i.mark{border-top:0;border-left:2px solid var(--mark);height:12px;width:0}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{font:10.5px var(--mono);fill:var(--mute)}
svg .lbl{fill:var(--ink2)}.lbl.in{font:500 11.5px/1 var(--mono);letter-spacing:.04em;paint-order:stroke;stroke:var(--panel);stroke-width:3px;stroke-linejoin:round;pointer-events:none}
#tip{position:fixed;left:0;top:0;width:max-content;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12px;line-height:1.4;padding:7px 9px;border-radius:6px;max-width:300px;z-index:9;display:none}
.log{margin:6px 0 0;padding:0;list-style:none;font-size:13.5px}
.log li{display:grid;grid-template-columns:104px 1fr;gap:8px;padding:5px 0;border-bottom:1px solid var(--grid)}
.log time{font:400 11.5px/1.7 var(--mono);color:var(--mute)}
.log .ours{color:var(--ours);font-weight:600}
.bars{display:grid;gap:7px;margin-top:6px}
.bar{display:grid;grid-template-columns:56px 1fr 64px;gap:10px;align-items:center;font:400 12.5px/1 var(--mono);color:var(--ink2)}
.bar div{height:10px;border-radius:0 4px 4px 0;background:var(--series)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{font:500 11px/1.3 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
td.n{text-align:right;font-family:var(--mono);white-space:nowrap}
td.m{font:400 12px/1.6 var(--mono);color:var(--ink2);white-space:nowrap}
tr.go{cursor:pointer}tr.go:hover{background:var(--raise)}
.scroll{overflow-x:auto}
.empty{padding:28px 14px;color:var(--mute)}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0 6px}
.filters input[type=search]{flex:1 1 260px;width:auto;margin:0}
.filters select,.filters button{height:36px;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:0 10px;cursor:pointer}
.filters button{background:transparent;font-weight:600}.filters .fcount{font:500 12.5px/1 var(--mono);color:var(--mute);margin-left:auto;white-space:nowrap}
@media (max-width:700px){.filters select{flex:1 1 45%}.filters .fcount{margin-left:0}}
input[type=search]{height:36px;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:0 12px;width:100%;margin-top:8px}
.act{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;padding-top:10px;border-top:1px dashed var(--line)}
.act button{height:36px;font:600 14px/1 var(--sans);border-radius:8px;padding:0 16px;cursor:pointer;border:1px solid var(--line);background:transparent;color:var(--ink)}
.act button:hover{background:var(--panel)}
.act button.ok{border-color:var(--accent);background:var(--accent);color:var(--onaccent)}
.act button.ok:hover{filter:brightness(1.08);background:var(--accent)}
.act button.no{border-color:var(--line);color:var(--ink)}
.act button:disabled{opacity:.4;cursor:not-allowed}
.act label{font-size:12.5px;color:var(--ink2)}
.act .state{font:600 12px/1.4 var(--mono)}
.act .state.approved{color:var(--auto)}.act .state.rejected{color:var(--crit)}
.act small{flex-basis:100%;color:var(--mute);font-size:11.5px}
@media (max-width:700px){
  header{padding:12px 16px 0}.hbox{padding:14px 14px 10px}.wrap{padding:10px 16px 14px}footer{padding:4px 16px 28px}h1{font-size:29px}
  .tiles{grid-auto-flow:row;grid-template-columns:repeat(2,minmax(0,1fr))}.tiles .tile b{font-size:21px}
  .card{padding:12px}.scroll table{min-width:680px}
  .step .h b{flex-basis:100%}.act button{padding:11px 14px}
  .log li{grid-template-columns:1fr;gap:0}
  svg text{font-size:11px}
}
/* phone: title above the buttons, all ten navigation boxes visible, tables as cards */
@media (max-width:700px){
  header{margin-top:0;padding-top:calc(44px + env(safe-area-inset-top, 0px))}.hbox{padding-top:20px}
  .top{flex-direction:column;align-items:stretch;gap:12px}
  .top>div:last-child{display:flex;gap:8px}.top>div:last-child button{flex:1;margin:0}
  nav{grid-auto-flow:row;grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-columns:auto;overflow:visible;gap:6px;padding-bottom:0}
  nav button{padding:7px 5px 8px 7px}nav button b,.tiles .tile b{font-size:21px}nav button i{font-size:9.5px;margin-top:4px}
  nav button span{font-size:10.5px;letter-spacing:-.01em;line-height:1.2;white-space:normal;overflow:visible;min-height:2.4em;overflow-wrap:normal}
  .scroll{overflow-x:visible}.scroll table{min-width:0;display:block}
  .scroll table tbody{display:block}.scroll table tr{display:block;border:1px solid var(--line);border-radius:8px;background:var(--bg);padding:8px 10px;margin-top:8px}
  .scroll table tr:has(th){display:none}
  .scroll table td{display:grid;grid-template-columns:104px minmax(0,1fr);gap:8px;border:0;padding:3px 0;text-align:left;white-space:normal;overflow-wrap:anywhere}
  .scroll table td::before{content:attr(data-l);font:500 9.5px/1.5 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--mute)}
  .scroll table td:empty{display:none}
  .scroll table td>*{justify-self:start}
  td.n,td.m{text-align:left;white-space:normal}
}
.bld{display:block;width:100%;height:auto;max-height:700px;overflow:hidden;touch-action:pan-y;cursor:grab;user-select:none;-webkit-user-select:none}
.bld:active{cursor:grabbing}.bld .bx.hit{cursor:pointer}.bld .bx:hover polygon{stroke:var(--ink);stroke-width:1.2}
.bld .bn{font:600 13px/1 var(--mono);fill:var(--bg);pointer-events:none}.bld .bn.lo{fill:var(--ink)}
.bld .bl{font:500 10px/1 var(--mono);letter-spacing:.08em;fill:var(--ink2);pointer-events:none}
.bld .bf{font:500 10.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;fill:var(--mute)}
.legend i.sw{width:12px;height:12px;border:0;border-radius:3px;vertical-align:-1px}
:root{--c2:oklch(76% .09 195);--c3:oklch(58% .03 255);--hot:oklch(78% .17 58);--cool:oklch(40% .045 235)}
svg text.ax{font:400 11px/1 var(--mono);fill:var(--mute)}
.card h3{font:600 14px/1.3 var(--display);margin:16px 0 4px}
.legend.big{font-size:13.5px;gap:6px 18px;margin-top:4px;margin-bottom:0}.legend.big .wide{color:var(--mute);margin-left:auto;cursor:help}.legend.big i.sw{width:15px;height:15px;border-radius:4px;vertical-align:-2px;margin-right:8px}
.bldwrap{position:relative}.seg{display:flex;gap:6px;flex-wrap:wrap}
.bldhead{display:flex;align-items:center;justify-content:space-between;gap:10px 16px;flex-wrap:wrap}.bldhead h2{margin:0}.bldctl{display:flex;gap:6px 14px;align-items:center;flex-wrap:wrap}
.duo>.card>.note{margin:6px 0 4px}.duo>.card>.note.one{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.duo>.card>h2{min-height:34px;display:flex;align-items:center;margin:0}.tlstrip{display:block;width:100%}
.seg button{height:32px;font:600 13px/1 var(--sans);color:var(--ink2);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:0 12px;cursor:pointer}
.seg button.on{color:var(--ink);border-color:var(--accent);box-shadow:inset 0 -2px 0 var(--accent)}.bldzoom{display:flex;gap:6px}
.bldzoom button{width:32px;height:32px;font:500 20px/1 var(--sans);color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;cursor:pointer}
.bldzoom button:hover{border-color:var(--mute);background:var(--raise)}
.duo{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;align-items:stretch;margin-bottom:0}
.duo>.card{margin:0;display:flex;flex-direction:column}
.duo .tiles{flex:1;grid-auto-flow:row;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:1fr}
.duo .tiles .tile{display:flex;flex-direction:column;justify-content:center;padding:10px 14px 11px}
.duo .tiles .tile b{font-size:28px}
@media (max-width:1100px){.duo{grid-template-columns:1fr}.duo .tiles{flex:none;grid-auto-rows:auto}.duo .tiles .tile{justify-content:flex-start}.duo .tiles .tile b{font-size:23px}}
@media (max-width:700px){.duo .tiles .tile b{font-size:21px}.duo .tiles .tile{padding:9px 10px 10px}}
/* one size for the blue figures in the header boxes and in the key figures, at every width; placed last so it wins */
@media (max-width:1320px){nav button b,.tiles .tile b,.duo .tiles .tile b{font-size:24px}}
@media (max-width:700px){nav button b,.tiles .tile b,.duo .tiles .tile b{font-size:21px}}
circle.dot,.bld g.bx{transition:opacity .12s ease}
.duo.linkdots circle.dot{opacity:.16}.duo.linkdots circle.dot.lit{opacity:1;stroke:var(--ink);stroke-width:2.5}
.duo.linkrooms .bld g.bx{opacity:.22}.duo.linkrooms .bld g.bx.lit{opacity:1}.duo.linkrooms .bld g.bx.lit polygon{stroke:var(--ink);stroke-width:1.8}
/* comfort: motion, hover, focus */
header{position:sticky;top:0;z-index:5;background:var(--bg)}
.tile{transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
.tile.go{cursor:pointer}.tile.go:hover{background:var(--raise);border-color:var(--accent)}
.card,.step,.list{animation:rise .28s ease both}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.row{transition:background .12s ease;position:relative}
.row .spark{position:absolute;right:10px;top:10px;width:72px;height:24px;opacity:.85;pointer-events:none}
.tag{cursor:default}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 color-mix(in srgb,var(--crit) 60%,transparent)}50%{box-shadow:0 0 0 5px transparent}}
path.draw{stroke-dasharray:var(--len);stroke-dashoffset:var(--len);animation:draw .9s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
circle.dot{transition:r .12s ease}
circle.dot:hover{r:8}
.split-bar{display:flex;height:18px;border-radius:9px;overflow:hidden;gap:2px;margin:10px 0 6px}
.split-bar div{height:100%;transition:width .6s ease}
.who-link{display:block;margin:-6px 0 0;overflow:visible}
.legend.who{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:0}.legend.who .tag{margin:0;text-align:center;padding-top:5px;padding-bottom:5px}
@media (max-width:700px){.legend.who{grid-template-columns:1fr;margin-top:8px}}
.keys{font:400 11px/1.5 var(--mono);color:var(--mute);margin-top:6px}
kbd{font:600 10.5px/1 var(--mono);border:1px solid var(--line);border-bottom-width:2px;border-radius:4px;padding:2px 5px;color:var(--ink2);background:var(--panel)}
#toast{position:fixed;left:50%;bottom:22px;transform:translate(-50%,20px);background:var(--ink);color:var(--bg);font:600 12.5px/1.3 var(--sans);padding:10px 14px;border-radius:8px;opacity:0;transition:opacity .2s ease,transform .2s ease;pointer-events:none;z-index:10}
#toast.on{opacity:1;transform:translate(-50%,0)}
.copy{height:36px;font:600 14px/1 var(--sans);color:var(--ink);background:transparent;border:1px solid var(--line);border-radius:8px;padding:0 14px;cursor:pointer;margin-top:12px}
.copy:hover{background:var(--raise)}
.copy:hover,nav button:focus-visible,.row:focus-visible,.act button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}path.draw{stroke-dashoffset:0}}
.still *{animation:none!important;transition:none!important}
@media (max-width:700px){header{position:static}.row .spark{display:none}}
#voice{height:36px;font:600 14px/1 var(--sans);color:var(--onaccent);background:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:0 14px;cursor:pointer;margin-right:8px}
#voice.live{background:var(--crit);border-color:var(--crit)}
#voice[hidden]{display:none}
#vpanel{position:fixed;right:16px;bottom:16px;width:min(360px,calc(100vw - 32px));background:var(--panel);border:1px solid var(--accent);box-shadow:0 0 0 3px var(--glow);border-radius:10px;padding:12px 14px;z-index:8;display:none}
#vpanel.on{display:block}
#vpanel .st{font:600 10.5px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--accent);display:flex;align-items:center;gap:8px}
#vpanel .st i{width:8px;height:8px;border-radius:50%;background:var(--accent)}
#vpanel .cap{margin-top:8px;font-size:13px;max-height:150px;overflow:auto;color:var(--ink2)}
#vpanel .cap p{margin:4px 0}#vpanel .cap p.me{color:var(--ink)}
#vpanel small{display:block;margin-top:8px;color:var(--mute);font-size:11px}
/* A very quiet backdrop, the same as on the showcase page: a dot grid, wide diagonal hairlines and two faint glows */
body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
background-image:radial-gradient(circle at 1px 1px,color-mix(in oklab,var(--ink) 5%,transparent) 1px,transparent 0),
repeating-linear-gradient(45deg,color-mix(in oklab,var(--line) 14%,transparent) 0 1px,transparent 1px 96px),
radial-gradient(ellipse 60% 45% at 85% -5%,color-mix(in oklab,var(--accent) 9%,transparent),transparent 70%),
radial-gradient(ellipse 50% 40% at 5% 105%,color-mix(in oklab,var(--accent) 7%,transparent),transparent 70%);
background-size:26px 26px,auto,auto,auto;
-webkit-mask-image:radial-gradient(90% 80% at 50% 40%,#000 30%,rgb(0 0 0/.45) 100%);mask-image:radial-gradient(90% 80% at 50% 40%,#000 30%,rgb(0 0 0/.45) 100%)}
/* scrollbars in the page's colours: thumb in the border tone, track in the panel tone */
*{scrollbar-width:thin;scrollbar-color:var(--line) transparent}
*::-webkit-scrollbar{width:10px;height:10px}
*::-webkit-scrollbar-track{background:transparent}
*::-webkit-scrollbar-thumb{background:var(--line);border-radius:999px;border:2px solid var(--panel)}
*::-webkit-scrollbar-thumb:hover{background:var(--mute)}
*::-webkit-scrollbar-corner{background:transparent}
html{scrollbar-color:var(--line) var(--bg)}
footer{max-width:1536px;margin:0 auto;padding:4px 48px 32px;color:var(--mute);font-size:12px}
</style>
</head>
<body>
<header>
  <div class="hbox">
  <div class="top">
    <div>
      <div class="kicker">Autonomous building operations · fictional reference property</div>
      <h1 id="title"></h1>
      <div class="sub" id="source"></div>
    </div>
    <div><button id="brief" type="button" hidden>Voice briefing</button><button id="theme" type="button">Light theme</button></div>
  </div>
  <nav id="nav"></nav>
  </div>
</header>
<div class="wrap" id="view"></div>
<footer>PLATO-40 synthetic dataset, proximata Hackathon '26 · Rhomberg track (CC BY 4.0). Every finding concerns the fictional PLATO-40 only. Simulated effects are labelled; nothing here was measured on a real building.<br>Created by Alf-David Heermann, <a href="mailto:alfheermann@gmail.com">alfheermann@gmail.com</a><span id="apifoot" hidden> · <a id="apilink" target="_blank" rel="noopener">API description (Swagger)</a></span></footer>
<div id="tip"></div>
<div id="toast" role="status" aria-live="polite"></div>
<div id="emg" role="alertdialog" aria-modal="true" aria-label="Emergency view"></div>
<div id="vbox" aria-live="polite"><div class="st" id="vst">Voice</div><div class="cap" id="vcap2"></div><div class="vctl"><button id="ptt" type="button">Hold to talk</button><label><input id="pttOn" type="checkbox" checked> push to talk</label></div><div class="vctl"><button id="emgBtn" type="button" title="Show only the open case and connect the emergency team (simulated)">Emergency</button></div><form class="vtype" id="vform"><input id="vtext" type="text" placeholder="or type: status, open R403, approve item 1" aria-label="Type to the assistant" autocomplete="off"><button type="submit">Send</button></form><small>In a loud room: hold the button or the space bar while you speak, release when done. The microphone is closed in between, so the room cannot talk to the assistant. Typing works as well. Approvals happen only on your clear yes; effects are simulated.</small></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const NS = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs, text) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; };
const fmt = (opts) => new Intl.DateTimeFormat('sv-SE', Object.assign({timeZone: 'Europe/Vienna'}, opts));
const F_FULL = fmt({year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'});
const F_DAY = new Intl.DateTimeFormat('de-AT', {timeZone: 'Europe/Vienna', day: '2-digit', month: '2-digit'});
const F_HM = fmt({hour: '2-digit', minute: '2-digit'});
const F_DHM = new Intl.DateTimeFormat('de-AT', {timeZone: 'Europe/Vienna', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'});
const lt = ms => F_FULL.format(new Date(ms));
const dhm = ms => F_DHM.format(new Date(ms));
const level = d => d.autonomy || (d.requires_guest_consent ? 'approval_and_consent' : d.requires_human_approval ? 'human_approval' : 'autonomous');
const LEVEL = {autonomous: 'autonomous', human_approval: 'human approval', approval_and_consent: 'approval + guest consent'};
const SC = {S01: 'S01 Turnaround', S02: 'S02 Water', S03: 'S03 Heating', S04: 'S04 Maintenance', S05: 'S05 Event weekend', ENG: 'L2 Energy', LOG: 'L2 Logistics'};
const TABHINT = {budget: 'Planning: what each metered part of the building costs in electricity, and where the potential is', staff: 'Planning: who works in and for the building, internal and external, with service quality', S01: 'Scenario 1 of the brief: the perfect checkout', S02: 'Scenario 2: the hidden water leak', S03: 'Scenario 3: energy vs comfort', S04: 'Scenario 4: the maintenance cascade', S05: 'Scenario 5: the unexpected weekend',
  ENG: 'Level 2 of the brief, building and energy optimisation (no scenario number there)', LOG: 'Level 2 of the brief, cleaning and logistics (no scenario number there)', queue: 'Decisions that still wait for a person to approve or reject', trail: 'Every decision in order', overview: 'All cases at a glance. The figure counts incidents and plans; the routine guest answers are counted separately, see the header line', };
const KIND = {room_flow: 'Water leak in a room', main_gap: 'Water loss outside the rooms', room_meter: 'Unreliable water meter',
  cop: 'Heat pump degradation', forecast: 'Cold snap ahead', room_temp: 'Guest reports a cold room',
  room_day: 'Room turnaround', day_plan: 'Day capacity shortfall', ahu: 'Ventilation filter', logistics: 'Extra service ordered', energy: 'Battery plan'};
const tsOf = d => Date.parse(d.timestamp_utc);
const E = D.episodes;
const all = E.flatMap(e => e.decisions);
let tab = 'overview', selected = {}, showRoutine = {}, query = '';
/* ---------- approvals: a person decides, the effect is simulated, the log stays in this browser ---------- */
const KEY = 'approvals:' + D.profile + ':' + D.source;
let approvals = {}; try { approvals = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (err) {}
const saveApprovals = () => { if (window.__nosave) return; try { localStorage.setItem(KEY, JSON.stringify(approvals)); } catch (err) {} };
const needs = d => level(d) !== 'autonomous';
const pending = () => all.filter(d => needs(d) && !(approvals[d.event_id] && approvals[d.event_id].state));
function decide(d, state) { const a = approvals[d.event_id] || {}; approvals[d.event_id] = Object.assign(a, {state, at: new Date().toISOString(), action: d.action, assets: d.affected_assets, episode_id: d.episode_id, simulated: true}); saveApprovals(); render(); toast((state === 'approved' ? 'Approved: ' : 'Rejected: ') + d.action.replace(/_/g, ' ') + (state === 'approved' ? ' · executed in simulation' : '')); }
function controls(d) {
  const box = el('div', 'act'), a = approvals[d.event_id] || {}, consent = level(d) === 'approval_and_consent';
  if (a.state) { box.append(el('span', 'state ' + a.state, (a.state === 'approved' ? 'Approved' : 'Rejected') + ' ' + lt(Date.parse(a.at)) + (a.state === 'approved' ? ' · executed in simulation' : ' · not executed')));
    const undo = el('button', null, 'Undo'); undo.type = 'button'; undo.onclick = () => { delete approvals[d.event_id]; saveApprovals(); render(); }; box.append(undo); }
  else { const ok = el('button', 'ok', 'Approve'), no = el('button', 'no', 'Reject'); ok.type = no.type = 'button';
    if (consent) { const lb = el('label'), cb = el('input'); cb.type = 'checkbox'; cb.checked = !!a.consent; ok.disabled = !a.consent;
      cb.onchange = () => { approvals[d.event_id] = Object.assign(approvals[d.event_id] || {}, {consent: cb.checked}); saveApprovals(); ok.disabled = !cb.checked; };
      lb.append(cb, document.createTextNode(' Guest consent is on record')); box.append(lb); }
    ok.onclick = () => decide(d, 'approved'); no.onclick = () => decide(d, 'rejected'); box.append(ok, no); }
  box.append(el('small', null, 'Operator action in this demo. The replay does not change; the effect is simulated and the choice is kept in this browser only.'));
  return box;
}

$('title').textContent = D.title;
const INC = E.filter(e => !e.routine).length, ROUTINE = E.length - INC;
$('source').style.whiteSpace = 'pre-line'; $('source').textContent = 'Dataset: ' + D.profile + ' · ' + all.length + ' decisions in ' + E.length + ' cases (' + INC + ' incidents and plans + ' + ROUTINE + ' routine guest answers; a case can hold several decisions)\nVienna local time · PLATO-40 is fictional, data synthetic, effects simulated';

/* ---------- tooltip ---------- */
const tip = $('tip');
function showTip(ev, html) { tip.innerHTML = html; tip.style.display = 'block';
  // Measure at the left edge first: a fixed box near the right edge shrinks to the space that is left
  // there and would be measured too narrow, then stick out of the window once it is placed.
  tip.style.left = '0px'; tip.style.top = '0px';
  const w = tip.offsetWidth, h = tip.offsetHeight, vw = document.documentElement.clientWidth, vh = window.innerHeight, gap = 12;
  let x = ev.clientX + gap; if (x + w > vw - 6) x = ev.clientX - gap - w;          // no room on the right: open to the left of the pointer
  x = Math.max(6, Math.min(vw - w - 6, x));
  let y = ev.clientY - h - 10; if (y < 6) y = ev.clientY + 18;                      // no room above: open below
  y = Math.max(6, Math.min(vh - h - 6, y));
  tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
function hideTip() { tip.style.display = 'none'; }
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

let toastTimer = null;
function toast(msg) { const t = $('toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('on'), 2200); }
// ?still in the address switches all motion off (for screenshots and print)
const calm = /[?&]still\b/.test(location.search) || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
if (calm) document.documentElement.classList.add('still');
function countUp(node, target, suffix) { if (calm || !isFinite(target)) { node.textContent = target + (suffix || ''); return; }
  const t0 = performance.now(), dur = 600; (function tick(now) { const k = Math.min(1, (now - t0) / dur), v = Math.round(target * (1 - Math.pow(1 - k, 3)));
    node.textContent = v + (suffix || ''); if (k < 1) requestAnimationFrame(tick); })(t0); }
function spark(e) { const S = e.series; if (!S || !S.v) return null; const pts = S.v.map((v, i) => [S.t[i], v]).filter(p => p[1] != null); if (pts.length < 4) return null;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const step = Math.max(1, Math.floor(pts.length / 60)), d = pts.filter((p, i) => i % step === 0).map((p, i) => (i ? 'L' : 'M') + ((p[0] - x0) / (x1 - x0 || 1) * 72).toFixed(1) + ' ' + (22 - (p[1] - y0) / (y1 - y0 || 1) * 20).toFixed(1)).join('');
  const s = svg('svg', {viewBox: '0 0 72 24', class: 'spark', 'aria-hidden': 'true'}); s.append(svg('path', {d, fill: 'none', stroke: 'var(--series)', 'stroke-width': 1.5}));
  const mx = (e.start - x0) / (x1 - x0 || 1) * 72; if (mx >= 0 && mx <= 72) s.append(svg('line', {x1: mx, x2: mx, y1: 1, y2: 23, stroke: 'var(--mark)', 'stroke-width': 1.5})); return s; }
const HINT = {critical: 'Critical: act now, guests or the building are affected', high: 'High: act today', medium: 'Medium: plan it', low: 'Low: routine, for the record',
  autonomous: 'Runs on its own in the mock executor; logged and explainable', human_approval: 'Waits for a person: technician, contractor, room block, on-call, notable cost',
  approval_and_consent: 'Waits for a person and for the guest: entering an occupied room, water shutoff'};
/* ---------- line chart: one axis, hover crosshair ---------- */
function niceTicks(lo, hi, n) { const span = hi - lo || 1, step0 = Math.pow(10, Math.floor(Math.log10(span / n)));
  const step = [1, 2, 5, 10].map(m => m * step0).find(s => span / s <= n) || step0 * 10; const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6)); return out; }
function lineChart(host, o) {
  const narrow = window.innerWidth < 700, W = narrow ? Math.max(300, window.innerWidth - 74) : 820, H = narrow ? 230 : 250, m = {l: narrow ? 34 : 46, r: narrow ? 8 : 14, t: 14, b: 26};
  const t = o.t, lines = o.lines.filter(l => l.v && l.v.some(v => v != null)).map(l => o.cap ? Object.assign({}, l, {raw: l.v, v: l.v.map(v => v == null ? null : Math.min(v, o.cap))}) : l);
  if (!t || !t.length || !lines.length) { host.append(el('div', 'empty', 'No readings in this window.')); return; }
  const vals = lines.flatMap(l => l.v.filter(v => v != null)).concat(o.band || []).concat(o.zero ? [0] : []);
  let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo || 1) * 0.08; lo -= o.zero && lo >= 0 ? 0 : pad; hi += pad;
  const t0 = t[0], t1 = t[t.length - 1] === t0 ? t0 + 1 : t[t.length - 1];
  const x = v => m.l + (v - t0) / (t1 - t0) * (W - m.l - m.r), y = v => H - m.b - (v - lo) / (hi - lo) * (H - m.t - m.b);
  const s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.label});
  for (const v of niceTicks(lo, hi, 5)) { s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'var(--grid)'}));
    s.append(svg('text', {x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end'}, v)); }
  if (o.band) s.append(svg('rect', {x: m.l, width: W - m.l - m.r, y: y(o.band[1]), height: y(o.band[0]) - y(o.band[1]), fill: 'var(--band)'}));
  const spanH = (t1 - t0) / 36e5, nt = narrow ? 2 : 5;
  for (let i = 0; i <= nt; i++) { const tv = t0 + (t1 - t0) * i / nt;
    s.append(svg('text', {x: x(tv), y: H - 8, 'text-anchor': i === 0 ? 'start' : i === nt ? 'end' : 'middle'}, spanH > 96 ? F_DAY.format(new Date(tv)) : dhm(tv))); }
  s.append(svg('text', {x: m.l, y: 10, class: 'lbl'}, o.unit));
  for (const l of lines) { let dpath = '', pen = false;
    l.v.forEach((v, i) => { if (v == null) { pen = false; return; } dpath += (pen ? 'L' : 'M') + x(t[i]).toFixed(1) + ' ' + y(v).toFixed(1); pen = true; });
    const pe = svg('path', {d: dpath, fill: 'none', stroke: l.ref ? 'var(--ref)' : 'var(--series)', 'stroke-width': 2, 'stroke-dasharray': l.ref ? '5 4' : '', 'stroke-linejoin': 'round'}); s.append(pe);
    if (!l.ref && !calm) { pe.setAttribute('class', 'draw'); pe.style.setProperty('--len', '6000'); } }
  (o.marks || []).forEach((mk, i) => { if (mk.t < t0 || mk.t > t1) return; const X = x(mk.t);
    s.append(svg('line', {x1: X, x2: X, y1: m.t, y2: H - m.b, stroke: mk.check ? 'var(--mute)' : 'var(--mark)', 'stroke-width': 2, 'stroke-dasharray': mk.check ? '2 3' : ''}));
    const flip = X > W - (narrow ? 150 : 190); s.append(svg('text', {x: X + (flip ? -5 : 5), y: m.t + 10 + i * 13, 'text-anchor': flip ? 'end' : 'start', class: 'lbl'}, mk.label)); });
  const cross = svg('line', {y1: m.t, y2: H - m.b, stroke: 'var(--ink2)', 'stroke-width': 1, visibility: 'hidden'}); s.append(cross);
  const dots = lines.map(l => { const c = svg('circle', {r: 4.5, fill: l.ref ? 'var(--ref)' : 'var(--series)', stroke: 'var(--panel)', 'stroke-width': 2, visibility: 'hidden'}); s.append(c); return c; });
  const hit = svg('rect', {x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: 'transparent'});
  hit.addEventListener('mousemove', ev => { const r = s.getBoundingClientRect(), px = (ev.clientX - r.left) / r.width * W, tv = t0 + (px - m.l) / (W - m.l - m.r) * (t1 - t0);
    let i = 0, best = Infinity; t.forEach((q, k) => { const dd = Math.abs(q - tv); if (dd < best) { best = dd; i = k; } });
    cross.setAttribute('x1', x(t[i])); cross.setAttribute('x2', x(t[i])); cross.setAttribute('visibility', 'visible');
    lines.forEach((l, k) => { const v = l.v[i]; if (v == null) dots[k].setAttribute('visibility', 'hidden'); else { dots[k].setAttribute('cx', x(t[i])); dots[k].setAttribute('cy', y(v)); dots[k].setAttribute('visibility', 'visible'); } });
    showTip(ev, '<b>' + esc(lt(t[i])) + '</b><br>' + lines.map(l => esc(l.name) + ': ' + ((l.raw || l.v)[i] == null ? 'missing' : (l.raw || l.v)[i] + ' ' + (o.short || ''))).join('<br>')); });
  hit.addEventListener('mouseleave', () => { cross.setAttribute('visibility', 'hidden'); dots.forEach(c => c.setAttribute('visibility', 'hidden')); hideTip(); });
  s.append(hit);
  const lg = el('div', 'legend');
  for (const l of lines) { const sp = el('span'); sp.append(el('i', l.ref ? 'ref' : ''), document.createTextNode(l.name)); lg.append(sp); }
  if ((o.marks || []).some(mk => !mk.check)) { const sp = el('span'); sp.append(el('i', 'mark'), document.createTextNode('our decision')); lg.append(sp); }
  host.append(lg, s);
}

/* ---------- parts ---------- */
function tags(d) { const w = el('span'), a = el('span', 'tag p-' + d.priority, d.priority), b = el('span', 'tag l-' + level(d), LEVEL[level(d)]); a.title = HINT[d.priority]; b.title = HINT[level(d)]; w.append(a, b); return w; }
function step(d) {
  const s = el('div', 'step'), h = el('div', 'h');
  h.append(el('b', null, d.action.replace(/_/g, ' ')), el('time', null, lt(tsOf(d))), tags(d));
  if (d.resource_id) h.append(el('span', 'tag plain', d.resource_id));
  if (d.confidence != null) h.append(el('span', 'tag plain', 'confidence ' + d.confidence));
  s.append(h, el('p', null, d.reason));
  if (d.proposed_message) { const mm = el('div', 'msg'); mm.append(el('div', 'k', 'Proposed message (' + (d.message_language || '') + '), not sent'), el('div', null, d.proposed_message)); s.append(mm); }
  const add = (k, v) => { if (v) { s.append(el('div', 'k', k)); s.append(el(Array.isArray(v) ? 'pre' : 'div', Array.isArray(v) ? '' : 'v', Array.isArray(v) ? v.join('\n') : v)); } };
  add('Evidence', d.evidence && d.evidence.length ? d.evidence : null);
  add('Expected outcome', d.expected_outcome); add('Verification', d.verification_plan);
  const a = D.actions[d.event_id];
  if (a && !needs(d)) add('Mock executor', a.status.replace(/_/g, ' ') + ' · simulated, no effect was measured');
  if (needs(d)) s.append(controls(d));
  return s;
}
function evidenceCard(e) {
  const c = el('div', 'card'), first = e.start, marks = [{t: first, label: 'decision ' + dhm(first)}];
  if (e.check) marks.push({t: e.check.t, label: 'work order ' + dhm(e.check.t), check: true});
  const S = e.series;
  if (e.kind === 'room_flow') { c.append(el('h2', null, 'Water flow in ' + e.subject), el('p', 'note', 'Litres per 15 minutes from the room meter. A healthy room has long stretches at zero.'));
    const after = S ? S.v.filter((v, i) => v != null && v > 0 && S.t[i] >= first - 5 * 36e5 && S.t[i] <= first) : [];
    const quiet = after.length && after.slice().sort((a, b) => a - b)[Math.floor(after.length / 2)] < 3;
    if (quiet) c.append(el('p', 'note', 'The leak is small (about 1 L per 15 min), so the axis is cut at 6 L: showers go off the top. What matters is that the line never returns to zero.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'flow', v: S && S.v}], unit: 'L per 15 min', short: 'L', zero: true, cap: quiet ? 6 : null, marks, label: 'Water flow'}); }
  else if (e.kind === 'room_meter') { c.append(el('h2', null, 'Meter reading of WM_' + e.subject), el('p', 'note', 'Cumulative litres. A meter can only count up; this one steps backwards, so its consumption is not used.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'meter total', v: S && S.v}], unit: 'litres', short: 'L', marks, label: 'Meter reading'}); }
  else if (e.kind === 'main_gap') { c.append(el('h2', null, 'Night gap: main meter minus all room meters'), el('p', 'note', 'Median of the 15-minute intervals between 01:00 and 05:00, one point per night. Normal is about zero.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'night gap', v: S && S.v}], unit: 'L per 15 min', short: 'L', zero: true, marks, label: 'Night gap'}); }
  else if (e.kind === 'cop') { c.append(el('h2', null, 'Heat pump COP against the outdoor-temperature model'), el('p', 'note', 'Hourly median of heat output divided by electric input. The dashed line is what the outdoor temperature explains.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'measured COP', v: S && S.v}, {name: 'expected from outdoor temperature', v: S && S.ref, ref: true}], unit: 'COP', marks, label: 'COP'}); }
  else if (e.kind === 'ahu') { const dm = e.decisions.map(d => ({t: tsOf(d), label: (d.stage || 'decision') + ' ' + dhm(tsOf(d))})).filter((x, i, a) => a.findIndex(y => y.label === x.label) === i).concat(e.check ? [{t: e.check.t, label: 'work order ' + dhm(e.check.t), check: true}] : []);
    c.append(el('h2', null, 'Filter differential pressure'), el('p', 'note', 'Hourly median. Where the line stops, the sensor sent nothing; a gap is not a recovery. The saw-tooth is the planned reduced operation at night.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'filter pressure', v: S && S.v}], unit: 'Pa', short: 'Pa', marks: dm, label: 'Filter pressure'});
    c.append(el('h2', null, 'Fan power'), el('p', 'note', 'A different sensor, still reporting through the gap. The fan works harder against a loaded filter until it reaches its limit of 5.4 kW.'));
    c.lastChild.previousSibling.style.marginTop = '14px';
    lineChart(c, {t: S && S.t, lines: [{name: 'fan power', v: S && S.fan}], unit: 'kW', short: 'kW', marks: dm, label: 'Fan power'});
    c.append(el('h2', null, 'Airflow'), el('p', 'note', 'Nominal is 4,200 m³/h. Once the fan is at its limit, airflow falls.'));
    c.lastChild.previousSibling.style.marginTop = '14px';
    lineChart(c, {t: S && S.t, lines: [{name: 'airflow', v: S && S.air}], unit: 'm³/h', short: 'm³/h', marks: dm, label: 'Airflow'}); }
  else if (e.kind === 'energy') { c.append(el('h2', null, 'Day-ahead price on ' + e.subject), el('p', 'note', 'EUR per kWh, hourly, as published the day before. The plan charges in the valleys and discharges on the peaks.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'price', v: S && S.v}], unit: 'EUR/kWh', short: 'EUR/kWh', label: 'Price'});
    c.append(el('h2', null, 'Planned battery movement'), el('p', 'note', 'kWh per hour: above zero the battery charges, below zero it discharges. A plan, not a measurement.'));
    c.lastChild.previousSibling.style.marginTop = '14px';
    lineChart(c, {t: S && S.t, lines: [{name: 'charge (+) / discharge (−)', v: S && S.plan}], unit: 'kWh per hour', short: 'kWh', band: [0, 0], label: 'Battery plan'});
    if (e.costs) c.append(el('div', 'check', 'Checked against the dataset, simulated: run against the load and PV that were measured that day, this plan gives ' + e.costs.plan + ' EUR grid cost. The replay, with its own battery control, paid ' + e.costs.replay + ' EUR; without a battery it would have been ' + e.costs.no_battery + ' EUR. The replay does not react to our plan.')); }
  else if (e.kind === 'logistics') { const waste = e.subject.startsWith('WASTE'); if (e.outage) marks.push({t: e.outage.t, label: (waste ? 'container full ' : 'out of stock ') + dhm(e.outage.t), check: true});
    c.append(el('h2', null, waste ? 'Fill level of the central waste container' : 'Stock of the vending machine'), el('p', 'note', waste ? 'Per cent full. It rises in one step per day when the floor bins are emptied and drops at each pickup. The replay does not react to our order.' : 'Units left. It drops with the guests in the house and jumps at each restock. The replay does not react to our order.'));
    lineChart(c, {t: S && S.t, lines: [{name: waste ? 'fill level' : 'stock', v: S && S.v}], unit: waste ? '% full' : 'units', short: waste ? '%' : 'units', zero: true, marks, label: 'Level'});
    c.append(el('div', 'check', e.outage ? 'Checked against the dataset: the replay shows ' + (waste ? 'a full container' : 'an empty machine') + ' ' + Math.round(e.outage.lead_h) + ' h after our order. An extra service needs about 24 h.' : 'Checked against the dataset: no outage followed in the replay, so this extra service would not have been needed.')); }
  else if (e.kind === 'forecast') { c.append(el('h2', null, 'Outdoor temperature forecast used for the decision'), el('p', 'note', 'Solid: the forecast issued at the decision time. Dashed: what was measured afterwards, shown for checking only.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'forecast', v: S && S.v}, {name: 'measured later', v: S && S.ref, ref: true}], unit: '°C outdoor', short: '°C', marks, label: 'Forecast'}); }
  else if (e.kind === 'room_temp') { c.append(el('h2', null, 'Room ' + e.subject + ': temperature and setpoint'), el('p', 'note', 'Shaded band: comfort range for occupied rooms, 20 to 23 °C. The replay does not react to our action.'));
    lineChart(c, {t: S && S.t, lines: [{name: 'room temperature', v: S && S.v}, {name: 'setpoint', v: S && S.ref, ref: true}], unit: '°C', short: '°C', band: [20, 23], marks, label: 'Room temperature'}); }
  else if (e.kind === 'room_day') { c.append(el('h2', null, 'What happened in ' + e.subject + ' that day'), el('p', 'note', 'Grey: events and guest requests from the dataset. Blue: our decisions.'));
    const items = (e.timeline || []).map(x => ({t: x.t, text: x.type.replace(/_/g, ' ') + (x.who ? ' · ' + x.who : '') + (x.text ? ' · “' + x.text + '”' : '')}))
      .concat(e.decisions.map(d => ({t: tsOf(d), ours: true, text: '→ ' + d.action.replace(/_/g, ' ') + ' (' + LEVEL[level(d)] + ')'}))).sort((a, b) => a.t - b.t || (a.ours ? 1 : -1));
    const ul = el('ul', 'log'); for (const it of items) { const li = el('li'); li.append(el('time', null, dhm(it.t)), el('span', it.ours ? 'ours' : '', it.text)); ul.append(li); }
    c.append(ul); }
  else if (e.kind === 'day_plan') { const dd = e.day || {waits: []}; c.append(el('h2', null, 'The day as it went in the replay'), el('p', 'note', 'From the dataset, for checking only. The replay did not follow our plan.'));
    const tl = el('div', 'tiles'); [[dd.checkouts, 'check-outs'], [dd.checkins, 'check-ins'], [dd.cleanings, 'cleanings finished'], [dd.oncall, 'on-call call-outs'], [dd.waits.length, 'guests who waited']].forEach(([v, k]) => { const t = el('div', 'tile'); t.append(el('b', null, v), el('span', null, k)); tl.append(t); });
    c.append(tl);
    if (dd.waits.length) { const mx = Math.max(...dd.waits.map(w => w.min)), bs = el('div', 'bars'); c.append(el('p', 'note', 'Waiting time per guest, arrival at the door to check-in:'));
      for (const w of dd.waits.sort((a, b) => b.min - a.min)) { const b = el('div', 'bar'), bar = el('div'); bar.style.width = Math.max(2, w.min / mx * 100) + '%'; const holder = el('span'); holder.append(bar);
        b.append(el('span', null, w.room), holder, el('span', null, w.min + ' min')); bs.append(b); } c.append(bs); } }
  return c;
}
function episodeTitle(e) { if (e.kind === 'energy') return 'Battery plan · ' + e.subject; if (e.kind === 'day_plan') return (e.scenario === 'S05' ? 'Event weekend, cleaners short' : 'Day capacity shortfall') + ' · ' + e.id.split(':').pop(); if (e.kind === 'logistics') return (e.subject.startsWith('WASTE') ? 'Extra waste pickup' : 'Extra vending restock') + ' · ' + e.subject.replace(':', ' ').replace('_', ' '); if (e.kind === 'ahu') return e.issue_type === 'data_quality' ? 'Filter sensor gap, plant healthy' : 'Ventilation filter cascade'; return (KIND[e.kind] || e.issue_type) + (e.subject && e.subject !== 'BUILDING' && e.kind !== 'cop' && e.kind !== 'main_gap' ? ' · ' + e.subject : ''); }
function detail(e) {
  const box = el('div', 'detail');
  if (!e) { box.append(el('div', 'empty', 'Select a case.')); return box; }
  const head = el('div', 'card hero');
  head.append(el('h3', null, episodeTitle(e)), el('div', 'sub', lt(e.start) + (e.end > e.start ? ' to ' + lt(e.end) : '') + ' · ' + e.decisions.length + ' decision(s) · episode ' + e.id));
  const tg = el('div'); tg.append(el('span', 'tag p-' + e.priority, 'risk: ' + e.priority));
  for (const lv of [...new Set(e.decisions.map(level))]) tg.append(el('span', 'tag l-' + lv, LEVEL[lv]));
  head.append(tg);
  if (e.check) { const ck = el('div', 'check'); ck.append(el('b', null, 'Checked against the dataset: '), document.createTextNode('work order ' + e.check.id + ' was written ' + lt(e.check.t) + ', ' + Math.round(e.check.lead_h) + ' h after our decision: “' + e.check.text + '”. The detector does not read work orders.')); head.append(ck); }
  const cp = el('button', 'copy', 'Copy link to this case'); cp.type = 'button'; cp.onclick = () => { const u = location.href.split('#')[0] + '#' + e.scenario + ':' + encodeURIComponent(e.id); (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => toast('Link copied'), () => toast(u)); }; head.append(cp);
  box.append(head, evidenceCard(e));
  const ch = el('div', 'card'); ch.append(el('h2', null, 'Decisions and actions'), el('p', 'note', 'In order. Autonomous actions run in the mock executor; the others wait for a person, or for a person and the guest.'));
  const chain = el('div', 'chain'); const ORDER = ['flag_anomaly', 'schedule_cleaning', 'dispatch_robot', 'adjust_room_setpoint', 'optimize_energy', 'request_inspection', 'dispatch_technician', 'order_service', 'block_room', 'request_human_approval', 'release_room', 'notify_guest'];
  const rank = d => { const i = ORDER.indexOf(d.action); return i < 0 ? 99 : i; };
  for (const d of e.decisions.slice().sort((a, b) => tsOf(a) - tsOf(b) || rank(a) - rank(b))) chain.append(step(d)); ch.append(chain); box.append(ch);
  return box;
}

/* ---------- views ---------- */
// On a phone a table becomes a stack of cards; each cell then needs its column name in front of it.
function labelCells(table) { const hs = [...table.querySelectorAll('th')].map(h => h.textContent);
  for (const r of table.querySelectorAll('tr')) [...r.children].forEach((c, i) => { if (c.tagName === 'TD') c.dataset.l = hs[i] || ''; }); }
function tile(v, k, small, key, go) { const t = el('div', 'tile' + (key ? ' key' : '') + (go ? ' go' : '')), b = el('b', null, v); t.append(b, el('span', null, k)); if (small) t.append(el('small', null, small));
  const mm = /^(\d+)( h)?$/.exec(String(v)); if (mm) countUp(b, +mm[1], mm[2] || '');
  if (go) { t.tabIndex = 0; t.onclick = () => { tab = go; history.replaceState(null, '', '#' + go); render(); }; t.onkeydown = ev => { if (ev.key === 'Enter') t.onclick(); }; } return t; }
// Where it happened: a schematic 3D building, drawn here from building.json. The dataset gives each room a floor and
// an orientation and no floor plan, so rooms are placed by number: five south rooms in front, five north rooms behind,
// floors pulled apart so every room stays visible. Drag turns it. A case that touches many rooms at once (a cold snap,
// an event weekend) is a building-wide case and is not painted onto single rooms.
let yaw = 0.62, zoom = 1.2, panY = 0, bldLayer = 'cases', bldFit = null, tlFit = null; window.addEventListener('resize', () => { if (bldFit) bldFit(); else if (tlFit) tlFit(); });
// Building and timeline are linked: a room lights up its cases in the timeline, a case lights up its rooms and plant.
let linkAt = {}, linkEp = {};
function lightDots(asset) { const d = document.querySelector('.duo'); if (!d) return; const ids = new Set(((asset && linkAt[asset]) || []).map(e => e.id));
  d.querySelectorAll('circle.dot.lit').forEach(c => c.classList.remove('lit')); d.classList.toggle('linkdots', ids.size > 0);
  if (ids.size) d.querySelectorAll('circle.dot').forEach(c => { if (ids.has(c.dataset.ep)) { c.classList.add('lit'); c.parentNode.append(c); } }); }
function lightRooms(ep) { const d = document.querySelector('.duo'); if (!d) return; const as = new Set((ep && linkEp[ep]) || []);
  d.querySelectorAll('g.bx.lit').forEach(g => g.classList.remove('lit')); d.classList.toggle('linkrooms', as.size > 0);
  if (as.size) d.querySelectorAll('g.bx').forEach(g => { if (as.has(g.dataset.a)) g.classList.add('lit'); }); }
function buildingView(inc) {
  const B = D.building; if (!B || !B.rooms || !B.rooms.length) return null;
  const NOTE = {cases: 'Most serious case per room, with the number of cases.', noise: 'Noise complaints of guests per room over the year.', gaps: 'Hours without a temperature reading per room, and each floor\'s gateway.'};
  const note = el('p', 'note one'), setNote = () => { note.textContent = NOTE[bldLayer] + ' Schematic: the dataset has no floor plan.'; note.title = 'Drag sideways to turn, up or down to move, plus and minus to zoom. In the cases layer a click opens the most serious case of a room. The dataset gives a floor and an orientation per room; the positions are derived from the room numbers.'; }; setNote();
  const card = el('div', 'card'), head = el('div', 'bldhead'); head.append(el('h2', null, 'Where it happened')); card.append(head, note);
  const rank = {critical: 3, high: 2, medium: 1, low: 0}, at = {}, wide = [];
  for (const e of inc) { const as = [...new Set(e.decisions.flatMap(d => d.affected_assets || []).map(a => a.replace(/^WM_(R\d+)$/, '$1')))], rooms = as.filter(a => /^R\d{3}$/.test(a));
    if (rooms.length > 6) wide.push(e);
    for (const a of as) { if (/^R\d{3}$/.test(a) && rooms.length > 6) continue; (at[a] = at[a] || []).push(e); } }
  for (const k in at) at[k].sort((a, b) => rank[b.priority] - rank[a.priority] || b.start - a.start);
  linkAt = at; linkEp = {}; for (const k in at) for (const e of at[k]) (linkEp[e.id] = linkEp[e.id] || []).push(k);
  const FH = 0.5, GAP = 1.2, boxes = [], nF = B.floors || Math.max(...B.rooms.map(r => r.floor));
  const perFloor = {}; for (const r of B.rooms) (perFloor[r.floor + r.o] = perFloor[r.floor + r.o] || []).push(r);
  for (const key in perFloor) perFloor[key].sort((a, b) => a.id.localeCompare(b.id)).forEach((r, i) => { const north = r.o === 'N', z = (r.floor - 1) * GAP;
    boxes.push({id: r.id, label: r.id + ' · floor ' + r.floor + ', faces ' + (north ? 'north' : 'south'), x0: i, x1: i + 0.94, y0: north ? -1.45 : 0.25, y1: north ? -0.25 : 1.45, z0: z, z1: z + FH, room: true}); });
  for (const g of (B.gateways || [])) if (g.floor) boxes.push({id: g.id, label: g.id, gw: g, name: g.id, x0: 5.12, x1: 5.62, y0: -0.25, y1: 0.25, z0: (g.floor - 1) * GAP, z1: (g.floor - 1) * GAP + 0.5});
  const W = 5, roof = nF * GAP, top = roof + 0.5, plant = (id, label, x0, y0, w, d, z0, h) => boxes.push({id, label, x0, x1: x0 + w, y0, y1: y0 + d, z0, z1: z0 + h, name: id});
  const has = id => B.assets.includes(id) || at[id];
  if (has('HP1')) plant('HP1', 'HP1 · heat pump', -1.9, 0.3, 0.9, 0.9, 0, 0.7);
  if (has('BAT1')) plant('BAT1', 'BAT1 · battery', -1.9, -1.2, 0.9, 0.9, 0, 0.55);
  if (has('WM_MAIN')) plant('WM_MAIN', 'WM_MAIN · main water meter', -0.75, -0.2, 0.45, 0.45, 0, 0.3);
  if (has('VEND1')) plant('VEND1', 'VEND1 · vending machine, lobby', W + 0.35, 0.7, 0.55, 0.55, 0, 0.75);
  if (has('WASTE_MAIN')) plant('WASTE_MAIN', 'WASTE_MAIN · central waste container', W + 0.35, -1.2, 0.9, 0.9, 0, 0.5);
  if (has('AHU1')) plant('AHU1', 'AHU1 · air handling unit, roof', 0.3, -1.1, 1.5, 0.9, roof, 0.45);
  if (has('PV1')) plant('PV1', 'PV1 · photovoltaics, roof', 2.3, -1.2, 2.5, 2.4, roof, 0.08);
  const VW = 800, VH = 450, S = 62, cx0 = W / 2, s = svg('svg', {viewBox: `0 0 ${VW} ${VH}`, class: 'bld', role: 'img', 'aria-label': 'Schematic 3D view of the building with the number of cases per room and asset'});
  // Three layers over the same building: the cases, the noise complaints, and the hours a room sent no reading.
  const NOISE = B.noise || {}, GAPS = B.gaps_h || {}, GW = B.gateways || [], maxOf = o => Math.max(1, ...Object.values(o));
  const LAYER = {cases: {name: 'Cases'}, noise: {name: 'Noise complaints', data: NOISE, max: maxOf(NOISE), unit: n => n + ' noise complaint' + (n === 1 ? '' : 's')},
    gaps: {name: 'Data gaps', data: GAPS, max: Math.max(maxOf(GAPS), ...GW.map(g => g.hours)), unit: n => n + ' h without a temperature reading'}};
  const val = b => bldLayer === 'cases' ? (at[b.id] || []).length : b.gw ? b.gw.hours : (LAYER[bldLayer].data[b.id] || 0);
  const colour = b => { if (bldLayer !== 'cases') { const v = val(b), L = LAYER[bldLayer]; if (!v || (!b.room && !b.gw)) return ['var(--raise)', b.room || b.gw ? 0.9 : 0.35];
      const t = v / (b.gw ? Math.max(...GW.map(g => g.hours), 1) : maxOf(L.data));        // 0..1 within the layer: dim for few, vivid for many
      return ['color-mix(in oklab, var(--hot) ' + Math.round(12 + 88 * Math.pow(t, 1.25)) + '%, var(--cool))', 0.96, t]; }
    const l = at[b.id]; if (!l) return ['var(--raise)', 0.9]; const p = l[0].priority; return [p === 'critical' ? 'var(--crit)' : p === 'high' ? 'var(--appr)' : 'var(--series)', Math.min(0.95, 0.55 + 0.1 * l.length)]; };
  const tipFor = b => { if (bldLayer !== 'cases') { if (b.gw) return '<b>' + b.gw.id + ' · sensor gateway, floor ' + b.gw.floor + '</b><br>' + b.gw.hours + ' room-hours without a temperature reading<br>' + b.gw.alarms + ' communication-loss alarms of the building system';
      if (!b.room) return '<b>' + b.label + '</b><br>not part of this layer'; const v = val(b); return '<b>' + b.label + '</b><br>' + (v ? LAYER[bldLayer].unit(v) : bldLayer === 'noise' ? 'no noise complaint' : 'no gap'); }
    const l = at[b.id] || []; return '<b>' + b.label + '</b><br>' + (l.length ? l.length + ' case' + (l.length > 1 ? 's' : '') + '<br>' + l.slice(0, 4).map(e => lt(e.start).slice(0, 10) + ' · ' + episodeTitle(e) + ' · ' + e.priority).join('<br>') + (l.length > 4 ? '<br>and ' + (l.length - 4) + ' more' : '') : 'no case of its own'); };
  function draw() { s.replaceChildren(); const c = Math.cos(yaw), sn = Math.sin(yaw);
    const shown = s.getBoundingClientRect(), k = shown.height ? Math.min(shown.height / VH, shown.width / VW) : 1, fs = 13 / k;   // floor names keep 13 px on screen, whatever the view's size
    const P = (x, y, z) => { const xr = (x - cx0) * c - y * sn, yr = (x - cx0) * sn + y * c; return [VW / 2 + 72 + xr * S * zoom, VH * 0.5 + panY + (yr * S * 0.4 - (z - top / 2) * S * 0.86) * zoom, yr]; };
    const pts = a => a.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
    for (let f = 0; f <= nF; f++) { const z = f * GAP - 0.03, q = [P(-0.1, -1.55, z), P(W + 0.04, -1.55, z), P(W + 0.04, 1.55, z), P(-0.1, 1.55, z)];           // floor slab
      const slab = svg('polygon', {points: pts(q), fill: 'var(--bg)', 'fill-opacity': 0.55, stroke: 'var(--line)', 'stroke-width': 1}); slab.dataset.o = f * 1000 - 500; s.append(slab); }
    const order = boxes.map(b => ({b, k: Math.round(b.z0 / GAP) * 1000 + P((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2, 0)[2] * 10})).sort((a, b2) => a.k - b2.k);
    const slabs = [...s.children]; s.replaceChildren();
    let si = 0; const flush = k => { while (si < slabs.length && +slabs[si].dataset.o <= k) s.append(slabs[si++]); };
    for (const {b, k} of order) { flush(k); if (b.gw && bldLayer !== 'gaps') continue; const [fill, op, heat] = colour(b), g = svg('g', {class: 'bx' + (bldLayer === 'cases' && at[b.id] ? ' hit' : '')});
      const sides = [[1, 0, [[b.x1, b.y0], [b.x1, b.y1]]], [-1, 0, [[b.x0, b.y1], [b.x0, b.y0]]], [0, 1, [[b.x1, b.y1], [b.x0, b.y1]]], [0, -1, [[b.x0, b.y0], [b.x1, b.y0]]]];
      for (const [nx, ny, [[xa, ya], [xb, yb]]] of sides) { const facing = nx * sn + ny * c; if (facing <= 0.02) continue;
        g.append(svg('polygon', {points: pts([P(xa, ya, b.z0), P(xb, yb, b.z0), P(xb, yb, b.z1), P(xa, ya, b.z1)]), fill, 'fill-opacity': op * (nx ? 0.42 : 0.6), stroke: 'var(--line)', 'stroke-width': 0.8, 'stroke-linejoin': 'round'})); }
      const tp = [P(b.x0, b.y0, b.z1), P(b.x1, b.y0, b.z1), P(b.x1, b.y1, b.z1), P(b.x0, b.y1, b.z1)];
      g.append(svg('polygon', {points: pts(tp), fill, 'fill-opacity': op, stroke: 'var(--line)', 'stroke-width': 0.8, 'stroke-linejoin': 'round'}));
      const mx = (tp[0][0] + tp[2][0]) / 2, my = (tp[0][1] + tp[2][1]) / 2, n = b.room || b.gw || bldLayer === 'cases' ? Math.round(val(b)) : 0;
      if (n) g.append(svg('text', {x: mx, y: my + 4, 'text-anchor': 'middle', class: 'bn' + (heat != null && heat < 0.45 ? ' lo' : '')}, n));
      if (b.name) g.append(svg('text', {x: mx, y: my - (n ? 12 : -4), 'text-anchor': 'middle', class: 'bl'}, b.name));
      g.dataset.a = b.id; g.addEventListener('mouseenter', () => lightDots(b.id)); g.addEventListener('mouseleave', () => lightDots(null));
      g.addEventListener('mousemove', ev => showTip(ev, tipFor(b))); g.addEventListener('mouseleave', hideTip);
      if (n && bldLayer === 'cases') g.addEventListener('click', () => { if (!moved) { hideTip(); open(at[b.id][0]); } });
      s.append(g); }
    flush(1e9);
    for (let f = 0; f <= nF; f++) { const p = P(cx0, 0, f * GAP + FH / 2); s.append(svg('text', {x: 14, y: p[1] + fs * 0.35, class: 'bf', style: 'font-size:' + fs.toFixed(1) + 'px'}, f < nF ? 'Floor ' + (f + 1) : 'Roof')); } }
  let dragX = null, dragY = null, moved = false;
  s.addEventListener('pointerdown', ev => { dragX = ev.clientX; dragY = ev.clientY; moved = false; lightDots(null); });
  window.addEventListener('pointerup', () => { dragX = null; setTimeout(() => { moved = false; }, 0); });
  s.addEventListener('pointermove', ev => { if (dragX == null || !s.isConnected) return; const dx = ev.clientX - dragX, dy = ev.clientY - dragY; if (Math.abs(dx) < 3 && Math.abs(dy) < 3 && !moved) return; moved = true; hideTip(); yaw += dx * 0.008;
    if (ev.pointerType === 'mouse') { const k = VH / s.getBoundingClientRect().height, lim = VH * 0.5 * zoom; panY = Math.max(-lim, Math.min(lim, panY + dy * k)); }   // touch keeps scrolling the page
    dragX = ev.clientX; dragY = ev.clientY; draw(); });
  draw(); const wrap = el('div', 'bldwrap'), ctl = el('div', 'bldzoom');
  for (const [sym, f, name] of [['+', 1.2, 'Zoom in'], ['−', 1 / 1.2, 'Zoom out']]) { const b = el('button', null, sym); b.type = 'button'; b.title = name; b.setAttribute('aria-label', name);
    b.onclick = () => { zoom = Math.min(2.4, Math.max(0.6, zoom * f)); if (zoom <= 1) panY = 0; draw(); }; ctl.append(b); }
  wrap.append(s); card.append(wrap);
  const lg = el('div', 'legend big'), sw = (c, t) => '<span><i class="sw" style="background:' + c + '"></i>' + t + '</span>';
  const legend = () => { if (bldLayer === 'cases') { lg.innerHTML = sw('var(--crit)', 'critical case') + sw('var(--appr)', 'high') + sw('var(--series)', 'medium or low') + '<span><i class="sw" style="background:var(--raise);border:1px solid var(--line)"></i>no case of its own</span>';
      if (wide.length) { const w = el('span', 'wide', '+ ' + wide.length + ' building-wide'); w.title = wide.length + ' cases concern many rooms at once (cold snaps, event weekends, building-wide energy plans). They are counted for the building as a whole and are not shown per room.'; lg.append(w); } }
    else { const tot = bldLayer === 'noise' ? Object.values(NOISE).reduce((a, b) => a + b, 0) + ' noise complaints in the year' : Math.round(Object.values(GAPS).reduce((a, b) => a + b, 0)) + ' room-hours without a reading; end box: gateway';
      lg.innerHTML = '<span><i class="sw" style="background:var(--hot)"></i>many</span><span><i class="sw" style="background:color-mix(in oklab, var(--hot) 22%, var(--cool))"></i>few</span><span><i class="sw" style="background:var(--raise);border:1px solid var(--line)"></i>none</span>';
      const w = el('span', 'wide', tot); w.title = bldLayer === 'noise' ? 'Guest requests of the type noise complaint, counted per room' : 'Quarter hours in which a room sent no temperature, summed per room; the building system raised its own communication-loss alarms, shown on the gateway'; lg.append(w); } };
  const seg = el('div', 'seg'); for (const k of Object.keys(LAYER)) { if (k !== 'cases' && !Object.keys(LAYER[k].data).length) continue; const b = el('button', k === bldLayer ? 'on' : '', LAYER[k].name); b.type = 'button';
    b.onclick = () => { bldLayer = k; for (const x of seg.children) x.className = x === b ? 'on' : ''; setNote(); legend(); bldFit ? bldFit() : draw(); }; seg.append(b); }
  const ctlRow = el('div', 'bldctl'); if (seg.children.length > 1) ctlRow.append(seg); ctlRow.append(ctl); head.append(ctlRow);
  legend(); card.append(lg);
  // On a wide screen the view takes exactly the height that is left, so building and key figures are visible without scrolling.
  bldFit = () => { if (!s.isConnected) return; if (innerWidth <= 1100) { s.style.height = ''; draw(); return; }
    const tl = document.querySelector('.duo .tlstrip'); if (tl) tl.style.display = 'none';             // the neighbour must not stretch this box while it is measured
    s.style.height = '300px'; const r = s.getBoundingClientRect(), below = card.getBoundingClientRect().bottom - r.bottom;
    s.style.height = Math.round(Math.max(190, Math.min(640, innerHeight - (r.top + scrollY) - below - 16))) + 'px'; draw(); if (tl) tl.style.display = ''; if (tlFit) tlFit(); };
  requestAnimationFrame(bldFit); if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => bldFit && bldFit());
  return card; }
/* ---------- planning views: budget and staff. Summaries of the year, no decisions. ---------- */
const eur = v => Math.round(v).toLocaleString('en-US') + ' EUR', kwh = v => Math.round(v).toLocaleString('en-US') + ' kWh';
const PART = {heat_pump: ['Heat pump (heating and hot water)', 'var(--series)'], fans: ['Ventilation fans', 'var(--c2)'], rest: ['Rest of the building (rooms, lighting, lobby, robots)', 'var(--c3)']};
function simpleTable(head, rows) { const sc = el('div', 'scroll'), t = el('table'), hr = el('tr'); head.forEach(h => hr.append(el('th', null, h))); t.append(hr);
  for (const r of rows) { const tr = el('tr'); r.forEach((c, i) => { const td = el('td', typeof c === 'string' && /^[\d.,–-]+ ?(EUR|kWh|%|m³|h|min)?$/.test(c) && i ? 'n' : null); if (c instanceof Node) td.append(c); else td.textContent = c == null ? '' : c; tr.append(td); }); t.append(tr); }
  labelCells(t); sc.append(t); return sc; }
function budgetView(root) { const B = D.budget, tl = el('div', 'tiles'), hp = B.parts.find(p => p.key === 'heat_pump');
  tl.append(tile(eur(B.bill.eur), 'electricity bought from the grid', 'the year at the hourly tariff; the only cost the dataset prices', true),
    tile(eur(B.load.eur), 'what the consumption is worth', kwh(B.load.kwh) + ' at the hourly tariff'),
    tile(eur(B.pv.eur), 'covered by the solar panels', kwh(B.pv.kwh) + ' produced, valued at the tariff of the hour'),
    tile(Math.round(hp.eur / B.load.eur * 100) + ' %', 'of the cost is the heat pump', 'the largest single part')); root.append(tl);
  const c1 = el('div', 'card'); c1.append(el('h2', null, 'Where the electricity money goes'), el('p', 'note', 'Each quarter hour of consumption is priced with the tariff of its hour. The dataset meters the heat pump and the ventilation fans separately; the rest is what remains of the building load. Rooms have no electricity meter of their own, so no cost per room is shown.'));
  const bar = el('div', 'split-bar'); for (const p of B.parts) { const seg = el('div'); seg.style.background = PART[p.key][1]; seg.style.width = p.eur / B.load.eur * 100 + '%';
    seg.addEventListener('mousemove', ev => showTip(ev, '<b>' + PART[p.key][0] + '</b><br>' + eur(p.eur) + ' · ' + kwh(p.kwh))); seg.addEventListener('mouseleave', hideTip); bar.append(seg); } c1.append(bar);
  c1.append(simpleTable(['Part of the building', 'Electricity', 'Cost at tariff', 'Share'], B.parts.map(p => { const n = el('span'); const sw = el('i', 'sw'); sw.style.background = PART[p.key][1]; n.className = 'legend'; n.style.margin = '0'; n.append(sw, PART[p.key][0]); return [n, kwh(p.kwh), eur(p.eur), Math.round(p.eur / B.load.eur * 100) + ' %']; })));
  c1.append(el('p', 'note', 'Assumption: the fan power is part of the metered building load. The dataset does not state this.')); root.append(c1);
  const c2 = el('div', 'card'); c2.append(el('h2', null, 'Cost by month'), el('p', 'note', 'Consumption valued at the tariff, by part. Winter is the heat pump; the fans and the rest hardly change over the year.'));
  const M = B.months.filter(x => (x.heat_pump || 0) + (x.fans || 0) + (x.rest || 0) > 50), W = 1000, H = 250, m = {l: 54, r: 8, t: 10, b: 26}, mx = Math.max(...M.map(x => (x.heat_pump || 0) + (x.fans || 0) + (x.rest || 0))), s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Electricity cost per month by part of the building'});
  const y = v => m.t + (H - m.t - m.b) * (1 - v / mx), bw = (W - m.l - m.r) / M.length;
  for (const g of [0, 0.25, 0.5, 0.75, 1]) { const v = mx * g; s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'var(--grid)'}), svg('text', {x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'ax'}, Math.round(v / 100) * 100)); }
  M.forEach((x, i) => { let acc = 0; const g = svg('g'); for (const k of ['rest', 'fans', 'heat_pump']) { const v = x[k] || 0, x0 = m.l + i * bw + bw * 0.16;
      g.append(svg('rect', {x: x0, width: bw * 0.68, y: y(acc + v), height: Math.max(0, y(acc) - y(acc + v) - 2), rx: 3, fill: PART[k][1]})); acc += v; }
    g.addEventListener('mousemove', ev => showTip(ev, '<b>' + x.month + '</b><br>' + ['heat_pump', 'fans', 'rest'].map(k => PART[k][0].split(' (')[0] + ': ' + eur(x[k] || 0)).join('<br>') + '<br>bought from the grid: ' + eur(x.bill || 0))); g.addEventListener('mouseleave', hideTip);
    s.append(g, svg('text', {x: m.l + i * bw + bw / 2, y: H - 8, 'text-anchor': 'middle', class: 'ax'}, x.month.slice(5))); });
  s.append(svg('text', {x: m.l, y: m.t + 2, class: 'ax'}, 'EUR')); c2.append(s);
  const lg = el('div', 'legend'); for (const k of ['heat_pump', 'fans', 'rest']) { const sp = el('span'), sw = el('i', 'sw'); sw.style.background = PART[k][1]; sp.append(sw, PART[k][0]); lg.append(sp); } c2.append(lg); root.append(c2);
  const c3 = el('div', 'card'); c3.append(el('h2', null, 'Where the potential is'), el('p', 'note', 'Sizes from the replayed year. They are estimates of what a lever is worth, not measured savings: the replay does not react to our decisions.'));
  const days = E.filter(e => e.costs), sum = k => days.reduce((a, e) => a + e.costs[k], 0), fans = B.parts.find(p => p.key === 'fans'), rows = [];
  if (days.length) rows.push(['Battery schedule', eur(sum('replay') - sum('plan')), 'Our day-ahead plan against what the battery did in the replay, summed over the ' + days.length + ' days for which a plan was issued. Without a battery those days would have cost ' + eur(sum('no_battery')) + '.', 'simulated']);
  rows.push(['Solar power given away', eur(B.export.eur), kwh(B.export.kwh) + ' were exported without payment. Used on site at that hour, they would have been worth this much: an upper bound.', 'estimate']);
  rows.push(['Heat pump efficiency', eur(hp.eur / 100) + ' per 1 %', 'The heat pump costs ' + eur(hp.eur) + ' a year. The two faults found in S03 each cost about 15 % efficiency while they lasted.', 'arithmetic']);
  rows.push(['Ventilation run time', eur(fans.eur / 100) + ' per 1 %', 'The fans cost ' + eur(fans.eur) + ' a year and run almost evenly through all months; a loaded filter (S04) raises fan power.', 'arithmetic']);
  c3.append(simpleTable(['Lever', 'Size per year', 'Basis', 'Kind of figure'], rows)); root.append(c3);
  const c4 = el('div', 'card'); c4.append(el('h2', null, 'What the dataset does not price'), el('p', 'note', 'There is no water price, no wage and no cost on a work order in the dataset. These parts of a budget are shown as volumes and counts. A live system would take the prices from the accounts.'));
  if (B.water) c4.append(el('h3', null, 'Water, ' + B.water.total_m3.toLocaleString('en-US') + ' m³ in the year'), simpleTable(['Where', 'Volume'], [...B.water.floors.map(f => ['Rooms on floor ' + f.floor, f.m3.toLocaleString('en-US') + ' m³']), ['Outside the rooms (common areas, plant, losses)', B.water.outside_rooms_m3.toLocaleString('en-US') + ' m³']]));
  if (B.work_orders) { const by = {}; for (const w of B.work_orders) { (by[w.where] = by[w.where] || {})[w.type] = w.n; }
    c4.append(el('h3', null, 'Maintenance work orders'), simpleTable(['Where', 'Corrective', 'Preventive', 'Metering'], Object.entries(by).map(([k, v]) => [k === 'BUILDING' ? 'Building in general' : k, String(v.corrective || 0), String(v.preventive || 0), String(v.metering || 0)]))); }
  root.append(c4); }
const SERVICE = {EXTERNAL_PLUMBER: 'Plumbing contractor', EXTERNAL_HVAC: 'Heating and ventilation contractor', EXTERNAL_METERING: 'Metering service', VENDOR_EXT: 'Vending supplier', MUNICIPAL_SERVICE: 'Municipal waste service',
  housekeeping: 'Housekeeping team as a whole', cleaner: 'Cleaner', robot: 'Floor-cleaning robot', technician: 'In-house technician', on_call_housekeeping: 'On-call housekeeper, evenings'};
function staffView(root) { const S = D.staff, R = S.resources, inn = R.filter(r => r.internal), ext = R.filter(r => !r.internal), tech = R.find(r => r.role === 'technician');
  const absent = r => Object.values(r.absent).reduce((a, b) => a + b, 0), cl = inn.filter(r => r.role === 'cleaner');
  const oncall = all.filter(d => (d.affected_assets || []).includes('ONCALL_1')).length, tl = el('div', 'tiles');
  tl.append(tile(inn.length, 'internal people, robots and teams', 'cleaners, robots, technician, on-call', true), tile(ext.length, 'external partners', 'contractors, supplier, municipal service'),
    tile(cl.reduce((a, r) => a + absent(r), 0), 'cleaner shifts lost to sickness', 'all known less than a day ahead'),
    tile(tech && tech.timed ? tech.on_time + ' of ' + tech.timed : 'n/a', 'technician jobs on schedule', 'finished within ' + S.on_time_h + ' h of the planned slot')); root.append(tl);
  const none = () => { const s = el('span', null, 'not in the dataset'); s.style.color = 'var(--mute)'; s.title = 'The dataset has resource ids only, no names and no contact details. A live system takes them from the roster and the contractor list.'; return s; };
  const abs = r => Object.entries(r.absent).map(([k, v]) => v + ' ' + k.replace(/_/g, ' ')).join(', ') || 'none';
  const work = r => Object.entries(r.work).map(([k, v]) => v.toLocaleString('en-US') + ' ' + k).join(', ') || (r.orders ? r.orders + ' work orders' : r.id === 'ONCALL_1' ? oncall + ' call-outs proposed by the system' : 'none recorded');
  const quality = r => r.timed ? r.on_time + ' of ' + r.timed + ' on schedule · ' + r.median_h + ' h median from order to done' + (r.postponed ? ' · ' + r.postponed + ' postponed' : '')
    : r.id === 'VENDOR_EXT' ? r.misses + ' times out of stock between ' + (r.work.restocks || 0) + ' restocks' : r.id === 'MUNICIPAL_SERVICE' ? r.misses + ' full-container events between ' + (r.work.pickups || 0) + ' pickups'
    : r.median_min != null ? r.median_min + ' min median per ' + (r.role === 'robot' ? 'floor run' : 'room') : 'no measure in the dataset';
  const c1 = el('div', 'card'); c1.append(el('h2', null, 'Internal'), el('p', 'note', 'From the roster and the event log of the year. Shifts are those that took place; an absence counts per shift.'));
  c1.append(simpleTable(['Resource', 'Role', 'Contact', 'Shifts worked', 'Absent', 'Work done', 'Service quality'], inn.map(r => [r.id, SERVICE[r.role] || SERVICE[r.id] || r.role, none(), r.shifts ? String(r.shifts) : '', abs(r), work(r), quality(r)]))); root.append(c1);
  const c2 = el('div', 'card'); c2.append(el('h2', null, 'External partners'), el('p', 'note', 'From the work orders and the event log. On schedule means finished within ' + S.on_time_h + ' hours of the planned slot.'));
  c2.append(simpleTable(['Partner', 'Service', 'Contact', 'Jobs', 'Service quality'], ext.map(r => [r.id, SERVICE[r.id] || 'External service', none(), work(r), quality(r)]))); root.append(c2);
  const c3 = el('div', 'card'); c3.append(el('h2', null, 'Absences by month'), el('p', 'note', 'Shifts that did not take place, by role. An event weekend with a sick cleaner is scenario S05.'));
  const M = S.absent_months, keys = ['cleaner', 'robot', 'technician'], col = {cleaner: 'var(--series)', robot: 'var(--c2)', technician: 'var(--c3)'}, W = 1000, H = 190, m = {l: 34, r: 8, t: 10, b: 26};
  const mx = Math.max(1, ...M.map(x => keys.reduce((a, k) => a + (x[k] || 0), 0))), s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Absent shifts per month by role'}), y = v => m.t + (H - m.t - m.b) * (1 - v / mx), bw = (W - m.l - m.r) / Math.max(1, M.length);
  for (let v = 0; v <= mx; v += Math.max(1, Math.ceil(mx / 4))) s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: 'var(--grid)'}), svg('text', {x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'ax'}, v));
  M.forEach((x, i) => { let acc = 0; const g = svg('g'); for (const k of keys) { const v = x[k] || 0; if (!v) continue; g.append(svg('rect', {x: m.l + i * bw + bw * 0.2, width: bw * 0.6, y: y(acc + v), height: Math.max(0, y(acc) - y(acc + v) - 2), rx: 3, fill: col[k]})); acc += v; }
    g.addEventListener('mousemove', ev => showTip(ev, '<b>' + x.month + '</b><br>' + keys.map(k => k + ': ' + (x[k] || 0) + ' shifts').join('<br>'))); g.addEventListener('mouseleave', hideTip);
    s.append(g, svg('text', {x: m.l + i * bw + bw / 2, y: H - 8, 'text-anchor': 'middle', class: 'ax'}, x.month.slice(5))); });
  c3.append(s); const lg = el('div', 'legend'); for (const k of keys) { const sp = el('span'), sw = el('i', 'sw'); sw.style.background = col[k]; sp.append(sw, k); lg.append(sp); } c3.append(lg); root.append(c3);
  root.append(el('p', 'note', 'Names and contact details are not part of the dataset, and none are invented here. Service quality uses only what the dataset records: planned and actual times of work orders, durations of cleanings, and stock-outs between deliveries.')); }
let whoDraw = null; window.addEventListener('resize', () => whoDraw && whoDraw());
function overview(root) {
  const inc = E.filter(e => !e.routine), by = s => inc.filter(e => e.scenario === s).length;
  const checked = E.filter(e => e.check), leads = checked.map(e => Math.round(e.check.lead_h)).sort((a, b) => a - b);
  const tech = E.filter(q => ['room_flow', 'main_gap', 'cop'].includes(q.kind) || (q.kind === 'ahu' && q.issue_type !== 'data_quality'));
  const tl = el('div', 'tiles');
  const wait = pending(), needConsent = wait.filter(d => level(d) === 'approval_and_consent').length;
  const kt = (v, k, small, hint, key, go) => { const t = tile(v, k, small, key, go); t.title = hint; return t; };     // short on the box, the full sentence on hover
  tl.append(kt(leads.length ? Math.round(leads[Math.floor(leads.length / 2)]) + ' h' : 'n/a', 'median head start', 'first decision to repair order', 'Median time from our first decision to the repair order in the dataset, over the technical incidents', true),
    kt(leads.length ? leads[0] + '–' + leads[leads.length - 1] + ' h' : 'n/a', 'shortest to longest', 'burst pipe to slow leak', 'A burst pipe shows within hours; a slow leak or a clogging filter shows days ahead'),
    kt(checked.length + ' of ' + tech.length, 'incidents confirmed', 'by a later work order', 'Technical incidents for which the dataset holds a later corrective work order. Work orders are used for checking only; no detector reads them'),
    kt(inc.filter(e => e.priority === 'critical').length, 'critical cases', 'red in building and timeline', 'Cases whose highest priority is critical'),
    kt(wait.length, 'waiting for a person', needConsent + ' also need guest consent', 'Decisions that wait for approval. Click to open the approvals', false, 'queue'),
    kt(E.length - inc.length, 'routine guest answers', 'not counted as incidents', 'Routine answers to guests. Tick the box in S01 or S03 to see them'));
  const kf = el('div', 'card'); kf.append(el('h2', null, 'Key figures'), el('p', 'note', 'Head start, how it was checked, what waits, what is counted. Hover a box for details.'), tl);
  const bld = buildingView(inc), duo = bld ? el('div', 'duo') : null;   // first row: where it happened (the building) beside when it happened (the timeline)
  if (duo) { bld.style.marginTop = '0'; duo.append(bld); root.append(duo); }
  root.append(kf);
  const na = all.filter(d => level(d) === 'autonomous').length, nh = all.filter(d => level(d) === 'human_approval').length, nc = all.length - na - nh;
  const sb = el('div', 'card'); sb.append(el('h2', null, 'Who decides'), el('p', 'note', 'Share of all decisions by autonomy level. The gate is code: a detector can ask for more oversight, never for less.'));
  const bar = el('div', 'split-bar'); [[na, 'var(--auto)', 'autonomous'], [nh, 'var(--appr)', 'human approval'], [nc, 'var(--cons)', 'approval + guest consent']].forEach(([n, col, name]) => { const seg = el('div'); seg.style.background = col; seg.style.width = Math.max(n ? 0.8 : 0, n / all.length * 100) + '%';
    seg.addEventListener('mousemove', ev => showTip(ev, '<b>' + name + '</b><br>' + n + ' of ' + all.length + ' decisions (' + (n / all.length * 100).toFixed(1) + ' %)')); seg.addEventListener('mouseleave', hideTip); bar.append(seg); });
  const lgd = el('div', 'legend'); [[na, 'l-autonomous', 'autonomous'], [nh, 'l-human_approval', 'human approval'], [nc, 'l-approval_and_consent', 'approval + guest consent']].forEach(([n, cls, name]) => { const sp = el('span', 'tag ' + cls, name + ' · ' + n); sp.title = HINT[cls.slice(2)]; lgd.append(sp); });
  // Thin connectors tie each label to its part of the bar: the two small parts sit far right, so their labels move under them.
  const link = svg('svg', {class: 'who-link', height: 22, 'aria-hidden': 'true'}); lgd.classList.add('who');
  sb.append(bar, link, lgd); root.append(sb);
  whoDraw = () => { if (!lgd.isConnected) return; const tags = [...lgd.children], segs = [...bar.children], box = sb.getBoundingClientRect(), W = bar.getBoundingClientRect().width;
    const oneRow = tags.every(t => Math.abs(t.offsetTop - tags[0].offsetTop) < 4); link.style.display = oneRow ? 'block' : 'none'; if (!oneRow) return;
    link.setAttribute('width', W); link.setAttribute('viewBox', `0 0 ${W} 22`); link.replaceChildren(); const x0 = bar.getBoundingClientRect().left;
    tags.forEach((t, i) => { const tr = t.getBoundingClientRect(), sr = segs[i].getBoundingClientRect(); if (!sr.width) return;
      const tx = tr.left + tr.width / 2 - x0, sx = tx > sr.left - x0 + 2 && tx < sr.right - x0 - 2 ? tx : (sr.left + sr.right) / 2 - x0, mid = 6 + i * 5;      // staggered so the lines never share a path
      link.append(svg('path', {d: `M${sx.toFixed(1)} 0V${mid}H${tx.toFixed(1)}V22`, fill: 'none', stroke: segs[i].style.background, 'stroke-width': 1.5, 'stroke-opacity': 0.8, 'stroke-linejoin': 'round'})); }); };
  requestAnimationFrame(whoDraw); if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => whoDraw && whoDraw());
  // time strip
  const c = el('div', 'card'); c.append(el('h2', null, 'When the cases happened'), el('p', 'note', 'One dot per case, one lane per scenario; red is critical. Curves: how many cases fall around that time.'));
  const strip = fill => {
  const narrow = window.innerWidth < 700, half = !!duo && window.innerWidth > 1100, W = narrow ? Math.max(300, window.innerWidth - 74) : half ? 660 : 1000, lanes = ['S01', 'S02', 'S03', 'S04', 'S05', 'ENG', 'LOG'];
  const m0 = {b: 26}, gap = fill ? Math.max(30, Math.min(84, (fill - 20 - m0.b) / (lanes.length - 1 + 0.72))) : narrow ? 68 : half ? 34 : 64, rise = fill || half ? gap * 0.72 : narrow ? 36 : 44, m = {l: 6, r: narrow ? 8 : 10, t: rise + 6, b: m0.b}, H = m.t + (lanes.length - 1) * gap + 14 + m.b;
  const t0 = Math.min(...E.map(e => e.start)), t1 = Math.max(...E.map(e => e.start), t0 + 1);
  const x = v => m.l + (v - t0) / (t1 - t0) * (W - m.l - m.r), s = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', class: 'tlstrip', 'aria-label': 'Cases over time'});
  // Density curve behind each lane: how many cases happen around that time. A Gaussian window of about
  // ten days, the same height scale for all lanes, so a taller curve means more cases.
  const DAY = 864e5, BW = 10 * DAY, N = 140, grid = Array.from({length: N}, (_, i) => t0 + (t1 - t0) * i / (N - 1));
  const dens = lanes.map(ln => { const ts = inc.filter(q => q.scenario === ln).map(q => q.start); return grid.map(g => ts.reduce((a, t) => a + Math.exp(-0.5 * Math.pow((g - t) / BW, 2)), 0)); });
  const densCrit = lanes.map(ln => { const ts = inc.filter(q => q.scenario === ln && q.priority === 'critical').map(q => q.start); return grid.map(g => ts.reduce((a, t) => a + Math.exp(-0.5 * Math.pow((g - t) / BW, 2)), 0)); });
  const peak = Math.max(1e-9, ...dens.flat());
  const lanesLabels = [], laneName = ln => SC[ln].replace(/^S(\d\d)/, 'S-$1');
  lanes.forEach((ln, i) => { const y = m.t + i * gap, d = dens[i], cases = inc.filter(q => q.scenario === ln);
    let area = `M${x(grid[0]).toFixed(1)} ${y}`; d.forEach((v, k) => { area += `L${x(grid[k]).toFixed(1)} ${(y - v / peak * rise).toFixed(1)}`; }); area += `L${x(grid[N - 1]).toFixed(1)} ${y}Z`;
    let line = ''; d.forEach((v, k) => { line += (k ? 'L' : 'M') + x(grid[k]).toFixed(1) + ' ' + (y - v / peak * rise).toFixed(1); });
    s.append(svg('path', {d: area, fill: 'var(--series)', 'fill-opacity': 0.14}), svg('path', {d: line, fill: 'none', stroke: 'var(--series)', 'stroke-opacity': 0.45, 'stroke-width': 1.2}));
    const dc = densCrit[i]; if (dc.some(v => v > 0.01)) { let ca = `M${x(grid[0]).toFixed(1)} ${y}`, cl = ''; dc.forEach((v, k) => { const yy = (y - v / peak * rise).toFixed(1); ca += `L${x(grid[k]).toFixed(1)} ${yy}`; cl += (k ? 'L' : 'M') + x(grid[k]).toFixed(1) + ' ' + yy; }); ca += `L${x(grid[N - 1]).toFixed(1)} ${y}Z`;
      let seg = '', pen = false; dc.forEach((v, k) => { if (v / peak * rise < 0.6) { pen = false; return; } seg += (pen ? 'L' : 'M') + x(grid[k]).toFixed(1) + ' ' + (y - v / peak * rise).toFixed(1); pen = true; });
      s.append(svg('path', {d: ca, fill: 'var(--crit)', 'fill-opacity': 0.22}), svg('path', {d: seg, fill: 'none', stroke: 'var(--crit)', 'stroke-opacity': 0.75, 'stroke-width': 1.2})); }
    s.append(svg('line', {x1: m.l, x2: W - m.r, y1: y, y2: y, stroke: 'var(--line)'})); lanesLabels.push(svg('text', {x: m.l + 2, y: y - 21, class: 'lbl in'}, laneName(ln)));        // the lane's name sits inside the lane, just above its zero line
    const band = svg('rect', {x: m.l, y: y - rise, width: W - m.l - m.r, height: rise + 8, fill: 'transparent'});
    band.addEventListener('mousemove', ev => { const r = s.getBoundingClientRect(), tv = t0 + ((ev.clientX - r.left) / r.width * W - m.l) / (W - m.l - m.r) * (t1 - t0), near = cases.filter(q => Math.abs(q.start - tv) <= 15 * DAY), n = near.length, nc = near.filter(q => q.priority === 'critical').length;
      showTip(ev, '<b>' + esc(laneName(ln)) + '</b><br>' + n + ' case' + (n === 1 ? '' : 's') + ' in the 30 days around ' + esc(F_DAY.format(new Date(tv))) + (nc ? '<br>' + nc + ' of them critical' : '')); });
    band.addEventListener('mouseleave', hideTip); s.append(band);
    for (const e of cases) { const cc = svg('circle', {cx: x(e.start), cy: y, r: (e.priority === 'critical' ? 6 : 4.5) + (narrow ? 1 : 0), fill: e.priority === 'critical' ? 'var(--crit)' : 'var(--series)', stroke: 'var(--panel)', 'stroke-width': 2, style: 'cursor:pointer', class: 'dot'});
      cc.dataset.ep = e.id; cc.addEventListener('mouseenter', () => lightRooms(e.id)); cc.addEventListener('mouseleave', () => lightRooms(null));
      cc.addEventListener('mousemove', ev => showTip(ev, '<b>' + esc(episodeTitle(e)) + '</b><br>' + esc(lt(e.start)) + '<br>risk: ' + e.priority + (linkEp[e.id] ? '' : '<br>building-wide, no single room'))); cc.addEventListener('mouseleave', hideTip);
      cc.addEventListener('click', () => open(e)); s.append(cc); } });
  for (const t of lanesLabels) s.append(t);          // above curves and bands, so the names stay readable; they take no pointer events
  const ticks = narrow ? 3 : half ? 4 : 6; for (let i = 0; i <= ticks; i++) { const tv = t0 + (t1 - t0) * i / ticks; s.append(svg('text', {x: x(tv), y: H - 6, 'text-anchor': i === 0 ? 'start' : i === ticks ? 'end' : 'middle'}, F_DAY.format(new Date(tv)))); }
  return s; };
  let stripEl = strip(); c.append(stripEl); if (duo) { c.style.marginTop = '0'; duo.append(c); } else root.append(c);
  // Beside the building the timeline takes the height that is left in its box, so no band stays empty under it.
  tlFit = () => { if (!duo || !c.isConnected || window.innerWidth <= 1100) return; const width = stripEl.getBoundingClientRect().width || c.clientWidth - 40; stripEl.style.display = 'none';
    const free = c.getBoundingClientRect().bottom - 20 - stripEl.previousElementSibling.getBoundingClientRect().bottom - 6; stripEl.style.display = '';
    if (width < 50 || free < 120) return; const next = strip(free * 660 / width); stripEl.replaceWith(next); stripEl = next; };
  requestAnimationFrame(() => bldFit ? bldFit() : tlFit());
  // table
  const tb = el('div', 'card'); tb.append(el('h2', null, 'Technical incidents and how early they were seen'), el('p', 'note', 'How much earlier the system saw each fault than the building did. "Seen earlier by" is the time between our first decision and the moment the repair was logged in the dataset: 187 h means we flagged it 187 hours before anyone wrote the repair order. Longer is better. The repair orders are used for this comparison only; no detector reads them.'));
  const sc = el('div', 'scroll'), table = el('table'), hr = el('tr'); ['Case', 'Our first decision (Vienna)', 'Risk', 'Repair logged in the dataset', 'Seen earlier by'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
  for (const e of E.filter(q => ['room_flow', 'main_gap', 'cop'].includes(q.kind) || (q.kind === 'ahu' && q.issue_type !== 'data_quality'))) { const tr = el('tr', 'go'); tr.onclick = () => open(e);
    tr.append(el('td', null, episodeTitle(e)), el('td', 'm', lt(e.start))); const td = el('td'); td.append(el('span', 'tag p-' + e.priority, e.priority)); tr.append(td);
    const lead = el('td', 'n', e.check ? Math.round(e.check.lead_h) + ' h' : '');
    if (e.check) lead.title = 'Our first decision was taken ' + Math.round(e.check.lead_h) + ' hours before the repair order ' + e.check.id + ' was written (' + lt(e.check.t) + ')';
    tr.append(el('td', null, e.check ? e.check.text + ' · ' + dhm(e.check.t) : 'none within 14 days'), lead); table.append(tr); }
  labelCells(table); sc.append(table); tb.append(sc); root.append(tb);
}
function scenario(root, sc) {
  const list = E.filter(e => e.scenario === sc), routine = list.filter(e => e.routine).length;
  const shown = list.filter(e => (showRoutine[sc] || !e.routine) && (!query || JSON.stringify(e.decisions).toLowerCase().includes(query)));
  if (!shown.includes(selected[sc])) selected[sc] = shown.find(e => e.priority === 'critical') || shown[0] || null;
  const split = el('div', 'split'), L = el('div', 'list'), tools = el('div', 'tools');
  tools.append(document.createTextNode(shown.length + ' case(s)'));
  if (routine) { const lb = el('label'); lb.style.marginLeft = '10px'; const cb = el('input'); cb.type = 'checkbox'; cb.checked = !!showRoutine[sc]; cb.onchange = () => { showRoutine[sc] = cb.checked; render(); };
    lb.append(cb, document.createTextNode(' show ' + routine + ' routine guest answers')); tools.append(lb); }
  const q = el('input'); q.type = 'search'; q.placeholder = 'Filter by room, booking or text'; q.value = query; q.onchange = () => { query = q.value.trim().toLowerCase(); render(); }; tools.append(q);
  const kh = el('div', 'keys'); kh.append(el('kbd', null, '↑'), document.createTextNode(' '), el('kbd', null, '↓'), document.createTextNode(' next case  '), el('kbd', null, '←'), document.createTextNode(' '), el('kbd', null, '→'), document.createTextNode(' next tab')); tools.append(kh);
  L.append(tools);
  if (!shown.length) L.append(el('div', 'empty', 'No case matches.'));
  for (const e of shown) { const r = el('div', 'row' + (e === selected[sc] ? ' on' : '')); r.append(el('div', 't', lt(e.start)), el('div', 'a', episodeTitle(e)));
    const tg = el('div'); tg.append(el('span', 'tag p-' + e.priority, e.priority), el('span', 'tag plain', e.decisions.length + ' decision' + (e.decisions.length > 1 ? 's' : ''))); if (e.check) { const tgl = el('span', 'tag l-autonomous', Math.round(e.check.lead_h) + ' h early'); tgl.title = 'Flagged ' + Math.round(e.check.lead_h) + ' hours before the repair was logged in the dataset'; tg.append(tgl); }
    r.append(tg); const sp = spark(e); if (sp) r.append(sp); r.tabIndex = 0; r.onclick = () => { selected[sc] = e; history.replaceState(null, '', '#' + sc + ':' + encodeURIComponent(e.id)); render(); }; L.append(r); }
  split.append(L, detail(selected[sc])); root.append(split);
  // Put the selected case directly under the pinned filter bar, measured rather than assumed: the bar's
  // height changes with the tab (the routine checkbox) and once the web fonts have loaded.
  const place = () => { const on = L.querySelector('.row.on'); if (!on || !L.isConnected) return;
    L.scrollTop = Math.max(0, L.scrollTop + on.getBoundingClientRect().top - tools.getBoundingClientRect().bottom); };
  place(); requestAnimationFrame(place); if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
}
const logF = {q: '', scenario: '', action: '', priority: '', level: ''};       // filters of the log; they survive a change of view
function trail(root) {
  const c = el('div', 'card'); c.style.marginTop = '0'; c.append(el('h2', null, 'Every decision, in order'), el('p', 'note', 'The complete log as written to ' + D.source + '. Filter it, then click a row to open its case.'));
  const rows = E.flatMap(e => e.decisions.map(d => [d, e])).sort((a, b) => tsOf(a[0]) - tsOf(b[0])), cap = 1500;
  const bar = el('div', 'filters'), count = el('span', 'fcount'), sc = el('div', 'scroll'), more = el('p', 'note');
  const uniq = f => [...new Set(rows.map(f))].filter(Boolean).sort();
  const pick = (key, label, values, name) => { const sel = el('select'); sel.setAttribute('aria-label', label); const all0 = el('option', null, label + ': all'); all0.value = ''; sel.append(all0);
    for (const v of values) { const o = el('option', null, name ? name(v) : v.replace(/_/g, ' ')); o.value = v; sel.append(o); } sel.value = logF[key]; sel.onchange = () => { logF[key] = sel.value; fill(); }; return sel; };
  const q = el('input'); q.type = 'search'; q.placeholder = 'Search room, asset or words in the reason'; q.setAttribute('aria-label', 'Search the log'); q.value = logF.q; q.oninput = () => { logF.q = q.value; fill(); };
  const reset = el('button', null, 'Reset'); reset.type = 'button'; reset.onclick = () => { for (const k in logF) logF[k] = ''; render(); };
  bar.append(q, pick('scenario', 'View', Object.keys(SC).filter(k => rows.some(r => r[1].scenario === k)), k => SC[k].replace(/^S(\d\d)/, 'S-$1')), pick('action', 'Action', uniq(r => r[0].action)),
    pick('priority', 'Risk', ['critical', 'high', 'medium', 'low'].filter(p => rows.some(r => r[0].priority === p))), pick('level', 'Autonomy', Object.keys(LEVEL).filter(l => rows.some(r => level(r[0]) === l)), l => LEVEL[l]), reset, count);
  function fill() { const words = logF.q.toLowerCase().split(/\s+/).filter(Boolean);
    const hit = rows.filter(([d, e]) => (!logF.scenario || e.scenario === logF.scenario) && (!logF.action || d.action === logF.action) && (!logF.priority || d.priority === logF.priority) && (!logF.level || level(d) === logF.level)
      && (!words.length || (() => { const hay = ((d.affected_assets || []).join(' ') + ' ' + d.reason + ' ' + d.action + ' ' + d.issue_type).toLowerCase(); return words.every(w => hay.includes(w)); })()));
    const table = el('table'), hr = el('tr'); ['Time (Vienna)', 'Action', 'Assets', 'Risk', 'Autonomy', 'Reason'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
    for (const [d, e] of hit.slice(0, cap)) { const tr = el('tr', 'go'); tr.onclick = () => open(e);
      const a = d.affected_assets || []; tr.append(el('td', 'n', dhm(tsOf(d))), el('td', null, d.action.replace(/_/g, ' ')), el('td', null, a.slice(0, 3).join(', ') + (a.length > 3 ? ' +' + (a.length - 3) : '')));
      const p = el('td'); p.append(el('span', 'tag p-' + d.priority, d.priority)); const l = el('td'); l.append(el('span', 'tag l-' + level(d), LEVEL[level(d)]));
      tr.append(p, l, el('td', null, d.reason.length > 170 ? d.reason.slice(0, 170) + '…' : d.reason)); table.append(tr); }
    labelCells(table); sc.replaceChildren(hit.length ? table : el('p', 'note', 'No decision matches these filters.'));
    count.textContent = hit.length === rows.length ? rows.length + ' decisions' : hit.length + ' of ' + rows.length + ' decisions';
    more.textContent = hit.length > cap ? 'Showing the first ' + cap + ' of ' + hit.length + '.' : ''; }
  fill(); c.append(bar, sc, more); root.append(c);
}
function queue(root) {
  const open_ = pending(), done = all.filter(d => approvals[d.event_id] && approvals[d.event_id].state);
  const tl = el('div', 'tiles'); tl.append(tile(open_.length, 'waiting for a person', null, true), tile(open_.filter(d => level(d) === 'approval_and_consent').length, 'of these need guest consent'),
    tile(done.filter(d => approvals[d.event_id].state === 'approved').length, 'approved'), tile(done.filter(d => approvals[d.event_id].state === 'rejected').length, 'rejected')); root.append(tl);
  const c = el('div', 'card'); c.append(el('h2', null, 'Approval queue'), el('p', 'note', 'Everything the building may not do on its own: technician and contractor call-outs, blocking a room, the on-call housekeeper, entering an occupied room. Most urgent first.'));
  const rank = {critical: 0, high: 1, medium: 2, low: 3}, chain = el('div', 'chain');
  for (const d of open_.slice().sort((a, b) => rank[a.priority] - rank[b.priority] || tsOf(a) - tsOf(b))) chain.append(step(d));
  if (!open_.length) chain.append(el('div', 'empty', 'Nothing is waiting.')); c.append(chain); root.append(c);
  const lg = el('div', 'card'); lg.append(el('h2', null, 'Approval log'), el('p', 'note', 'Who decided what in this session. Kept in this browser; export it to keep it.'));
  if (done.length) { const sc = el('div', 'scroll'), table = el('table'), hr = el('tr'); ['Decided (Vienna)', 'Result', 'Action', 'Assets', 'Case'].forEach(h => hr.append(el('th', null, h))); table.append(hr);
    for (const d of done.sort((a, b) => approvals[b.event_id].at.localeCompare(approvals[a.event_id].at))) { const a = approvals[d.event_id], tr = el('tr', 'go'); tr.onclick = () => open(E.find(e => e.id === d.episode_id));
      tr.append(el('td', 'm', lt(Date.parse(a.at)))); const td = el('td'); td.append(el('span', 'tag ' + (a.state === 'approved' ? 'l-autonomous' : 'p-critical'), a.state)); tr.append(td, el('td', null, d.action.replace(/_/g, ' ')), el('td', null, (d.affected_assets || []).slice(0, 4).join(', ')), el('td', 'm', d.episode_id)); table.append(tr); }
    labelCells(table); sc.append(table); lg.append(sc);
    const row = el('div', 'act'), ex = el('button', null, 'Export log (JSON)'), cl = el('button', 'no', 'Clear log'); ex.type = cl.type = 'button';
    ex.onclick = () => { const blob = new Blob([JSON.stringify(Object.entries(approvals).filter(([, v]) => v.state).map(([event_id, v]) => Object.assign({event_id}, v)), null, 1)], {type: 'application/json'}), a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'approvals.json'; a.click(); URL.revokeObjectURL(a.href); };
    cl.onclick = () => { if (window.confirm('Clear the approval log? Every approval and rejection in this browser is removed.')) { approvals = {}; saveApprovals(); render(); } }; row.append(ex, cl); lg.append(row); }
  else lg.append(el('div', 'empty', 'No decision taken yet.'));
  root.append(lg);
}
function open(e) { tab = e.scenario in SC ? e.scenario : 'trail'; history.replaceState(null, '', '#' + tab + ':' + encodeURIComponent(e.id)); if (e.routine) showRoutine[e.scenario] = true; selected[e.scenario] = e; query = ''; render(); window.scrollTo(0, 0); }
function render() {
  hideTip();
  const nav = $('nav'); nav.replaceChildren();
  const inc = E.filter(e => !e.routine), by = k => inc.filter(e => e.scenario === k).length;
  // Every box has the same three lines: figure, short code, name. SC labels are "S01 Turnaround": code, then name.
  const split = k => { const i = SC[k].indexOf(' '); return [SC[k].slice(0, i), SC[k].slice(i + 1)]; };
  const tabs = [['overview', inc.length, 'All', 'Overview'], ['queue', pending().length, 'Open', 'Approvals'], ...Object.keys(SC).map(k => [k, by(k), ...split(k)]), ['trail', all.length, 'Log', 'All decisions']];
  if (D.budget) tabs.splice(tabs.length - 1, 0, ['budget', Math.round(D.budget.bill.eur / 1000) + 'k', 'Plan €', 'Budget']);
  if (D.staff) tabs.splice(tabs.length - 1, 0, ['staff', D.staff.resources.length, 'Plan', 'Staff']);
  for (const [k, n, code, name] of tabs) { const b = el('button', k === tab ? 'on' : ''); b.title = TABHINT[k] || ''; b.dataset.tab = k; b.setAttribute('aria-current', k === tab ? 'page' : 'false');
    b.setAttribute('aria-label', code + ' ' + name + ', ' + n);
    b.append(el('b', null, n), el('i', null, code.replace(/^S(\d\d)$/, 'S-$1')), el('span', null, name === 'Event weekend' ? 'Weekend' : name));     // twelve boxes: the short name fits, the full one is in the hint
    b.onclick = () => { tab = k; history.replaceState(null, '', '#' + k); render(); }; nav.append(b); }
  const root = $('view'); root.replaceChildren();
  if (tab === 'overview') overview(root); else if (tab === 'budget') budgetView(root); else if (tab === 'staff') staffView(root); else if (tab === 'trail') trail(root); else if (tab === 'queue') queue(root); else scenario(root, tab);
}

/* ---------- voice control (opt-in): the agent's tools run here, in the page ---------- */
let VQ = [];
const short = (t, n) => t.length > n ? t.slice(0, n) + '…' : t;
const VIEW = {overview: 'overview', turnaround: 'S01', water: 'S02', heating: 'S03', maintenance: 'S04', weekend: 'S05', energy: 'ENG', logistics: 'LOG', budget: 'budget', staff: 'staff', approvals: 'queue', decisions: 'trail'};
function summary(e) { const main = e.decisions.find(d => d.action === 'flag_anomaly') || e.decisions[0];
  return {title: episodeTitle(e), when: lt(e.start), risk: e.priority, decisions: e.decisions.length, actions: [...new Set(e.decisions.map(d => d.action.replace(/_/g, ' ')))],
    oversight: [...new Set(e.decisions.map(d => LEVEL[level(d)]))], finding: short(main.reason, 320),
    checked_against_dataset: e.check ? 'A work order was written ' + Math.round(e.check.lead_h) + ' hours after our decision: ' + e.check.text : 'no later work order to compare' }; }
// Emergency: the whole dashboard gives way to one case. The view shows only what an emergency team
// needs: where, what was found, since when, what the system already did. The connection to the team
// is simulated here and labelled as such; no call is placed.
let emgTimer = null;
function emergency(e, what) { const box = $('emg'), inn = el('div', 'e-in'); clearTimeout(emgTimer);
  const bar = el('div', 'e-bar'), left = el('div'), line = el('div', 'e-line'), end = el('button', null, 'End emergency view'); end.type = 'button'; end.onclick = endEmergency;
  line.innerHTML = '<b>Connecting</b> you to the on-call emergency team …';
  emgTimer = setTimeout(() => { line.innerHTML = '<b>Emergency team on the line.</b> They see this case.'; }, 2500);
  left.append(el('div', 'e-eyebrow', 'Emergency · PLATO-40'), el('h1', null, e ? episodeTitle(e) : 'Emergency reported by the caller'), line,
    el('div', 'e-sim', 'Simulated in this demo: no real call is placed. In operation this step bridges the caller to the on-call number. In real danger dial 112.'));
  bar.append(left, end); inn.append(bar);
  const sec = (title, node) => { const c = el('div', 'e-sec'); c.append(el('h2', null, title), node); inn.append(c); };
  if (what) sec('The caller said', el('p', null, '“' + what + '”'));
  if (e) { const assets = [...new Set(e.decisions.flatMap(d => d.affected_assets || []))], main = e.decisions.find(d => d.action === 'flag_anomaly') || e.decisions[0];
    const facts = el('div', 'e-facts'), fact = (k, v) => { const f = el('div', 'e-fact'); f.append(el('span', null, k), el('b', null, v)); facts.append(f); };
    fact('Where', assets.slice(0, 4).join(', ') || 'not stated'); fact('First seen (Vienna)', lt(e.start)); fact('Risk', e.priority);
    fact('Waiting for a person', e.decisions.filter(d => level(d) !== 'autonomous' && !(approvals[d.event_id] && approvals[d.event_id].state)).length + ' of ' + e.decisions.length + ' decisions');
    inn.append(facts);
    sec('What was found', el('p', null, main.reason));
    const ev = el('ul'); for (const x of [...new Set(e.decisions.flatMap(d => d.evidence || []))].slice(0, 6)) { const li = el('li'); li.append(el('code', null, x)); ev.append(li); }
    if (ev.children.length) sec('Evidence', ev);
    const done = el('ul'); for (const d of e.decisions) { const st = approvals[d.event_id] && approvals[d.event_id].state;
      done.append(el('li', null, dhm(tsOf(d)) + ' · ' + d.action.replace(/_/g, ' ') + ' · ' + (level(d) === 'autonomous' ? 'done by the system (simulated)' : st ? st + ' by a person' : 'waits for ' + LEVEL[level(d)]))); }
    sec('What the system has done so far', done); }
  else sec('No case identified', el('p', null, 'The system has no matching case for this report. Say or type the room, for example “R403”, and the case will be shown here.'));
  box.replaceChildren(inn); box.className = 'on'; box.scrollTop = 0; document.body.style.overflow = 'hidden'; }
function endEmergency() { clearTimeout(emgTimer); $('emg').className = ''; $('emg').replaceChildren(); document.body.style.overflow = ''; }
document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && $('emg').className === 'on') endEmergency(); });
const VT = {
  get_status() { const inc = E.filter(e => !e.routine), by = s => inc.filter(e => e.scenario === s).length, p = pending(), rank = {critical: 0, high: 1, medium: 2, low: 3};
    return {dataset: D.profile, decisions_total: all.length, cases: {turnaround: by('S01'), water: by('S02'), heating: by('S03'), maintenance: by('S04'), event_weekends: by('S05'), energy_plans: by('ENG'), logistics_orders: by('LOG')}, routine_guest_answers: E.length - inc.length,
      waiting_for_a_person: p.length, of_these_need_guest_consent: p.filter(d => level(d) === 'approval_and_consent').length,
      most_urgent_open: p.slice().sort((a, b) => rank[a.priority] - rank[b.priority] || tsOf(a) - tsOf(b)).slice(0, 3).map(d => ({action: d.action.replace(/_/g, ' '), assets: (d.affected_assets || []).slice(0, 3), risk: d.priority, when: lt(tsOf(d))})),
      critical_cases: inc.filter(e => e.priority === 'critical').length,
      latest_critical_cases: inc.filter(e => e.priority === 'critical').sort((a, b) => b.start - a.start).slice(0, 4).map(e => ({case: episodeTitle(e), when: lt(e.start), flagged_before_repair_hours: e.check ? Math.round(e.check.lead_h) : null})),
      note: 'Replay of a fictional building. Effects of actions are simulated.'}; },
  open_view({view}) { const k = VIEW[String(view || '').toLowerCase()]; if (!k) return {error: 'Unknown view. Use one of: ' + Object.keys(VIEW).join(', ')};
    tab = k; history.replaceState(null, '', '#' + k); render(); return {ok: true, showing: view}; },
  open_case({query}) { const words = String(query || '').toLowerCase().split(/[^a-z0-9äöü.-]+/).filter(w => w.length > 1); if (!words.length) return {error: 'Say what to look for, for example a room or heat pump.'};
    let best = null, bestScore = 0; const pr = {critical: 3, high: 2, medium: 1, low: 0};
    for (const e of E) { const hay = (episodeTitle(e) + ' ' + e.id + ' ' + e.decisions.map(d => d.reason).join(' ')).toLowerCase(); let sc = 0;
      for (const w of words) { if (episodeTitle(e).toLowerCase().includes(w) || e.id.toLowerCase().includes(w)) sc += 3; else if (hay.includes(w)) sc += 1; }
      if (!sc) continue; sc = sc * 10 + pr[e.priority] + (e.routine ? 0 : 2) + (e.check ? 1 : 0); if (sc > bestScore) { bestScore = sc; best = e; } }
    if (!best) return {error: 'No case found for: ' + query}; open(best); return Object.assign({ok: true}, summary(best)); },
  describe_current_case() { const e = tab in SC ? selected[tab] : null; if (!e) return {error: 'No case is open. Open one first.'}; return summary(e); },
  list_pending_approvals({limit} = {}) { const rank = {critical: 0, high: 1, medium: 2, low: 3}, n = Math.max(1, Math.min(10, +limit || 3));
    VQ = pending().slice().sort((a, b) => rank[a.priority] - rank[b.priority] || tsOf(a) - tsOf(b)); tab = 'queue'; history.replaceState(null, '', '#queue'); render();
    return {waiting: VQ.length, items: VQ.slice(0, n).map((d, i) => ({item: i + 1, action: d.action.replace(/_/g, ' '), assets: (d.affected_assets || []).slice(0, 3), risk: d.priority,
      needs_guest_consent: level(d) === 'approval_and_consent', consent_on_record: !!(approvals[d.event_id] && approvals[d.event_id].consent), when: lt(tsOf(d)), reason: short(d.reason, 220)}))}; },
  _item(item) { const d = VQ[(+item || 0) - 1]; if (!d) return {error: 'No such item. Call list_pending_approvals first.'}; if (approvals[d.event_id] && approvals[d.event_id].state) return {error: 'That item was already ' + approvals[d.event_id].state + '.'}; return {d}; },
  record_guest_consent({item}) { const r = VT._item(item); if (r.error) return r; if (level(r.d) !== 'approval_and_consent') return {error: 'That item does not need guest consent.'};
    approvals[r.d.event_id] = Object.assign(approvals[r.d.event_id] || {}, {consent: true}); saveApprovals(); render(); return {ok: true, result: 'Guest consent recorded for item ' + item + '. It can now be approved.'}; },
  approve({item}) { const r = VT._item(item); if (r.error) return r; const d = r.d;
    if (level(d) === 'approval_and_consent' && !(approvals[d.event_id] && approvals[d.event_id].consent)) return {error: 'Guest consent is not on record for this item. Not approved.'};
    decide(d, 'approved'); return {ok: true, result: 'approved in the simulation', action: d.action.replace(/_/g, ' '), assets: (d.affected_assets || []).slice(0, 3), still_waiting: pending().length}; },
  emergency({query, what} = {}) { let e = null;
    if (query) { const r = VT.open_case({query}); if (!r.error) e = selected[tab]; }
    if (!e && tab in SC) e = selected[tab] || null;
    emergency(e, what ? String(what).slice(0, 300) : '');
    return Object.assign({ok: true, connection: 'simulated: the emergency team is shown as connected, no real call is placed', screen: 'the dashboard now shows only this case'},
      e ? {case: summary(e), where: [...new Set(e.decisions.flatMap(d => d.affected_assets || []))].slice(0, 4)} : {case: null, note: 'No matching case. Ask for the room and call emergency again with it.'}); },
  end_emergency() { endEmergency(); return {ok: true, result: 'emergency view closed, dashboard is back'}; },
  reject({item}) { const r = VT._item(item); if (r.error) return r; decide(r.d, 'rejected'); return {ok: true, result: 'rejected, not executed', action: r.d.action.replace(/_/g, ' '), still_waiting: pending().length}; },
};
// "Voice briefing" in the header is the one voice entry point: a click starts a call with the
// ElevenLabs agent and asks for the urgent items; the conversation then continues freely. The
// agent's tools are the handlers above, so it acts through this page's own code and rules.
let call = null;
function vsay(text, me) { const c = $('vcap2'), p = el('p', me ? 'me' : '', (me ? 'You: ' : '') + text); c.append(p); while (c.children.length > 8) c.firstChild.remove(); c.scrollTop = c.scrollHeight; }
async function briefing() {
  const btn = $('brief'), box = $('vbox'), st = $('vst');
  if (call) { try { await call.endSession(); } catch (err) {} return; }
  try { box.className = 'on'; st.textContent = 'Asking for the microphone'; btn.disabled = true;
    await navigator.mediaDevices.getUserMedia({audio: true});
    st.textContent = 'Connecting';
    let mod; try { mod = await import('https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.36.1/+esm'); } catch (err) { mod = await import('https://esm.sh/@elevenlabs/client@1.36.1'); }
    const tools = {}; for (const k of Object.keys(VT)) if (k[0] !== '_') tools[k] = async args => { let out; try { out = VT[k](args || {}); } catch (err) { out = {error: String(err && err.message || err)}; } return JSON.stringify(out); };
    call = await mod.Conversation.startSession({agentId: D.voiceAgent, connectionType: 'webrtc', clientTools: tools,
      onConnect: () => { st.textContent = 'Listening'; btn.textContent = 'End briefing'; btn.classList.add('live'); },
      onDisconnect: () => { call = null; talking = false; $('ptt').classList.remove('down'); $('ptt').disabled = true; btn.textContent = 'Voice briefing'; btn.classList.remove('live'); st.textContent = 'Voice ended'; setTimeout(() => { if (!call) box.className = ''; }, 2500); },
      onModeChange: ev => { if (!talking) st.textContent = ev && ev.mode === 'speaking' ? 'Assistant is speaking' : (pttActive() ? 'Hold to talk' : 'Listening'); },
      onMessage: ev => { if (ev && ev.message) vsay(ev.message, ev.source === 'user'); },
      onError: err => { st.textContent = 'Voice error'; vsay(String(err && err.message || err)); }});
    setTimeout(() => { try { if (call && call.sendUserMessage) call.sendUserMessage('Give me a short briefing: the status, the critical cases, and what is waiting for my approval.'); } catch (err) {} }, 1200);
    applyPtt();
  } catch (err) { call = null; st.textContent = 'Voice not available'; vsay(String(err && err.message || err) + '. Voice needs a microphone, network access and a page served over https or localhost.'); }
  finally { btn.disabled = false; }
}
// Push to talk, for loud rooms: the microphone is open only while the button or the space bar is held.
let talking = false, releaseTimer = null;
const pttActive = () => !!call && $('pttOn').checked;
function mic(open) { try { if (call && call.setMicMuted) call.setMicMuted(!open); } catch (err) {} }
function applyPtt() { const on = $('pttOn').checked; $('ptt').disabled = !call || !on; $('ptt').textContent = on ? 'Hold to talk (or hold space)' : 'Microphone is open'; mic(!on); }
function talk(down) { if (!pttActive()) return; clearTimeout(releaseTimer);
  if (down) { talking = true; mic(true); $('ptt').classList.add('down'); $('vst').textContent = 'You are speaking'; }
  else if (talking) { $('ptt').classList.remove('down'); releaseTimer = setTimeout(() => { talking = false; mic(false); if (call) $('vst').textContent = 'Listening for the assistant'; }, 350); } }   // short tail so the last word is not cut
$('pttOn').onchange = applyPtt;
$('emgBtn').onclick = () => { VT.emergency({}); if (call) try { call.sendUserMessage('Emergency. I have opened the emergency view for the case on screen. Connect the emergency team and brief them.'); } catch (err) {} };
for (const [evn, down] of [['pointerdown', true], ['pointerup', false], ['pointerleave', false], ['pointercancel', false]]) $('ptt').addEventListener(evn, ev => { ev.preventDefault(); talk(down); });
const typing = ev => /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || '');
document.addEventListener('keydown', ev => { if (ev.code === 'Space' && pttActive() && !typing(ev)) { ev.preventDefault(); if (!ev.repeat) talk(true); } });
document.addEventListener('keyup', ev => { if (ev.code === 'Space' && pttActive() && !typing(ev)) { ev.preventDefault(); talk(false); } });
$('vform').addEventListener('submit', ev => { ev.preventDefault(); const t = $('vtext').value.trim(); if (!t) return;
  if (!call) { vsay('Start the voice briefing first.'); return; }
  try { call.sendUserMessage(t); vsay(t, true); $('vtext').value = ''; } catch (err) { vsay(String(err && err.message || err)); } });
if (D.apiDocs) { $('apilink').href = D.apiDocs; $('apifoot').hidden = false; }
if (D.voiceAgent) { const b = $('brief'); b.hidden = false; b.title = 'Hear the status, the critical cases and what waits for approval'; b.onclick = briefing; }
// ?voicetest runs the tool handlers without any network or microphone and shows what they return
function voiceTest() { const KEYBAK = approvals; approvals = {}; const log = [], run = (name, args) => log.push(name + '(' + JSON.stringify(args || {}) + ') -> ' + JSON.stringify(VT[name](args || {}), null, 1));
  const real = saveApprovals; window.__nosave = true;
  run('get_status'); run('open_case', {query: 'R403 water'}); run('describe_current_case'); run('open_case', {query: 'heat pump'}); run('open_case', {query: 'filter cascade'}); run('open_view', {view: 'heating'});
  run('list_pending_approvals', {limit: 10}); const ci = VQ.findIndex(d => level(d) === 'approval_and_consent') + 1;
  run('approve', {item: ci}); run('record_guest_consent', {item: 1}); run('record_guest_consent', {item: ci}); run('approve', {item: ci}); run('approve', {item: ci}); run('reject', {item: 1}); run('approve', {item: 99}); run('get_status');
  approvals = KEYBAK; window.__nosave = false; tab = 'overview'; render();
  const c = el('div', 'card'); c.append(el('h2', null, 'Voice tool self-test'), el('pre', null, log.join('\n\n'))); c.querySelector('pre').style.cssText = 'white-space:pre-wrap;font:11.5px/1.45 var(--mono);color:var(--ink2)'; $('view').prepend(c); }
// deep links: #S02 opens a tab, #S02:<episode id> opens a case
(function () { const h = decodeURIComponent(location.hash.slice(1)); if (!h) return; const i = h.indexOf(':'), k = i < 0 ? h : h.slice(0, i);
  if (k === 'overview' || k === 'trail' || k === 'queue' || k in SC || (k === 'budget' && D.budget) || (k === 'staff' && D.staff)) tab = k;
  if (i > 0) { const e = E.find(q => q.id === h.slice(i + 1)); if (e) { if (e.routine) showRoutine[e.scenario] = true; selected[e.scenario] = e; } } })();
const themeBtn = $('theme');
function setTheme(t) { if (t === 'light') document.documentElement.setAttribute('data-theme', 'light'); else document.documentElement.removeAttribute('data-theme');
  themeBtn.textContent = t === 'light' ? 'Dark theme' : 'Light theme'; try { localStorage.setItem('theme', t); } catch (err) {} }
themeBtn.onclick = () => setTheme(document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
try { setTheme(localStorage.getItem('theme') || 'dark'); } catch (err) { setTheme('dark'); }
// keyboard: arrows move through cases and tabs (not while typing)
document.addEventListener('keydown', ev => { if (/^(INPUT|TEXTAREA|SELECT)$/.test((ev.target.tagName || ''))) return;
  const order = ['overview', 'queue', ...Object.keys(SC), ...(D.budget ? ['budget'] : []), ...(D.staff ? ['staff'] : []), 'trail'];
  if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') { const i = order.indexOf(tab), j = (i + (ev.key === 'ArrowRight' ? 1 : order.length - 1)) % order.length; tab = order[j]; history.replaceState(null, '', '#' + tab); render(); ev.preventDefault(); }
  else if ((ev.key === 'ArrowDown' || ev.key === 'ArrowUp') && tab in SC) { const list = E.filter(e => e.scenario === tab && (showRoutine[tab] || !e.routine) && (!query || JSON.stringify(e.decisions).toLowerCase().includes(query)));
    const i = list.indexOf(selected[tab]), j = Math.max(0, Math.min(list.length - 1, i + (ev.key === 'ArrowDown' ? 1 : -1))); if (list[j] && j !== i) { selected[tab] = list[j]; history.replaceState(null, '', '#' + tab + ':' + encodeURIComponent(list[j].id)); render(); } ev.preventDefault(); } });
let lastW = window.innerWidth, timer = null;
if (/[?&]voicetest\b/.test(location.search)) setTimeout(voiceTest, 0);
if (/[?&]emergencytest\b/.test(location.search)) setTimeout(() => console.log(JSON.stringify(VT.emergency({query: 'R201', what: 'Water is coming through the ceiling in the corridor on the second floor.'}))), 300);
// ?tiptest pins a tooltip at the right edge, for a screenshot check of the placement
if (/[?&]tiptest\b/.test(location.search)) setTimeout(() => { const vw = document.documentElement.clientWidth; showTip({clientX: vw - 8, clientY: 300}, '<b>Water leak in a room · R208</b><br>2026-11-10 16:30 CET<br>risk: high'); const r = tip.getBoundingClientRect(); document.title = 'tip ' + Math.round(r.left) + '..' + Math.round(r.right) + ' of ' + vw; const m = document.createElement('div'); m.style.cssText = 'position:fixed;left:' + (vw - 9) + 'px;top:294px;width:6px;height:12px;background:#ffb020;z-index:20'; document.body.append(m); }, 50);
window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => { if (Math.abs(window.innerWidth - lastW) > 40) { lastW = window.innerWidth; render(); } }, 150); });
render();
</script>
</body>
</html>
"""
