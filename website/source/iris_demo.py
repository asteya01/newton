CSS = r'''
/* ---- Iris demo ---- */
.iris-logo{display:inline-block;width:28px;height:28px;border-radius:50%;background:conic-gradient(from 210deg,#ff7a8a,#ffc46b,#c8f06b,#5fe0b0,#6db8ff,#b49bff,#ff7a8a);position:relative;flex:none}
.iris-logo::after{content:"";position:absolute;inset:26%;border-radius:50%;background:#fff;box-shadow:0 0 0 1px rgba(0,0,0,.04)}
.iw{max-width:1040px;margin:0 auto;border-radius:22px;overflow:hidden;background:#F7F9FB;color:#0E1621;border:1px solid rgba(255,255,255,.14);box-shadow:0 50px 120px -40px rgba(0,0,0,.85),0 0 120px -50px rgba(61,245,167,.35);font-family:var(--f-sans);text-align:left}
.iw-bar{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#fff;border-bottom:1px solid #E3E9F0}
.iw-bar b{font-weight:600;font-size:.98rem;letter-spacing:-.01em}
.iw-bar .dots{display:flex;gap:6px;margin-right:6px}.iw-bar .dots i{width:11px;height:11px;border-radius:50%;background:#E3E9F0}
.iw-bar .cwd{margin-left:auto;font:500 .78rem var(--f-mono);color:#5A6678;border:1px solid #E3E9F0;border-radius:999px;padding:4px 12px;background:#F7F9FB}
.iw-main{display:grid;grid-template-columns:230px minmax(0,1fr);min-height:520px}
.iw-side{background:#EEF2F6;border-right:1px solid #E3E9F0;padding:16px 12px;display:flex;flex-direction:column;gap:14px}
.iw-brand{display:flex;align-items:center;gap:10px;font-weight:600;padding:2px 6px}
.iw-new{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #DDE4EC;border-radius:12px;padding:10px 12px;font:500 .92rem var(--f-sans);color:#0E1621;cursor:pointer;text-align:left}
.iw-new:hover{border-color:#B7C3D2}
.iw-side small{font:600 .72rem var(--f-sans);color:#7A8697;padding:0 8px}
.iw-recent{display:grid;gap:2px}
.iw-recent div{padding:8px 10px;border-radius:9px;font-size:.88rem;color:#43506A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.iw-recent div.on{background:#fff;color:#0E1621;box-shadow:0 1px 0 #E3E9F0}
.iw-foot{margin-top:auto;font-size:.8rem;color:#5A6678;padding:0 6px;line-height:1.4}
.iw-chat{display:flex;flex-direction:column;min-width:0;background:#F7F9FB}
.iw-scroll{flex:1;overflow:auto;padding:22px 24px 8px;display:flex;flex-direction:column;gap:14px;max-height:520px;min-height:420px}
.iw-empty{margin:auto;text-align:center;max-width:560px}
.iw-empty .iris-logo{width:56px;height:56px}
.iw-empty h3{font-size:1.7rem;letter-spacing:-.03em;margin:16px 0 8px;color:#0E1621}
.iw-empty p{color:#566274;margin:0 auto 20px;max-width:44ch;font-size:.98rem;line-height:1.5}
.iw-sugs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.iw-sug{background:#fff;border:1px solid #DDE4EC;border-radius:14px;padding:14px 12px;text-align:center;cursor:pointer;font:inherit;color:#0E1621;transition:border-color .15s,transform .15s,box-shadow .15s}
.iw-sug:hover{border-color:#067A55;transform:translateY(-2px);box-shadow:0 10px 24px -14px rgba(6,122,85,.5)}
.iw-sug b{display:block;font-weight:600;font-size:.92rem}.iw-sug span{display:block;color:#5A6678;font-size:.8rem;margin-top:3px}
.iw-user{align-self:flex-end;background:#E6ECF3;border-radius:16px;padding:10px 16px;max-width:80%;font-size:.98rem}
.iw-ai{display:grid;grid-template-columns:28px minmax(0,1fr);gap:12px;align-items:start}
.iw-ai .txt{font-size:.98rem;line-height:1.55;color:#0E1621}
.iw-ai .txt p{margin:0 0 8px}.iw-ai .txt ul{margin:0 0 8px;padding-left:20px}
.iw-ai code,.iw-tool code{font:500 .86em var(--f-mono);background:#EAEFF5;border:1px solid #DDE4EC;border-radius:6px;padding:1px 6px}
.iw-tool{margin-left:40px;background:#fff;border:1px solid #DDE4EC;border-radius:14px;overflow:hidden;animation:iwin .25s ease-out}
.iw-th{display:flex;align-items:center;gap:12px;padding:10px 14px}
.iw-th .ic{width:28px;height:28px;border-radius:8px;background:#EEF2F6;display:grid;place-items:center;font:600 .8rem var(--f-mono);color:#566274}
.iw-th .cm{min-width:0;flex:1}.iw-th .cm b{display:block;font:500 .86rem var(--f-mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.iw-th .cm span{font-size:.78rem;color:#5A6678}
.chip{font:600 .72rem var(--f-sans);border-radius:999px;padding:3px 10px;border:1px solid}
.chip.run{color:#5A6678;border-color:#DDE4EC;background:#F7F9FB}.chip.ok{color:#067A55;border-color:#BFE6D6;background:#F0FBF6}
.chip.wait{color:#9A5B00;border-color:#F2D49B;background:#FFF9EC}.chip.no{color:#B4372B;border-color:#F3C3BD;background:#FFF4F2}
.iw-out{border-top:1px solid #E3E9F0;background:#F3F6FA;padding:10px 14px;font:500 .8rem/1.55 var(--f-mono);color:#33415A;white-space:pre-wrap;overflow-x:auto}
.iw-appr{border-top:1px solid #F2D49B;background:#FFFBF1;padding:14px;font-size:.92rem}
.iw-appr .row{display:flex;gap:10px;margin-top:10px}
.iw-appr button{font:600 .9rem var(--f-sans);border-radius:10px;padding:9px 18px;border:1px solid #DDE4EC;background:#fff;color:#0E1621;cursor:pointer}
.iw-appr button.go{background:#067A55;border-color:#067A55;color:#fff}
.iw-appr button:focus-visible,.iw-sug:focus-visible,.iw-new:focus-visible{outline:3px solid #6FF0A0;outline-offset:2px}
.iw-dots{display:inline-flex;gap:5px;padding:8px 0}.iw-dots i{width:7px;height:7px;border-radius:50%;background:#9AA6B6;animation:iwd 1s infinite}.iw-dots i:nth-child(2){animation-delay:.15s}.iw-dots i:nth-child(3){animation-delay:.3s}
@keyframes iwd{0%,80%,100%{opacity:.25}40%{opacity:1}}@keyframes iwin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.iw-comp{margin:8px 24px 14px;background:#fff;border:1px solid #DDE4EC;border-radius:16px;padding:12px 16px;color:#7A8697;font-size:.92rem;display:flex;justify-content:space-between;gap:12px}
.iw-comp i{font-style:normal;font-size:.78rem}
.iw-note{max-width:1040px;margin:14px auto 0;color:var(--muted-d);font-size:.92rem;text-align:center}
.iw-note b{color:#fff}
.iris-feat{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;max-width:1040px;margin:34px auto 0}
.iris-feat div{border:1px solid var(--line-d);border-radius:20px;padding:24px;background:rgba(255,255,255,.03)}
.iris-feat h3{font-size:1.15rem;margin-bottom:8px;color:#fff}.iris-feat p{color:var(--muted-d);margin:0;font-size:.98rem}
.iris-cta{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:28px}
@media (max-width:860px){.iw-main{grid-template-columns:1fr}.iw-side{display:none}.iw-sugs{grid-template-columns:1fr}.iris-feat{grid-template-columns:1fr}.iw-scroll{padding:16px}.iw-tool{margin-left:0}}
@media (prefers-reduced-motion:reduce){.iw-tool{animation:none}.iw-dots i{animation:none;opacity:.6}}
'''

