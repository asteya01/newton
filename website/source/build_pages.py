import re, html
import parts
dl=open('download.html').read()
head=dl[:dl.index('</style>')]
rest=dl[dl.index('</style>'):]
svg=re.search(r'<svg width="0".*?</svg>',rest,re.S).group(0)
nav_tpl=re.search(r'<header class="nav".*?</header>',rest,re.S).group(0).replace(' class="cur" aria-current="page"','').replace('href="#get">Download','href="download.html">Download')
foot=re.search(r'<footer class="footer">.*?</footer>',rest,re.S).group(0)
EXTRA=parts.CSS+'''
.pg-hero{position:relative;overflow:hidden;isolation:isolate;padding-block:calc(var(--nav-h) + 100px) 84px}
.pg-hero h1{font-size:clamp(3rem,7.2vw,6rem);line-height:.96;letter-spacing:-.055em;margin-top:24px;max-width:12em}
.pg-hero .lead{margin-top:24px}
.pg-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:34px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.cards.two{grid-template-columns:repeat(2,1fr)}
.cd{background:#fff;border:1px solid var(--line);border-radius:24px;padding:32px;display:grid;gap:10px;align-content:start;transition:transform .3s cubic-bezier(.2,.7,.2,1),box-shadow .3s}
.cd:hover{transform:translateY(-4px);box-shadow:0 26px 50px -28px rgba(10,15,26,.35)}
.cd h3{font-size:1.45rem;line-height:1.12}.cd p{color:var(--muted)}
.cd code,.prose code{font-size:.88em;background:rgba(6,122,85,.09);color:var(--leaf);padding:.1em .4em;border-radius:5px}
.cd .go{margin-top:8px}
.cd.d{background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border-color:rgba(255,255,255,.12)}
.cd.d p{color:var(--muted-d)}
.cd.d code{background:rgba(255,255,255,.08);color:var(--mint)}
.prose{max-width:760px;display:grid;gap:18px;font-size:1.1rem;color:var(--muted)}
.prose strong{color:var(--text)}
.dark .prose,.dark-2 .prose{color:var(--muted-d)}.dark .prose strong{color:#fff}
.fine{font-size:.88rem;color:var(--muted-d);max-width:70ch}
.band.light .fine,.band.white .fine{color:var(--muted)}
.cta-row{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;border:1px dashed rgba(255,255,255,.22);border-radius:24px;padding:32px 36px}
.cta-row h3{font-size:1.7rem}.cta-row p{color:var(--muted-d);margin-top:6px}
.phone{display:inline-flex;align-items:center;gap:12px;font:600 1.5rem var(--f-mono);letter-spacing:-.01em;color:var(--mint);text-decoration:none}
.phone:hover{text-decoration:underline}
.btn-light{background:#fff;color:#07130E}.btn-light:hover{transform:translateY(-2px)}
/* docs */
.docs{display:grid;grid-template-columns:240px minmax(0,1fr);gap:clamp(28px,5vw,72px);align-items:start}
.toc{position:sticky;top:96px;display:grid;gap:2px;font-size:.95rem}
.toc a{display:block;padding:8px 14px;border-left:2px solid var(--line);color:var(--muted);text-decoration:none;transition:color .15s,border-color .15s,background .15s}
.toc a:hover{color:var(--text)}.toc a.on{color:var(--leaf);border-color:var(--leaf);background:rgba(6,122,85,.06);font-weight:600}
.doc{display:grid;gap:64px;min-width:0}
.doc section{display:grid;gap:18px;min-width:0}
.doc h2{font-size:clamp(1.9rem,3.4vw,2.7rem);line-height:1.05}
.doc h3{font-size:1.3rem;margin-top:10px}
.doc p,.doc li{color:var(--muted);max-width:70ch}
.doc ul{display:grid;gap:8px;padding-left:1.2em;margin:0}
.doc strong{color:var(--text)}
.doc code{font-size:.88em;background:rgba(6,122,85,.09);color:var(--leaf);padding:.1em .4em;border-radius:5px}
.doc kbd{background:#EEF2F7;color:#1B2735;border-color:#C9D3E0}
.doc .code{background:#070C12}.doc .code code{background:none;color:#DCE7EE;padding:0;font-size:inherit}
.doc .code pre{font-size:.84rem}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:16px;background:#fff}
.tbl table{border-collapse:collapse;width:100%;font-size:.96rem}
.tbl th,.tbl td{text-align:left;padding:13px 18px;border-top:1px solid var(--line);vertical-align:top}
.tbl tr:first-child th,.tbl tr:first-child td{border-top:0}
.tbl th{background:#F3F6FA;font-weight:600;color:var(--text)}
.tbl td:first-child{white-space:nowrap}
.tbl td{color:var(--muted)}
@media (max-width:960px){.docs{grid-template-columns:1fr}.toc{position:static;grid-auto-flow:column;overflow-x:auto;padding-bottom:6px}.toc a{white-space:nowrap;border-left:0;border-bottom:2px solid var(--line)}.cards,.cards.two{grid-template-columns:1fr}}
'''
SCRIPT='''<script>
(function(){
  "use strict";
  const $=(s,r)=>(r||document).querySelector(s), $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches, clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
  if("IntersectionObserver" in window&&!reduce){document.documentElement.classList.add("js-rv");const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}}),{threshold:.1,rootMargin:"0px 0px -6% 0px"});$$(".rv").forEach(el=>io.observe(el));}
  const prog=$("#prog");function sc(){const h=document.documentElement.scrollHeight-innerHeight;prog.style.transform="scaleX("+(h>0?clamp(scrollY/h,0,1):0)+")"}addEventListener("scroll",sc,{passive:true});sc();
  $$(".spot").forEach(el=>el.addEventListener("pointermove",e=>{const r=el.getBoundingClientRect();el.style.setProperty("--mx",(e.clientX-r.left)+"px");el.style.setProperty("--my",(e.clientY-r.top)+"px")}));
  async function copy(btn,text,src){let ok=false;try{await navigator.clipboard.writeText(text);ok=true}catch(e){try{const r=document.createRange();r.selectNodeContents(src);const s=getSelection();s.removeAllRanges();s.addRange(r);ok=document.execCommand("copy")}catch(e2){}}
    btn.textContent=ok?"Copied":"Select and copy";btn.classList.toggle("done",ok);setTimeout(()=>{btn.textContent="Copy";btn.classList.remove("done")},1800)}
  $$("[data-copy]").forEach(b=>b.addEventListener("click",()=>{const pre=b.parentElement.querySelector("pre");copy(b,pre.textContent.trim(),pre)}));
  const nav=$("#nav"),mb=$("#menuBtn");mb.addEventListener("click",()=>{const o=nav.classList.toggle("open");mb.setAttribute("aria-expanded",o)});
  $$("#menu a").forEach(a=>a.addEventListener("click",()=>{nav.classList.remove("open");mb.setAttribute("aria-expanded","false")}));
  $$(".show-phone").forEach(sb=>sb.addEventListener("click",()=>{const d=["279","267","6299"],a=document.createElement("a");a.className="phone";a.href="tel:+1"+d.join("");a.textContent="+1 "+d.join(" ");const box=sb.parentElement;box.textContent="";box.appendChild(a)}));
  const toc=$$(".toc a");
  if(toc.length&&"IntersectionObserver" in window){const map=new Map(toc.map(a=>[a.getAttribute("href").slice(1),a]));const io2=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){toc.forEach(a=>a.classList.remove("on"));const a=map.get(e.target.id);if(a)a.classList.add("on")}}),{rootMargin:"-20% 0px -70% 0px"});map.forEach((a,id)=>{const s=document.getElementById(id);if(s)io2.observe(s)});}
})();
</script>'''
def page(fname,title,desc,main,tail=''):
    h=head.replace('<title>Download Newton 2.2.0</title>',f'<title>{title}</title>')
    h=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="{desc}">',h)
    out=h+EXTRA+'</style></head><body>\n'+svg+'\n<a class="skip" href="#main">Skip to content</a><div id="prog" aria-hidden="true"></div>\n'+nav_tpl+'\n<main id="main">'+main+'</main>\n'+foot+'\n'+tail+SCRIPT+'</body></html>'
    open(fname,'w').write(out); print(fname,len(out)//1024,'KB')
def hero(kicker,h1,lead,actions=""):
    return f'<section class="pg-hero" aria-labelledby="h1"><div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div><div class="floor" aria-hidden="true"></div><div class="wrap"><span class="kicker"><i></i>{kicker}</span><h1 id="h1">{h1}</h1><p class="lead">{lead}</p>{actions}</div></section>'
def code(t): return '<div class="code"><pre><code>'+t+'</code></pre><button class="copy" type="button" data-copy>Copy</button></div>'
phone_btn='<div><button class="btn btn-primary show-phone" type="button">Click to see contact number</button></div>'

# ---------------- ABOUT ----------------
about=hero("About","Built for people who live in the terminal.","Newton makes the command line feel effortless. You say what you want. It writes the command. You stay in control.",
 '<div class="pg-actions"><a class="btn btn-primary" href="download.html">Download Newton</a><a class="btn btn-ghost" href="team.html">Meet the team</a></div>')
about+='''
<section class="band light" aria-labelledby="why-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="why-h">Why Newton exists.</h2></div>
  <div class="prose rv"><p>You know what you want to do. You just don't remember whether it's <code>tar -xzvf</code> or <code>-zxvf</code>, which <code>find</code> flag means bigger than, or how <code>lsof</code> takes a port.</p>
  <p>So you open a browser, search, skim a forum thread, copy, paste and edit. <strong>Newton turns that whole loop into one key.</strong> Type a sentence, press Tab, and the exact command appears in your prompt, ready for you to read, change and run.</p></div>
</div></section>
<section class="band dark" aria-labelledby="how-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="how-h">How we build it.</h2><p class="lead">A tool that touches your terminal has to earn trust. These are the rules we build by.</p></div>
  <div class="cards two">
    <div class="cd d spot rv"><h3>Newton writes. You decide.</h3><p>Nothing runs until you press Enter. Local safety rules flag dangerous commands whatever the AI says, and destructive steps always ask first.</p></div>
    <div class="cd d spot rv" style="--d:.06s"><h3>Private by default</h3><p>Secrets are scrubbed before anything is sent. There is no telemetry, and with Ollama nothing leaves your computer.</p></div>
    <div class="cd d spot rv" style="--d:.12s"><h3>Tested in real shells</h3><p>The test suite opens real zsh, bash and fish sessions, types a sentence, presses Tab, and checks that normal completion is untouched.</p></div>
    <div class="cd d spot rv" style="--d:.18s"><h3>Works where you work</h3><p>One file, Python 3.9 or newer, no admin rights. macOS, Linux, Chromebook and Windows through WSL.</p></div>
  </div>
</div></section>
<section class="band white" aria-labelledby="free-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="free-h">Free and open.</h2><p class="lead">Newton is released under the MIT license. Use your own AI: Claude or any OpenAI-compatible service with your own key, or Ollama on your computer for free.</p></div>
  <div class="pg-actions rv"><a class="btn btn-ink" href="download.html">Download Newton</a><a class="btn btn-ghost" style="color:var(--text);border-color:var(--line);background:#fff" href="docs.html">Read the docs</a></div>
</div></section>'''
page('about.html','About · Newton','Why Newton exists, how we build it, and what we believe about the command line.',about)

# ---------------- DOCS ----------------
def tbl(rows,head=None):
    h='<tr>'+''.join(f'<th>{c}</th>' for c in head)+'</tr>' if head else ''
    return '<div class="tbl"><table>'+h+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in r)+'</tr>' for r in rows)+'</table></div>'
