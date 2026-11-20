import re, hashlib, os
v2=open('v2.html').read()
style=re.search(r'<style>(.*?)</style>',v2,re.S).group(1)
defs=open('mark_defs.txt').read(); body=open('mark_body.txt').read()
if not defs.strip().startswith('<defs'): defs='<defs>'+defs+'</defs>'
z=open('newton.zip','rb').read(); sha=hashlib.sha256(z).hexdigest(); kb=round(len(z)/1024)
VER="2.2.1"
extra='''
.dl-hero{position:relative;overflow:hidden;isolation:isolate;padding-block:calc(var(--nav-h) + 90px) 90px}
.dl-grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:clamp(28px,5vw,72px);align-items:center}
.dl-hero h1{font-size:clamp(3rem,7vw,5.8rem);line-height:.96;letter-spacing:-.055em;margin-top:24px}
.dl-hero .lead{margin-top:24px}
.btn-lg{min-height:60px;padding:0 34px;font-size:1.12rem}
.dl-actions{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-top:34px}
.dl-note{margin-top:16px;font-size:.92rem;color:var(--muted-d)}
.pkg{position:relative;border:1px solid rgba(255,255,255,.14);border-radius:28px;padding:30px;background:linear-gradient(160deg,rgba(255,255,255,.08),rgba(255,255,255,.02));box-shadow:0 60px 120px -40px rgba(0,0,0,.9),0 0 120px -40px rgba(61,245,167,.35);display:grid;gap:22px}
.pkg-top{display:flex;align-items:center;gap:18px}
.pkg-top svg{width:72px;height:72px;flex:none}
.pkg-top b{display:block;font:600 1.5rem var(--f-mono);letter-spacing:-.02em}
.pkg-top span{color:var(--muted-d);font-size:.95rem}
.kv{display:grid;gap:0;margin:0}
.kv div{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-top:1px solid var(--line-d);font-size:.98rem}
.kv dt{color:var(--muted-d)}.kv dd{margin:0;font-family:var(--f-mono);font-size:.92rem;text-align:right}
.hash{position:relative;background:#070C12;border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px 76px 14px 16px;font:400 .8rem/1.6 var(--f-mono);color:#B9C9D6;overflow-wrap:anywhere}
.hash .copy{top:50%;transform:translateY(-50%)}
.reqs{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.req{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:28px;display:grid;gap:8px;align-content:start}
.req h3{font-size:1.25rem}.req p{color:var(--muted)}
.req code,.rel code,.note-l code{font-size:.88em;background:rgba(6,122,85,.09);color:var(--leaf);padding:.1em .4em;border-radius:5px}
.rel{display:grid;gap:0;max-width:880px}
.rel>div{display:grid;grid-template-columns:130px 1fr;gap:10px 28px;padding:26px 0;border-top:1px solid var(--line)}
.rel>div:last-child{border-bottom:1px solid var(--line)}
.rel b{font:600 1.5rem var(--f-sans);letter-spacing:-.04em}
.rel p{color:var(--muted);max-width:60ch}
.rel strong{color:var(--text);font-weight:600}
.soon-card{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;border:1px dashed rgba(255,255,255,.22);border-radius:20px;padding:24px 28px}
.soon-card em{font:500 .72rem var(--f-mono);font-style:normal;border:1px solid var(--line-d);border-radius:6px;padding:2px 8px;color:#7C8E9E;margin-left:10px}
.nav ul a.cur{color:#fff;background:rgba(255,255,255,.08)}
@media (max-width:960px){.dl-grid{grid-template-columns:1fr}.reqs{grid-template-columns:1fr}.rel>div{grid-template-columns:1fr}}
'''
nav='''<header class="nav" id="nav"><div class="nav-in">
<a class="brand" href="index.html" aria-label="Newton home"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#nmark"/></svg>newton</a>
<ul id="menu"><li><a href="index.html#how">How it works</a></li><li><a href="index.html#try">Try it</a></li><li><a href="index.html#plan">Plan mode</a></li><li><a href="index.html#features">Features</a></li><li><a href="index.html#safety">Safety</a></li><li><a href="download.html" class="cur" aria-current="page">Download</a></li><li><a href="index.html#faq">FAQ</a></li></ul>
<a class="btn btn-primary btn-sm" href="#get">Download</a>
<button class="menu-btn" id="menuBtn" aria-expanded="false" aria-controls="menu" type="button">Menu</button></div></header>'''
def code(t,label="Copy"): return '<div class="code"><pre>'+t+'</pre><button class="copy" type="button" data-copy>'+label+'</button></div>'
html=f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Download Newton {VER}</title>
<meta name="description" content="Download Newton {VER}: one file, Python 3.9 or newer, for macOS, Linux, Chromebook and Windows (WSL).">
<meta name="theme-color" content="#05080D">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='15' fill='%230B1118'/%3E%3Cpath d='M15 29l13 10-13 10' fill='none' stroke='%237DF08A' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/%3E%3Crect x='33' y='46' width='16' height='5' rx='2.5' fill='%23fff'/%3E%3Ccircle cx='44' cy='24' r='7' fill='%233DF5A7'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300..800&family=Geist+Mono:wght@400..600&display=swap" rel="stylesheet">
<style>{style}{extra}</style></head><body>
<svg width="0" height="0" style="position:absolute;overflow:hidden" aria-hidden="true" focusable="false">{defs}<symbol id="nmark" viewBox="0 0 512 512">{body}</symbol></svg>
<a class="skip" href="#main">Skip to content</a><div id="prog" aria-hidden="true"></div>
{nav}
<main id="main">
<section class="dl-hero" id="get" aria-labelledby="h1">
  <div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div><div class="floor" aria-hidden="true"></div>
  <div class="wrap dl-grid">
    <div>
      <span class="kicker"><i></i>Version {VER} · Free · MIT license</span>
      <h1 id="h1">Download Newton.</h1>
      <p class="lead">One file, no admin rights. Works on macOS, Linux, Chromebook and Windows through WSL. Needs Python 3.9 or newer.</p>
      <div class="dl-actions">
        <a class="btn btn-primary btn-lg" id="dlBtn" href="newton.zip" download>Download newton.zip</a>
        <a class="btn btn-ghost btn-lg" href="#install">Install steps</a>
      </div>
      <p class="dl-note" id="dlNote">{kb} KB · the same file works on every system</p>
    </div>
    <div class="pkg rv">
      <div class="pkg-top"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#nmark"/></svg><div><b>newton.zip</b><span>Newton {VER}</span></div></div>
      <dl class="kv"><div><dt>Version</dt><dd>{VER}</dd></div><div><dt>Size</dt><dd>{kb} KB</dd></div><div><dt>Needs</dt><dd>Python 3.9+</dd></div><div><dt>License</dt><dd>MIT</dd></div></dl>
      <div><div class="lbl-s" style="font-size:.85rem;color:var(--muted-d);margin-bottom:8px">SHA-256 checksum</div><div class="hash"><span id="hashTxt">{sha}</span><button class="copy" type="button" data-copy-id="hashTxt">Copy</button></div></div>
    </div>
  </div>