DEMO = r'''<div class="iw" id="irisDemo" role="region" aria-label="Interactive demo of the Iris chat app, using sample output">
  <div class="iw-bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><b>Iris</b><span class="cwd">~/projects/api</span></div>
  <div class="iw-main">
    <aside class="iw-side" aria-hidden="true">
      <div class="iw-brand"><span class="iris-logo"></span>Iris</div>
      <button class="iw-new" type="button" id="iwNew" aria-label="New chat">＋ New chat</button>
      <div><small>Recent</small><div class="iw-recent" id="iwRecent"></div></div>
      <div class="iw-foot">Ask before every command: off<br>Your AI: Ollama · llama3.1</div>
    </aside>
    <div class="iw-chat">
      <div class="iw-scroll" id="iwScroll" aria-live="polite"></div>
      <div class="iw-comp" aria-hidden="true"><span>Ask Iris to do something on this computer…</span><i>Demo: pick a suggestion above</i></div>
    </div>
  </div>
</div>
<p class="iw-note"><b>This is a demo with sample output, not a live AI.</b> Install Newton and run <code>newton agent</code> to use Iris on your own computer, with your own files and your own AI.</p>'''

JS = r'''<script>
(function(){
  var root=document.getElementById("irisDemo"); if(!root) return;
  var sc=document.getElementById("iwScroll"), recent=document.getElementById("iwRecent");
  var reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches, token=0;
  var sleep=function(ms){return new Promise(function(r){setTimeout(r,reduce?0:ms)})};
  var esc=function(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")};
  var SC=[
   {id:"disk",title:"What's using my disk space?",sub:"Find the biggest folders and explain them",
    steps:[{cmd:"du -sh * | sort -rh | head -4",why:"Find what takes the most space",out:"18M    videos\n6.1M   build\n412K   docs\n24K    src"}],
    answer:"<p>The biggest thing here is <code>videos/</code> at about 18 MB, then <code>build/</code> at 6 MB.</p><ul><li><code>videos/</code> holds a single large video</li><li><code>build/</code> is generated output, so it is safe to rebuild</li><li>Everything else is tiny</li></ul><p>Want me to look inside <code>videos/</code>?</p>"},
   {id:"git",title:"What changed in this git repo?",sub:"Summarize recent work and edits",
    steps:[{cmd:"git status --short",why:"See uncommitted changes",out:" M src/server.py\n M README.md\n?? notes.txt"},{cmd:"git log --oneline -3",why:"Read the latest commits",out:"a41c9e2 Add request logging\n7be03d1 Fix port parsing\n0c58f77 Initial commit"}],
    answer:"<p>You have two edited files and one new file that are not committed yet:</p><ul><li><code>src/server.py</code> and <code>README.md</code> are modified</li><li><code>notes.txt</code> is new and untracked</li></ul><p>The last commit added request logging. I can write a commit message for the changes if you like.</p>"},
   {id:"mk",title:"Create a notes folder with a todo file",sub:"Iris asks before it changes anything",
    ask:{cmd:"mkdir -p notes && echo '# Todo' > notes/todo.md",why:"Create a notes folder with a starter file"},
    yes:"<p>Done. I created <code>notes/</code> with a <code>todo.md</code> that starts with a heading.</p>",
    no:"<p>Okay, I did not create anything. Tell me if you want a different folder name or location.</p>"}
  ];
  function el(h){var d=document.createElement("div");d.innerHTML=h;return d.firstChild}
  function put(n){sc.appendChild(n);sc.scrollTop=sc.scrollHeight;return n}
  function logo(){return '<span class="iris-logo" style="width:28px;height:28px"></span>'}
  function empty(){
    token++; sc.innerHTML=""; recent.innerHTML="";
    var e=el('<div class="iw-empty"><span class="iris-logo"></span><h3>What can Iris help with?</h3><p>Iris looks around your computer, runs commands step by step, and tells you what it found. It asks before changing anything.</p><div class="iw-sugs"></div></div>');
    var box=e.querySelector(".iw-sugs");
    SC.forEach(function(s){var b=document.createElement("button");b.type="button";b.className="iw-sug";b.innerHTML="<b>"+esc(s.title)+"</b><span>"+esc(s.sub)+"</span>";b.onclick=function(){play(s)};box.appendChild(b)});
    sc.appendChild(e);
  }
  function tool(cmd,why){return put(el('<div class="iw-tool"><div class="iw-th"><span class="ic">&gt;_</span><div class="cm"><b>'+esc(cmd)+'</b><span>'+esc(why)+'</span></div><span class="chip run">Running</span></div></div>'))}
  function setChip(t,cls,txt){var c=t.querySelector(".chip");c.className="chip "+cls;c.textContent=txt}
  function out(t,o){t.appendChild(el('<div class="iw-out">'+esc(o)+'</div>'));sc.scrollTop=sc.scrollHeight}
  function thinking(){return put(el('<div class="iw-ai"><span>'+logo()+'</span><div class="txt"><span class="iw-dots"><i></i><i></i><i></i></span></div></div>'))}
  function say(th,h){th.querySelector(".txt").innerHTML=h;sc.scrollTop=sc.scrollHeight}
  async function play(s){
    var my=++token; sc.innerHTML=""; recent.innerHTML='<div class="on">'+esc(s.title)+'</div>';
    put(el('<div class="iw-user">'+esc(s.title)+'</div>'));
    var th=thinking(); await sleep(700); if(my!==token)return;
    if(s.steps){
      th.remove();
      for(var i=0;i<s.steps.length;i++){
        var t=tool(s.steps[i].cmd,s.steps[i].why); await sleep(800); if(my!==token)return;
        setChip(t,"ok","Done"); out(t,s.steps[i].out); await sleep(500); if(my!==token)return;
      }
      th=thinking(); await sleep(700); if(my!==token)return;
      say(th,s.answer);
    } else {
      th.remove();
      var t2=tool(s.ask.cmd,s.ask.why); setChip(t2,"wait","Needs your OK");
      var ap=el('<div class="iw-appr"><b style="color:#9A5B00">Waiting for you.</b> This could change something.<div class="row"><button type="button" class="go">Allow</button><button type="button">Deny</button></div></div>');
      t2.appendChild(ap); sc.scrollTop=sc.scrollHeight;
      var btns=ap.querySelectorAll("button"); btns[0].focus({preventScroll:true});
      btns[0].onclick=async function(){ap.remove();setChip(t2,"run","Running");await sleep(600);if(my!==token)return;setChip(t2,"ok","Done");out(t2,"(no output)");var th2=thinking();await sleep(600);if(my!==token)return;say(th2,s.yes)};
      btns[1].onclick=async function(){ap.remove();setChip(t2,"no","Denied");var th3=thinking();await sleep(500);if(my!==token)return;say(th3,s.no)};
    }
  }
  document.getElementById("iwNew").onclick=empty;
  empty();
})();
</script>'''

