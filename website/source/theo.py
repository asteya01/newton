"""Theo, the website helper. A scripted Q&A widget: no AI, no network. Answers only restate what the site says."""
import json

QA = [
 ("What is Newton?", "Newton turns plain English into the exact shell command. Type a sentence, press Tab, and the command appears in your prompt for you to read and run. It works in zsh, bash and fish."),
 ("How do I install it?", "Download newton.zip from the <a href=\"download.html\">download page</a>, unzip it, and run <code>sh install.sh</code>. It needs Python 3.9 or newer and no admin rights. The installer then helps you pick an AI and turn on Tab."),
 ("Does Newton run commands for me?", "Not with Tab. It only writes the command and you press Enter. Plan mode runs a step only after you approve it. Iris, the agent, runs read-only steps on its own and asks before anything that could change something."),
 ("What is Iris?", "Iris is a chat app that comes with Newton. Run <code>newton agent</code> and it opens in your browser, works on your computer step by step, and tells you what it found. <a href=\"iris.html\">See the demo</a>."),
 ("Is Newton free?", "Yes. Newton is free and MIT licensed. Your AI provider may charge: Claude and OpenAI-compatible services bill for usage, while Ollama runs models on your own computer at no cost."),
 ("What does Newton Max cost?", "Newton Max is $7 a month. Its extras, such as hosted models and priority support, are marked Planned, and you can reserve early access on the <a href=\"pricing.html\">pricing page</a>."),
 ("What does it send to the AI?", "For Tab suggestions: your request plus a short description of your setup, like your OS, shell and current folder. Never file contents, environment variables or shell history."),
 ("Can I use it offline?", "Yes, with Ollama running a model on your own computer. Nothing leaves your machine. Small local models make more mistakes than Claude, so read each command before you press Enter."),
 ("Which systems work?", "macOS and Linux, including a Chromebook's Linux terminal. Windows works through WSL. You need zsh, bash 4 or newer, or fish."),
 ("How do I contact you?", "Email <a href=\"mailto:tangriasteya@gmail.com\">tangriasteya@gmail.com</a>. You can also use the <a href=\"join.html\">Join page</a> if you want to work with us."),
]

INTRO = "Hi, I'm Theo, Newton's helper. I answer common questions about Newton, like installing it, what it sends to your AI, and what Iris can do. I'm a set of ready-made answers, not a live AI, so for anything else, email tangriasteya@gmail.com."

CSS = r'''
/* ---- Theo helper ---- */
.theo-fab{position:fixed;right:22px;bottom:22px;z-index:90;display:flex;align-items:center;gap:10px;height:54px;padding:0 20px 0 8px;border-radius:999px;border:1px solid rgba(255,255,255,.16);background:rgba(10,16,24,.92);color:#fff;font:600 .95rem var(--f-sans);cursor:pointer;box-shadow:0 18px 50px -14px rgba(0,0,0,.7),0 0 40px -14px rgba(61,245,167,.5);backdrop-filter:blur(12px);transition:transform .18s,box-shadow .18s}
.theo-fab:hover{transform:translateY(-2px)}
.theo-fab:focus-visible,.theo-x:focus-visible,.theo-sel:focus-visible{outline:3px solid #6FF0A0;outline-offset:2px}
.theo-av{width:38px;height:38px;border-radius:50%;flex:none;display:grid;place-items:center;background:var(--grad);color:#04130B;font:700 1.05rem var(--f-sans);letter-spacing:-.03em}
.theo-fab[aria-expanded="true"]{display:none}
.theo{position:fixed;right:22px;bottom:22px;z-index:91;width:min(392px,calc(100vw - 28px));height:min(580px,calc(100vh - 44px));display:none;flex-direction:column;border-radius:22px;overflow:hidden;background:#0B141C;color:var(--text-d);border:1px solid rgba(255,255,255,.14);box-shadow:0 40px 100px -20px rgba(0,0,0,.85),0 0 80px -30px rgba(61,245,167,.4);font-family:var(--f-sans)}
.theo.open{display:flex;animation:theoin .22s ease-out}
@keyframes theoin{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
.theo-h{display:flex;align-items:center;gap:12px;padding:14px 14px 14px 16px;border-bottom:1px solid var(--line-d);background:rgba(255,255,255,.03)}
.theo-h .t{flex:1;min-width:0}.theo-h .t b{display:block;font-size:1rem;color:#fff}.theo-h .t span{font-size:.8rem;color:var(--muted-d)}
.theo-x{width:34px;height:34px;border-radius:50%;border:0;background:rgba(255,255,255,.08);color:#fff;font-size:1.1rem;cursor:pointer}
.theo-x:hover{background:rgba(255,255,255,.16)}
.theo-log{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}
.theo-m{max-width:88%;padding:11px 14px;border-radius:16px;font-size:.95rem;line-height:1.5;overflow-wrap:anywhere}
.theo-m.bot{align-self:flex-start;background:#15222D;border:1px solid var(--line-d);border-bottom-left-radius:5px}
.theo-m.me{align-self:flex-end;background:#1E5A43;color:#fff;border-bottom-right-radius:5px}
.theo-m a{color:var(--mint)}.theo-m code{font:500 .86em var(--f-mono);background:rgba(255,255,255,.09);border-radius:5px;padding:1px 5px}
.theo-dots{display:inline-flex;gap:5px;padding:4px 2px}.theo-dots i{width:7px;height:7px;border-radius:50%;background:var(--muted-d);animation:theod 1s infinite}.theo-dots i:nth-child(2){animation-delay:.15s}.theo-dots i:nth-child(3){animation-delay:.3s}
@keyframes theod{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
.theo-caret::after{content:"";display:inline-block;width:2px;height:1em;margin-left:2px;vertical-align:-2px;background:var(--mint);animation:theob 1s steps(2) infinite}
@keyframes theob{50%{opacity:0}}
.theo-f{padding:12px 14px 14px;border-top:1px solid var(--line-d);background:rgba(255,255,255,.03)}
.theo-f label{display:block;font-size:.78rem;color:var(--muted-d);margin-bottom:7px}
.theo-sel{width:100%;appearance:none;-webkit-appearance:none;background:#15222D url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' fill='none' stroke='%2398A6B5' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E") right 14px center/12px no-repeat;color:#fff;border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:12px 38px 12px 14px;font:500 .95rem var(--f-sans);cursor:pointer}
.theo-sel:disabled{opacity:.55;cursor:wait}.theo-sel option{background:#15222D;color:#fff}
@media (max-width:560px){.theo{right:8px;bottom:8px;width:calc(100vw - 16px);height:min(80vh,600px)}.theo-fab{right:14px;bottom:14px}.theo-fab span.lbl{display:none}.theo-fab{padding:0 8px}}
@media (prefers-reduced-motion:reduce){.theo.open{animation:none}.theo-dots i{animation:none;opacity:.6}.theo-caret::after{animation:none}.theo-log{scroll-behavior:auto}}
'''