</section>

<section class="band dark-2" id="install" aria-labelledby="inst-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="inst-h">Install in a minute.</h2><p class="lead">Pick your system. After the download, it's the same three commands everywhere.</p></div>
    <div class="install">
      <div class="rv">
        <div class="tabs" role="tablist" aria-label="Your system">
          <button class="tab" role="tab" id="t-mac" aria-controls="p-mac" aria-selected="true" type="button">macOS</button>
          <button class="tab" role="tab" id="t-linux" aria-controls="p-linux" aria-selected="false" tabindex="-1" type="button">Linux</button>
          <button class="tab" role="tab" id="t-chromeos" aria-controls="p-chromeos" aria-selected="false" tabindex="-1" type="button">Chromebook</button>
          <button class="tab" role="tab" id="t-wsl" aria-controls="p-wsl" aria-selected="false" tabindex="-1" type="button">Windows (WSL)</button>
        </div>
        <div class="panel" id="p-mac" role="tabpanel" aria-labelledby="t-mac"><ol class="osteps">
          <li><h3>Download newton.zip</h3><p>It lands in your Downloads folder.</p></li>
          <li><h3>Open Terminal and run the installer</h3><p>macOS includes Python 3. If it's missing, macOS offers to install developer tools.</p>{code("cd ~/Downloads\nunzip newton.zip\ncd newton\nsh install.sh")}</li>
          <li><h3>Open a new terminal</h3><p>Type a sentence and press Tab. zsh, the macOS default, works best.</p></li></ol></div>
        <div class="panel" id="p-linux" role="tabpanel" aria-labelledby="t-linux" hidden><ol class="osteps">
          <li><h3>Download newton.zip</h3><p>It lands in your Downloads folder.</p></li>
          <li><h3>Unzip and run the installer</h3><p>Works on any distro with <code>python3</code>. If something is missing, the installer prints the exact command for your system.</p>{code("cd ~/Downloads\nunzip newton.zip\ncd newton\nsh install.sh")}</li>
          <li><h3>Open a new terminal</h3><p>zsh, bash 4+ and fish are supported.</p></li></ol></div>
        <div class="panel" id="p-chromeos" role="tabpanel" aria-labelledby="t-chromeos" hidden><ol class="osteps">
          <li><h3>Turn on Linux</h3><p>Settings → About ChromeOS → Developers → Linux development environment → Turn on. Then open the Terminal app.</p></li>
          <li><h3>Download newton.zip, then move it into Linux files</h3><p>In the Files app, drag <code>newton.zip</code> from My files › Downloads into Linux files. That folder is <code>~</code> in the terminal.</p></li>
          <li><h3>Install what's missing, then Newton</h3><p>The first line is only needed if <code>unzip</code> or <code>python3</code> isn't there yet.</p>{code("sudo apt update &amp;&amp; sudo apt install -y unzip python3\ncd ~\nunzip newton.zip\ncd newton\nsh install.sh")}</li></ol></div>
        <div class="panel" id="p-wsl" role="tabpanel" aria-labelledby="t-wsl" hidden><ol class="osteps">
          <li><h3>Set up WSL</h3><p>In PowerShell as administrator, install Ubuntu, restart, then open the Ubuntu app.</p>{code("wsl --install")}</li>
          <li><h3>Download newton.zip, then install inside WSL</h3><p>Replace <code>YOU</code> with your Windows user name.</p>{code("cp /mnt/c/Users/YOU/Downloads/newton.zip ~\ncd ~\nsudo apt update &amp;&amp; sudo apt install -y unzip python3\nunzip newton.zip\ncd newton\nsh install.sh")}</li>
          <li><h3>Use it inside WSL</h3><p>Newton runs in the Linux shell, not in PowerShell.</p></li></ol></div>
      </div>
      <div class="side">
        <div class="card-d spot rv"><h3>Check your download (optional)</h3><p class="dim" style="font-size:.95rem">The result should match the SHA-256 checksum at the top of this page.</p>
          <div class="lbl-s" style="font-size:.85rem;color:var(--muted-d)">macOS</div>{code("shasum -a 256 ~/Downloads/newton.zip")}
          <div class="lbl-s" style="font-size:.85rem;color:var(--muted-d)">Linux, Chromebook, WSL</div>{code("sha256sum newton.zip")}</div>
        <div class="card-d spot rv" style="--d:.1s"><h3>Update or remove it</h3>{code("newton update\nnewton uninstall")}<p class="dim" style="font-size:.9rem">Download a newer zip, then run <code>newton update</code>. Updates are built and tested before they replace your copy. Uninstall only removes Newton's own lines from your shell config.</p></div>
      </div>
    </div>
  </div>