def section():
    return '''<section class="band dark" id="iris" aria-labelledby="iris-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="iris-h">Meet Iris, the agent.</h2>
    <p class="lead">Tab writes one command. Iris takes on a whole task: it looks around your computer, runs the steps, reads what happens, and tells you the result. It lives in a chat window on your own computer.</p></div>
    <div class="rv">'''+DEMO+'''</div>
    <div class="iris-feat">
      <div class="rv"><h3>Looks on its own</h3><p>Read-only steps like listing files or reading a git log run without asking, so Iris can investigate.</p></div>
      <div class="rv" style="--d:.06s"><h3>Asks before it changes</h3><p>Anything that could change or delete something shows the exact command with Allow and Deny. Dangerous commands always ask.</p></div>
      <div class="rv" style="--d:.12s"><h3>Stays on your computer</h3><p>The app only answers to your own machine, with your own AI. Secrets are redacted and files like <code>.env</code> are never read.</p></div>
    </div>
    <div class="iris-cta rv"><a class="btn btn-primary" href="iris.html">Learn about Iris</a><a class="btn btn-ghost" href="download.html">Download Newton</a></div>
  </div>
</section>
'''+JS

CSS += r'''
@media (min-width:861px) and (max-width:1120px){.nav-in{gap:12px;padding-left:16px}.nav ul a{padding:8px 9px;font-size:.88rem}}
'''
