import re
dl=open('download.html').read()
head=dl[:dl.index('</style>')]
head=head.replace('<title>Download Newton 2.2.0</title>','<title>Team · Newton</title>')
head=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="The people building Newton, and what we believe about the command line.">',head)
extra='''
.tm-hero{position:relative;overflow:hidden;isolation:isolate;padding-block:calc(var(--nav-h) + 100px) 90px}
.tm-hero h1{font-size:clamp(3rem,7.4vw,6.4rem);line-height:.95;letter-spacing:-.055em;margin-top:24px;max-width:11em}
.tm-hero .lead{margin-top:26px}
.beliefs{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.bel{background:#fff;border:1px solid var(--line);border-radius:24px;padding:32px;display:grid;gap:10px;align-content:start;transition:transform .3s cubic-bezier(.2,.7,.2,1),box-shadow .3s}
.bel:hover{transform:translateY(-4px);box-shadow:0 26px 50px -28px rgba(10,15,26,.35)}
.bel h3{font-size:1.6rem;line-height:1.1}.bel p{color:var(--muted);max-width:44ch}
.people{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.person{background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.12);border-radius:28px;padding:34px;display:grid;gap:16px;align-content:start;transition:transform .3s cubic-bezier(.2,.7,.2,1),border-color .3s}
.person:hover{transform:translateY(-5px);border-color:rgba(61,245,167,.45)}
.ava{position:relative;width:132px;height:132px;border-radius:50%;display:grid;place-items:center;font:600 2.6rem var(--f-sans);letter-spacing:-.04em;color:#06140E;background:conic-gradient(from var(--a,0deg),#D4FA6A,#3DF5A7,#4D7CFF,#B9A2FF,#D4FA6A);animation:spin 9s linear infinite}
.ava::before{content:"";position:absolute;inset:4px;border-radius:50%;background:#0B1219}
.ava span{position:relative;z-index:1;color:#E8FFF5}
@keyframes spin{to{--a:360deg}}
@property --a{syntax:"<angle>";initial-value:0deg;inherits:false}
.person h3{font-size:1.7rem;line-height:1.1}
.person .role{color:var(--mint);font:500 .95rem var(--f-mono)}
.person p{color:var(--muted-d);font-size:1rem;max-width:36ch}
.person .links{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}
.person .links span{font:500 .78rem var(--f-mono);color:#7C8E9E;border:1px solid var(--line-d);border-radius:8px;padding:4px 9px}
.join{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;border:1px dashed rgba(255,255,255,.22);border-radius:24px;padding:32px 36px;margin-top:18px}
.join h3{font-size:1.7rem}.join p{color:var(--muted-d);margin-top:6px}
.join em{font:500 .72rem var(--f-mono);font-style:normal;border:1px solid var(--line-d);border-radius:6px;padding:2px 8px;color:#7C8E9E;margin-left:10px;vertical-align:middle}

.people.one{grid-template-columns:1fr}
.person.wide{grid-template-columns:auto 1fr;gap:20px 44px;align-items:center;padding:44px}
.person.wide .ava{width:180px;height:180px;font-size:3.6rem}
.person.wide p{max-width:52ch;font-size:1.12rem;color:#B6C4CF}
.person.wide h3{font-size:2.4rem;letter-spacing:-.045em}
.person .links a{font:500 .85rem var(--f-mono);color:#E3ECF3;border:1px solid rgba(255,255,255,.2);border-radius:999px;padding:8px 16px;text-decoration:none;display:inline-flex;gap:8px;align-items:center;transition:border-color .2s,background .2s}
.person .links a:hover{border-color:var(--mint);background:rgba(61,245,167,.1)}
.reveal-btn{cursor:pointer}
.phone{display:inline-flex;align-items:center;gap:12px;font:600 1.5rem var(--f-mono);letter-spacing:-.01em;color:var(--mint);text-decoration:none}
.phone:hover{text-decoration:underline}
@media (max-width:700px){.person.wide{grid-template-columns:1fr;padding:30px}}
@media (max-width:960px){.people{grid-template-columns:1fr}.beliefs{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){.ava{animation:none}}
'''
rest=dl[dl.index('</style>'):]
# nav + footer + svg defs from the download page
svg=re.search(r'<svg width="0".*?</svg>',rest,re.S).group(0)
nav=re.search(r'<header class="nav".*?</header>',rest,re.S).group(0).replace(' class="cur" aria-current="page"','').replace('href="#get">Download','href="download.html">Download')
foot=re.search(r'<footer class="footer">.*?</footer>',rest,re.S).group(0).replace('<span class="soon">Team <em>Soon</em></span>','<a href="team.html">Team</a>')
def person(): return """<article class="person wide spot rv"><div class="ava" aria-hidden="true"><span>A</span></div><div style="display:grid;gap:14px"><div><h3>Asteya</h3><div class="role">Founder</div></div><p>Entrepreneur and builder who has competed in hackathons and turned ideas into working products fast. Founded Newton to make the command line feel effortless.</p><div class="links"><a href="https://github.com/asteya01" rel="noopener">GitHub · asteya01</a></div></div></article>"""
main=f'''<main id="main">
<section class="tm-hero" aria-labelledby="h1"><div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div><div class="floor" aria-hidden="true"></div>
  <div class="wrap"><span class="kicker"><i></i>Team</span><h1 id="h1">The people behind Newton.</h1>
  <p class="lead">We're building a calmer, friendlier way to use the command line.</p></div></section>

<section class="band dark" aria-labelledby="ppl-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="ppl-h">Meet the team.</h2></div>
  <div class="people one">
    {person()}
  </div>
  <div class="join rv"><div><h3>Want to help build Newton?</h3><p>We'd like to hear from you.</p></div><div id="contactBox" aria-live="polite"><button class="btn btn-primary reveal-btn" id="showPhone" type="button">Click to see contact number</button></div></div>
</div></section>

<section class="band light" aria-labelledby="bel-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="bel-h">What we believe.</h2><p class="lead">These four ideas shape every decision in Newton.</p></div>
  <div class="beliefs">
    <div class="bel spot rv"><h3>You stay in control</h3><p>Newton suggests. You decide. Nothing runs until you press Enter, and risky steps always ask first.</p></div>
    <div class="bel spot rv" style="--d:.06s"><h3>Your data is yours</h3><p>Secrets are scrubbed before anything is sent, there's no telemetry, and you can run fully offline.</p></div>
    <div class="bel spot rv" style="--d:.12s"><h3>It works where you work</h3><p>Your shell, your system, your AI. zsh, bash and fish, on Mac, Linux and Chromebook.</p></div>
    <div class="bel spot rv" style="--d:.18s"><h3>Plain English first</h3><p>You shouldn't need to memorize flags to get things done in a terminal.</p></div>
  </div>
</div></section>
</main>'''
script=re.search(r'<script>.*</script>',rest,re.S).group(0)
# trimmed script: keep reveal, progress, spotlight, menu
script=re.sub(r'  const tabs=.*?\n  const nav=','  const nav=',script,flags=re.S)
script=script[:script.rindex('})();')]+'''
  const sb=$("#showPhone");
  if(sb)sb.addEventListener("click",()=>{const d=["279","267","6299"],n=d[0]+" "+d[1]+" "+d[2],a=document.createElement("a");a.className="phone";a.href="tel:+1"+d.join("");a.textContent="+1 "+n;const box=$("#contactBox");box.textContent="";box.appendChild(a)});
'''+script[script.rindex('})();'):]
page=head+extra+'</style></head><body>\n'+svg+'\n<a class="skip" href="#main">Skip to content</a><div id="prog" aria-hidden="true"></div>\n'+nav+'\n'+main+'\n'+foot+'\n'+script+'</body></html>'
page=page.replace('</style></head><body>','</style></head><body>',1)
open('team.html','w').write(page); print(len(page)//1024,'KB')