</section>

<section class="band light" aria-labelledby="req-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="req-h">What you need.</h2><p class="lead">Newton has no dependencies beyond Python.</p></div>
    <div class="reqs">
      <div class="req spot rv"><h3>A computer</h3><p>macOS, Linux, a Chromebook with Linux turned on, or Windows with WSL.</p></div>
      <div class="req spot rv" style="--d:.06s"><h3>Python 3.9 or newer</h3><p>Already on most Macs and Linux systems. The installer checks and tells you what to do if it's missing.</p></div>
      <div class="req spot rv" style="--d:.12s"><h3>A shell</h3><p>zsh, bash 4 or newer, or fish. macOS ships bash 3.2, so use zsh, the macOS default.</p></div>
      <div class="req spot rv" style="--d:.18s"><h3>An AI to talk to</h3><p>Claude or any OpenAI-compatible service with your own key, or Ollama running on your own computer for free. Setup asks you which.</p></div>
    </div>
  </div>
</section>

<section class="band white" aria-labelledby="rel-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="rel-h">Release notes.</h2></div>
    <div class="rel">
      <div class="rv"><b>{VER}</b><p><strong>Tab works in more places.</strong> Sentences that start with <code>newton</code>, such as <code>newton find big files</code>, now turn into commands with Tab. Newton also recognises many more everyday words, so shorter requests are caught. <kbd>Esc</kbd> then <kbd>N</kbd> forces Newton on any line.</p></div>
      <div class="rv"><b>2.2</b><p><strong>Installer and updates.</strong> One-file install into <code>~/.local/bin</code>, a marked block in your shell config, <code>newton update</code> from a zip, folder or link, <code>newton uninstall</code>, and install checks in <code>newton doctor</code>. Chromebook is supported.</p></div>
      <div class="rv"><b>2.1</b><p><strong>Plan mode, upgraded.</strong> Works better with small local models, preflight check for needed programs, undo, export as a script or Markdown, per-step timing, and a tab title and bell when a plan finishes.</p></div>
      <div class="rv"><b>2.0</b><p><strong>Plan mode, ask, chat, fix and commit.</strong> Checklists you approve one step at a time, questions answered in the terminal, failed commands explained and fixed, and commit messages written from your staged changes.</p></div>
      <div class="rv"><b>1.0</b><p><strong>Tab to command.</strong> Type a sentence, press Tab, get the command. Safety flags, secret redaction, and Claude, OpenAI-compatible and Ollama support for zsh, bash and fish.</p></div>
    </div>
  </div>