docs_body=f'''
<section id="start"><h2>Quick start</h2><p>Newton is one file that needs Python 3.9 or newer. No pip, no virtual environment, no admin rights.</p>
{code("cd ~/Downloads\nunzip newton.zip\ncd newton\nsh install.sh")}
<p>The installer puts <code>newton</code> in <code>~/.local/bin</code>, makes sure that folder is on your <code>PATH</code>, then walks you through choosing an AI and turning on Tab. Open a new terminal when it finishes, type a sentence and press <kbd>Tab</kbd>.</p>
<p>Need system-specific steps (Chromebook, WSL)? See the <a href="download.html#install" style="color:var(--leaf)">download page</a>.</p></section>

<section id="keys"><h2>Keys</h2>
{tbl([["<kbd>Tab</kbd>","Plain English → command. On a normal command, ordinary completion."],["<kbd>Tab</kbd> again","Cycle through alternative commands."],["<kbd>Shift</kbd>+<kbd>Tab</kbd>","Undo: put your original words back."],["<kbd>Alt</kbd>+<kbd>N</kbd>","Force Newton on the current line, whatever it looks like."],["<code># …</code>","Lines starting with <code>#</code> always go to Newton."]],["Key","What it does"])}
<h3>How Newton decides what's a sentence</h3>
<p>A line goes to Newton if it starts with <code>#</code>, or if it has at least three words, no shell syntax and no flags, and either its first word isn't a real command or it reads like English. Anything else gets your normal Tab completion. To fire only on <code>#</code> lines, run <code>newton config trigger prefix</code>.</p></section>

<section id="plan"><h2>Plan mode</h2>
<p>For anything bigger than one command, give Newton a goal. It drafts a checklist, then walks you through it. You stay in control of every step.</p>
{code('newton plan "deploy this app to a VPS"   # draft, review, run\nnewton plan --dry-run "…"                # just show the plan\nnewton plan -y "…"                       # auto-run safe steps (danger steps still ask)\nnewton status                            # the checklist for your active plan\nnewton plans [list|show|rm] [id]         # saved plans\nnewton resume                            # continue where you stopped\nnewton plans undo [id]                   # roll back finished steps, newest first\nnewton plans export [id] [-o FILE] [--md]  # a runnable script or markdown checklist')}
<h3>One key per step</h3>
<p><kbd>⏎</kbd> runs it, <kbd>e</kbd> edits it, <kbd>s</kbd> skips it, <kbd>?</kbd> explains it, <kbd>a</kbd> asks a question about it, <kbd>r</kbd> revises the plan, <kbd>q</kbd> pauses.</p>
<ul><li><strong>State carries over.</strong> <code>cd</code> and <code>export</code> in one step apply to the next.</li>
<li><strong>Failures get fixed.</strong> Newton reads the error, proposes a fix and retries. You can run it, edit it, retry as-is, skip or ask.</li>
<li><strong>Dangerous steps need a deliberate <kbd>y</kbd>.</strong> Even <code>--yes</code> only auto-runs safe steps.</li>
<li><strong>Pause and resume.</strong> Press <kbd>q</kbd> or Ctrl+C and the plan is saved. <code>newton resume</code> continues from the same step.</li>
<li><strong>Preflight check.</strong> Before anything runs, the plan lists the programs it needs with a ✓ or ✗ for what's installed.</li>
<li><strong>Undo and export.</strong> <code>newton plans undo</code> reverses steps newest first and asks before each. <code>newton plans export -o setup.sh</code> makes a runnable script; <code>--md</code> gives a checklist.</li></ul>
<p>Put <code>$(newton prompt)</code> in your prompt to keep the active plan visible.</p></section>

<section id="commands"><h2>Commands</h2>
{tbl([["<code>newton ask &lt;question&gt;</code>","Streams an answer in your terminal. Pipe anything in (<code>make 2&gt;&amp;1 | newton ask why did this fail</code>) or attach files with <code>-f</code>."],["<code>newton chat</code>","A conversation with your shell attached. <code>!cmd</code> runs a command and shows Newton the output, <code>/run</code> executes the last code block."],["<code>newton fix</code>","Looks at your last command, re-runs it to see the real error, explains what went wrong and offers a fix. Destructive commands are never re-run."],["<code>newton commit</code>","Reads your staged diff and writes a clear commit message. You approve it before anything is committed."],["<code>newton explain '…'</code>","A flag-by-flag breakdown of a command."],["<code>newton suggest -c \"…\"</code>","Print a suggestion and copy it to the clipboard. <code>--json</code> gives full JSON."],["<code>newton history</code>","What you've asked recently."],["<code>newton doctor</code>","Checks your key, connection, shell integration, install and PATH."]],["Command","What it does"])}
<p><code>newton fix</code> needs the shell integration, which records your last command and exit status in a private file. For better plans, use a stronger model for heavy work: <code>newton config smart_model claude-sonnet-5-5</code>.</p></section>

<section id="providers"><h2>Providers</h2>
{tbl([["<strong>Claude</strong> (recommended)","API key from console.anthropic.com, or <code>ANTHROPIC_API_KEY</code>","<code>claude-haiku-5-5</code>"],["OpenAI-compatible","Any <code>/chat/completions</code> endpoint plus key (<code>OPENAI_API_KEY</code>)","<code>gpt-4o-mini</code>"],["Ollama","Local and offline. <code>ollama pull llama3.1</code>","<code>llama3.1</code>"]],["Provider","Setup","Default model"])}
{code("ollama pull llama3.1\nnewton config provider ollama\nnewton config model llama3.1")}
<p>Every setting can also be overridden per shell with <code>NEWTON_PROVIDER</code>, <code>NEWTON_MODEL</code>, <code>NEWTON_API_KEY</code> and <code>NEWTON_BASE_URL</code>.</p></section>

<section id="settings"><h2>Settings</h2>
<p>Run <code>newton config</code> to see settings and <code>newton config &lt;key&gt; &lt;value&gt;</code> to change one.</p>
{tbl([["<code>provider</code>","<code>anthropic</code>","<code>anthropic</code>, <code>openai</code> or <code>ollama</code>"],["<code>model</code>","provider default","Model name"],["<code>alternatives</code>","<code>2</code>","Extra commands to cycle with Tab (0–5)"],["<code>share_file_names</code>","<code>true</code>","Send top-level file names in the current folder for better answers"],["<code>cache</code>","<code>true</code>","Answer repeat requests instantly from the local cache"],["<code>trigger</code>","<code>smart</code>","<code>smart</code> or <code>prefix</code> (only <code>#</code> lines)"],["<code>timeout</code>","<code>20</code>","Seconds to wait for the AI on Tab suggestions"],["<code>smart_model</code>","same as model","Stronger model for plan, ask, chat, fix and commit"],["<code>plan_timeout</code>","<code>90</code>","Seconds to wait while drafting a plan"],["<code>plan_max_steps</code>","<code>15</code>","Upper limit on steps in a plan"],["<code>share_output</code>","<code>true</code>","Send the redacted output of a failed step to the AI so it can diagnose it"]],["Setting","Default","Meaning"])}
<p>Config lives in <code>~/.config/newton/config.json</code>. Cache and history are in <code>~/.cache/newton/</code>, saved plans in <code>~/.local/share/newton/plans/</code>. All three folders are owner-only.</p></section>

<section id="update"><h2>Update and uninstall</h2>
{code("newton update                      # finds the newest newton*.zip in ~/Downloads\nnewton update ~/Downloads/newton.zip\nnewton update https://…/newton.zip # https only")}
<p>It shows the version change, asks first, builds and tests the new copy, and only then replaces the old one. A broken download can never replace a working install. Your settings, key and saved plans are untouched.</p>
{code("newton uninstall            # removes the program and Newton's lines in your shell config\nnewton uninstall --purge    # also deletes your settings, API key, history and saved plans")}
<h3>Other install options</h3>
{code("sh install.sh --no-setup        # skip the guided setup\nsh install.sh --no-path         # don't touch shell config files\nsh install.sh --bin-dir ~/bin   # install somewhere else")}</section>

<section id="privacy"><h2>Privacy</h2>
<p>Each Tab request sends only your description plus a short environment summary: OS, shell, current folder path, project type, installed tool names, and top-level file names (which you can turn off). Tab suggestions never send file contents, environment variables, shell history or your previous commands.</p>
<ul><li><strong>Plan mode</strong> sends your goal, your answers to its questions and, if a step fails, the last lines of that step's output. Turn that off with <code>newton config share_output false</code>.</li>
<li><strong><code>ask</code> and <code>chat</code></strong> send what you type or pipe in, and files you attach. Files that look like secrets (<code>.env</code>, keys, credentials) are refused.</li>
<li><strong><code>fix</code></strong> sends your last command and its output. <strong><code>commit</code></strong> sends your staged diff.</li></ul>
<p>Everything sent passes through a redactor first: API keys, tokens, passwords and private keys are replaced with placeholders. With Ollama nothing leaves your machine. Newton has no telemetry.</p></section>

<section id="help"><h2>Troubleshooting</h2>
<ul><li><strong>Tab does normal completion on my sentence.</strong> Start the line with <code>#</code>, or press <kbd>Alt</kbd>+<kbd>N</kbd>.</li>
<li><strong>Tab stopped completing with oh-my-zsh or fzf-tab.</strong> Load Newton after other plugins (put the <code>eval</code> line last).</li>
<li><strong>macOS bash.</strong> The built-in bash 3.2 is too old. Use zsh (the macOS default) or <code>brew install bash</code>.</li>
<li><strong><code>newton: command not found</code> after installing.</strong> Open a new terminal. If it persists, run <code>~/.local/bin/newton doctor</code>.</li>
<li><strong>Something else is shadowing Newton.</strong> <code>newton doctor</code> warns when your shell finds a different <code>newton</code> first, such as an old pip install. Remove the other copy.</li>
<li><strong>Anything else:</strong> run <code>newton doctor</code>.</li></ul></section>
'''
toc=[("start","Quick start"),("keys","Keys"),("plan","Plan mode"),("commands","Commands"),("providers","Providers"),("settings","Settings"),("update","Update and uninstall"),("privacy","Privacy"),("help","Troubleshooting")]
docs=hero("Documentation","Everything Newton can do.","Install it, learn the keys, and get the most out of plan mode.")
docs+='<section class="band light"><div class="wrap docs"><nav class="toc" aria-label="On this page">'+''.join(f'<a href="#{i}">{t}</a>' for i,t in toc)+'</nav><div class="doc">'+docs_body+'</div></div></section>'
page('docs.html','Documentation · Newton','Newton documentation: install, keys, plan mode, commands, providers, settings and privacy.',docs)