HTML = '''<button class="theo-fab" id="theoFab" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="theo"><span class="theo-av" aria-hidden="true">T</span><span class="lbl">Ask Theo</span></button>
<section class="theo" id="theo" role="dialog" aria-label="Theo, Newton's helper" aria-modal="false">
  <div class="theo-h"><span class="theo-av" aria-hidden="true">T</span><div class="t"><b>Theo</b><span>Newton's helper</span></div><button class="theo-x" id="theoX" type="button" aria-label="Close chat">✕</button></div>
  <div class="theo-log" id="theoLog" role="log" aria-live="polite"></div>
  <div class="theo-f"><label for="theoSel">Pick a question</label>
    <select class="theo-sel" id="theoSel" disabled><option value="">Choose a question…</option></select></div>
</section>'''

JS = '<script>(function(){"use strict";\nvar QA=' + json.dumps(QA, ensure_ascii=False) + ';\nvar INTRO=' + json.dumps(INTRO, ensure_ascii=False) + ';\n' + r'''
var fab=document.getElementById("theoFab"),box=document.getElementById("theo"),log=document.getElementById("theoLog"),sel=document.getElementById("theoSel"),closeBtn=document.getElementById("theoX");
if(!fab||!box)return;
var reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches,run=0;
var sleep=function(ms){return new Promise(function(r){setTimeout(r,reduce?0:ms)})};
QA.forEach(function(q,i){var o=document.createElement("option");o.value=i;o.textContent=q[0];sel.appendChild(o)});
function add(cls){var d=document.createElement("div");d.className="theo-m "+cls;log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
function dots(){var d=add("bot");d.innerHTML='<span class="theo-dots" aria-label="Theo is typing"><i></i><i></i><i></i></span>';return d}
function plain(h){var t=document.createElement("div");t.innerHTML=h;return t.textContent}
async function typeInto(el,html,id){
  var text=plain(html);
  if(reduce){el.innerHTML=html;return}
  el.classList.add("theo-caret");el.textContent="";
  var step=Math.max(1,Math.round(text.length/90));
  for(var i=0;i<text.length;i+=step){if(id!==run)return;el.textContent=text.slice(0,i+step);log.scrollTop=log.scrollHeight;await sleep(16)}
  if(id!==run)return;el.classList.remove("theo-caret");el.innerHTML=html;log.scrollTop=log.scrollHeight;
}
async function bot(html,id){var d=dots();await sleep(700);if(id!==run)return;d.innerHTML="";await typeInto(d,html,id)}
async function intro(){
  var id=++run;log.innerHTML="";sel.disabled=true;sel.value="";
  await bot(INTRO,id);if(id!==run)return;
  sel.disabled=false;
}
sel.addEventListener("change",async function(){
  if(sel.value==="")return;var q=QA[+sel.value],id=run;sel.disabled=true;sel.value="";
  add("me").textContent=q[0];await bot(q[1],id);if(id!==run)return;sel.disabled=false;sel.focus();
});
function open(){box.classList.add("open");fab.setAttribute("aria-expanded","true");intro();closeBtn.focus()}
function close(){run++;box.classList.remove("open");fab.setAttribute("aria-expanded","false");fab.focus()}
fab.addEventListener("click",open);closeBtn.addEventListener("click",close);
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&box.classList.contains("open"))close()});
})();</script>'''