</section>

<section class="band dark" aria-labelledby="soon-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="soon-h">Coming next.</h2></div>
    <div class="soon-card rv"><div><strong>One-line install</strong><em>Soon</em><p class="lead" style="margin-top:6px">Install with a single command and update without downloading a file.</p></div></div>
  </div>
</section>
</main>

<footer class="footer"><div class="wrap">
  <div class="foot-grid">
    <div class="foot-brand"><a class="brand" href="index.html" aria-label="Newton home"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#nmark"/></svg>newton</a><p>Think it. Tab it. Done.</p></div>
    <div><h3>Product</h3><ul><li><a href="index.html#how">How it works</a></li><li><a href="index.html#try">Try it</a></li><li><a href="index.html#plan">Plan mode</a></li><li><a href="index.html#safety">Safety</a></li><li><a href="download.html">Download</a></li></ul></div>
    <div><h3>Company</h3><ul><li><a href="about.html">About</a></li><li><a href="team.html">Team</a></li><li><a href="invest.html">Invest</a></li><li><a href="donate.html">Donate</a></li></ul></div>
    <div><h3>Resources</h3><ul><li><a href="download.html">Download</a></li><li><a href="docs.html">Documentation</a></li><li><a href="index.html#video">Company video</a></li><li><a href="index.html#faq">FAQ</a></li></ul></div>
  </div>
  <div class="legal"><span>© 2026 Newton. Released under the MIT license.</span><span>Built for people who live in the terminal.</span></div>