# ---------------- INVEST ----------------
inv=hero("Invest","Back the way people use the terminal.","Newton is a free, privacy-first tool that turns plain English into shell commands. We'd like to talk to people who want to help it grow.",
 '<div class="pg-actions"><div>'+'<button class="btn btn-primary show-phone" type="button">Click to see contact number</button></div><a class="btn btn-ghost" href="download.html">Try Newton first</a></div>')
inv+='''
<section class="band light" aria-labelledby="bk-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="bk-h">What you'd be backing.</h2><p class="lead">A product you can try today, built on a simple idea: nobody should have to memorize command flags.</p></div>
  <div class="cards">
    <div class="cd spot rv"><h3>A working product</h3><p>Tab to command, plan mode, ask, chat, fix and commit. Version 2.2 is available to download and install in about a minute.</p></div>
    <div class="cd spot rv" style="--d:.06s"><h3>Trust built in</h3><p>Nothing runs without the user's Enter. Local safety rules, secret redaction and no telemetry, with a fully offline option.</p></div>
    <div class="cd spot rv" style="--d:.12s"><h3>Wide reach</h3><p>zsh, bash and fish on macOS, Linux and Chromebook, plus Windows through WSL. One file, no admin rights.</p></div>
  </div>
</div></section>
<section class="band dark" aria-labelledby="talk-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="talk-h">Let's talk.</h2><p class="lead">Interested in investing or partnering? Get in touch and we'll share more about where Newton is going.</p></div>
  <div class="cta-row rv"><div><h3>Contact the founder</h3><p>Phone numbers stay hidden until you ask for them.</p></div><div><button class="btn btn-primary show-phone" type="button">Click to see contact number</button></div></div>
  <p class="fine" style="margin-top:28px">This page is for information only. It is not an offer to sell, or a solicitation of an offer to buy, any securities.</p>
</div></section>'''
inv=inv.replace('<div class="pg-actions"><div><button class="btn btn-primary show-phone" type="button">Click to see contact number</button></div><a class="btn btn-ghost" href="download.html">Try Newton first</a></div>','<div class="pg-actions"><a class="btn btn-primary" href="#talk-h">Get in touch</a><a class="btn btn-ghost" href="download.html">Try Newton first</a></div>')
page('invest.html','Invest · Newton','Interested in investing in or partnering with Newton? Get in touch.',inv)