</div></footer>
<script>
(function(){{
  "use strict";
  const $=(s,r)=>(r||document).querySelector(s), $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches, clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
  if("IntersectionObserver" in window&&!reduce){{document.documentElement.classList.add("js-rv");const io=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{e.target.classList.add("in");io.unobserve(e.target)}}}}),{{threshold:.12,rootMargin:"0px 0px -6% 0px"}});$$(".rv").forEach(el=>io.observe(el));}}
  const prog=$("#prog");function sc(){{const h=document.documentElement.scrollHeight-innerHeight;prog.style.transform="scaleX("+(h>0?clamp(scrollY/h,0,1):0)+")"}}addEventListener("scroll",sc,{{passive:true}});sc();
  $$(".spot").forEach(el=>el.addEventListener("pointermove",e=>{{const r=el.getBoundingClientRect();el.style.setProperty("--mx",(e.clientX-r.left)+"px");el.style.setProperty("--my",(e.clientY-r.top)+"px")}}));
  const tabs=$$('[role="tab"]');
  function select(t){{tabs.forEach(x=>{{const on=x===t;x.setAttribute("aria-selected",on);x.tabIndex=on?0:-1;$("#"+x.getAttribute("aria-controls")).hidden=!on}});try{{sessionStorage.setItem("os",t.id)}}catch(e){{}}}}
  tabs.forEach((t,i)=>{{t.addEventListener("click",()=>select(t));t.addEventListener("keydown",e=>{{const k={{ArrowRight:1,ArrowLeft:-1}}[e.key];if(!k)return;e.preventDefault();const n=tabs[(i+k+tabs.length)%tabs.length];select(n);n.focus()}})}});
  const p=(navigator.userAgent||"")+" "+(navigator.platform||"");
  const det=/CrOS/i.test(p)?["t-chromeos","Chromebook"]:/Mac/i.test(p)?["t-mac","macOS"]:/Win/i.test(p)?["t-wsl","Windows"]:/Linux/i.test(p)?["t-linux","Linux"]:["t-mac","macOS"];
  let saved=null;try{{saved=sessionStorage.getItem("os")}}catch(e){{}}
  const st=document.getElementById(saved||det[0]);if(st)select(st);
  $("#dlNote").textContent="{kb} KB · looks like you're on "+det[1]+" · the same file works on every system";
  async function copy(btn,text,src){{let ok=false;try{{await navigator.clipboard.writeText(text);ok=true}}catch(e){{try{{const r=document.createRange();r.selectNodeContents(src);const s=getSelection();s.removeAllRanges();s.addRange(r);ok=document.execCommand("copy")}}catch(e2){{}}}}
    btn.textContent=ok?"Copied":"Select and copy";btn.classList.toggle("done",ok);setTimeout(()=>{{btn.textContent="Copy";btn.classList.remove("done")}},1800)}}
  $$("[data-copy]").forEach(b=>b.addEventListener("click",()=>{{const pre=b.parentElement.querySelector("pre");copy(b,pre.textContent.trim(),pre)}}));
  $$("[data-copy-id]").forEach(b=>b.addEventListener("click",()=>{{const el=document.getElementById(b.dataset.copyId);copy(b,el.textContent.trim(),el)}}));
  const nav=$("#nav"),mb=$("#menuBtn");mb.addEventListener("click",()=>{{const o=nav.classList.toggle("open");mb.setAttribute("aria-expanded",o)}});
  $$("#menu a").forEach(a=>a.addEventListener("click",()=>{{nav.classList.remove("open");mb.setAttribute("aria-expanded","false")}}));
}})();
</script></body></html>'''
open('download.html','w').write(html); print(len(html)//1024,'KB', sha[:12])