# ---------------- DONATE ----------------
don=hero("Support","Help Newton keep getting better.","Newton is free and open. You can help by using it, sharing it, improving it, or backing its development.",
 '<div class="pg-actions"><a class="btn btn-primary" href="#ways">Ways to help</a><a class="btn btn-ghost" href="download.html">Download Newton</a></div>')
don+='''
<section class="band light" id="ways" aria-labelledby="ways-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="ways-h">Ways to help.</h2></div>
  <div class="cards two">
    <div class="cd spot rv"><h3>Follow the code</h3><p>Follow the project on GitHub and watch for new releases.</p><div class="go"><a class="btn btn-ink btn-sm" href="https://github.com/asteya01" rel="noopener">github.com/asteya01</a></div></div>
    <div class="cd spot rv" style="--d:.06s"><h3>Tell someone</h3><p>Know a developer who looks up the same flags every week? Send them to Newton. It's the best help there is.</p><div class="go"><a class="btn btn-ink btn-sm" href="download.html">Share the download page</a></div></div>
    <div class="cd spot rv" style="--d:.12s"><h3>Send feedback</h3><p>Tell us what worked, what didn't, and which commands Newton got wrong. Every report makes it better.</p><div class="go"><a class="btn btn-ink btn-sm" href="team.html">Contact us</a></div></div>
    <div class="cd spot rv" style="--d:.18s"><h3>Donate</h3><p>Donations to fund development are being set up. Ask us and we'll tell you the best way to give.</p><div class="go" id="giveBox"><button class="btn btn-ink btn-sm show-phone" type="button">Click to see contact number</button></div></div>
  </div>
</div></section>
<section class="band dark" aria-labelledby="why-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="why-h">Where support goes.</h2><p class="lead">Newton is free to use. Support helps us spend more time on:</p></div>
  <div class="cards">
    <div class="cd d spot rv"><h3>Better commands</h3><p>Testing and improving accuracy across models, including small local ones.</p></div>
    <div class="cd d spot rv" style="--d:.06s"><h3>More systems</h3><p>Smoother installs and wider shell and platform support.</p></div>
    <div class="cd d spot rv" style="--d:.12s"><h3>Safer defaults</h3><p>Stronger checks and clearer warnings before anything risky runs.</p></div>
  </div>
</div></section>'''
page('donate.html','Support · Newton','Ways to support Newton: follow the project, share it, send feedback or ask about donating.',don)
