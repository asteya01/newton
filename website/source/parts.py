TO = "tangriasteya@gmail.com"

CSS = r'''
/* ---- shared UI: buttons, plans, forms, modal ---- */
.btn-ink{background:#0A0F1A;color:#fff;box-shadow:0 10px 30px -12px rgba(10,15,26,.6)}
.btn-ink:hover{transform:translateY(-2px);background:#111A28}
.btn-line{background:#fff;color:var(--text);border:1px solid var(--line)}
.btn-line:hover{transform:translateY(-2px);border-color:#B7C3D2}
.plans{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;max-width:980px}
.plan{grid-template-rows:auto auto 1fr;position:relative;border-radius:28px;padding:36px;display:grid;gap:24px;align-content:start;color:var(--text-d);background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.12)}
.plan h3{font-size:1.5rem;line-height:1.1}
.plan .sub{color:var(--muted-d);margin-top:6px;font-size:1rem}
.plan .price{display:flex;align-items:baseline;gap:10px;font:600 clamp(3.2rem,5.4vw,4.4rem)/1 var(--f-sans);letter-spacing:-.055em;color:#fff}
.plan .price small{font:500 1rem var(--f-sans);letter-spacing:0;color:var(--muted-d)}
.plan ul{list-style:none;margin:0;padding:0;display:grid;gap:13px}
.plan li{display:grid;grid-template-columns:22px minmax(0,1fr);gap:12px;color:var(--text-d);align-items:start}
.plan li::before{content:"";width:22px;height:22px;border-radius:50%;margin-top:1px;background:rgba(61,245,167,.16) center/12px no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M2.4 6.3l2.4 2.4 4.8-5' fill='none' stroke='%233DF5A7' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}
.plan li em{font-style:normal;font:500 .72rem var(--f-mono);color:var(--amber);border:1px solid rgba(245,177,74,.4);border-radius:999px;padding:2px 8px;margin-left:8px;white-space:nowrap}
.plan .btn{width:100%}
.plan.max{background:linear-gradient(#0B151D,#0B151D) padding-box,var(--grad) border-box;border:1.5px solid transparent;box-shadow:0 30px 80px -30px rgba(61,245,167,.45)}
.plan .badge{position:absolute;top:24px;right:24px;font:600 .78rem/1 var(--f-sans);padding:7px 12px;border-radius:999px;background:var(--grad);color:#04130B}
.plan .fineprint{font-size:.86rem;color:var(--muted-d);text-align:center;margin-top:-8px}
.plan.lt{background:#fff;color:var(--text);border-color:var(--line)}
.plan.lt .price{color:var(--text)}.plan.lt .sub,.plan.lt .price small{color:var(--muted)}
.plan.lt li{color:var(--text)}
.plan.lt li::before{background-color:rgba(6,122,85,.12);background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'%3E%3Cpath d='M2.4 6.3l2.4 2.4 4.8-5' fill='none' stroke='%23067A55' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}
.plan.max li{color:var(--text-d)}
.cmp{max-width:980px}
.cmp .tbl td:not(:first-child),.cmp .tbl th:not(:first-child){text-align:center}
.cmp .yes{color:var(--leaf);font-weight:700}.cmp .no{color:#A5B0BD}
/* forms */
.form{display:grid;gap:34px}
.form fieldset{border:0;padding:0;margin:0;display:grid;gap:18px;min-width:0}
.form legend{font:600 1.4rem/1.2 var(--f-sans);letter-spacing:-.035em;padding:0;margin-bottom:4px;color:var(--text)}
.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.fld{display:grid;gap:7px;min-width:0;align-content:start}
.fld.full{grid-column:1/-1}
.fld label{display:flex;justify-content:space-between;gap:10px;font-weight:600;font-size:.95rem;color:var(--text)}
.fld .opt{font-weight:400;font-size:.84rem;color:var(--muted)}
.fld .hint{font-size:.86rem;color:var(--muted)}
.fld input,.fld select,.fld textarea{width:100%;min-height:50px;padding:12px 16px;border:1.5px solid var(--line);border-radius:14px;background:#fff;color:var(--text);font:400 1rem/1.4 var(--f-sans);transition:border-color .15s,box-shadow .15s}
.fld textarea{min-height:150px;resize:vertical;line-height:1.55}
.fld select{appearance:none;-webkit-appearance:none;padding-right:44px;background:#fff center right 16px/12px no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' fill='none' stroke='%23566274' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}
.fld input::placeholder,.fld textarea::placeholder{color:#8896A8}
.fld input:hover,.fld select:hover,.fld textarea:hover{border-color:#B7C3D2}
.fld input:focus,.fld select:focus,.fld textarea:focus{outline:none;border-color:var(--leaf);box-shadow:0 0 0 4px rgba(6,122,85,.14)}
.fld [aria-invalid="true"]{border-color:#D6453D;box-shadow:0 0 0 4px rgba(214,69,61,.1)}
.err{color:#C0392B;font-size:.88rem;font-weight:500}
.count{font:400 .8rem var(--f-mono);color:var(--muted);text-align:right}
.count.ok{color:var(--leaf)}
.chk{display:grid;grid-template-columns:22px 1fr;gap:12px;align-items:start;font-size:.95rem;color:var(--muted);cursor:pointer}
.chk input{width:20px;height:20px;min-height:0;margin:2px 0 0;accent-color:var(--leaf)}
.form-actions{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.form-actions .note{font-size:.9rem;color:var(--muted);max-width:46ch}
.form-card{background:#fff;border:1px solid var(--line);border-radius:32px;padding:clamp(24px,4vw,48px);box-shadow:0 40px 80px -50px rgba(10,15,26,.4)}
.join-grid{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:clamp(28px,5vw,72px);align-items:start}
.join-aside{position:sticky;top:96px;display:grid;gap:18px}
.join-aside h2{font-size:clamp(2rem,3.6vw,2.8rem);line-height:1.05}
.jsteps{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:18px;counter-reset:s}
.jsteps li{display:grid;grid-template-columns:34px 1fr;gap:14px;counter-increment:s;color:var(--muted)}
.jsteps li::before{content:counter(s);display:grid;place-items:center;width:34px;height:34px;border-radius:50%;border:1.5px solid var(--leaf);color:var(--leaf);font:600 .9rem var(--f-mono)}
.jsteps strong{display:block;color:var(--text);margin-bottom:2px}
/* modal */
.modal{position:fixed;inset:0;z-index:200;display:grid;place-items:center;padding:20px;opacity:0;transition:opacity .18s ease}
.modal[hidden]{display:none}
.modal.open{opacity:1}
.modal-bg{position:absolute;inset:0;background:rgba(3,6,10,.74);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.modal-card{position:relative;width:min(580px,100%);max-height:calc(100dvh - 40px);overflow:auto;background:#fff;color:var(--text);color-scheme:light;border-radius:28px;padding:clamp(26px,4vw,40px);transform:translateY(16px) scale(.98);transition:transform .24s cubic-bezier(.2,.7,.2,1);box-shadow:0 40px 100px -20px rgba(0,0,0,.7)}
.modal.open .modal-card{transform:none}
.modal-card h2{font-size:clamp(1.7rem,3vw,2.1rem);line-height:1.08;letter-spacing:-.045em;margin-right:36px}
.modal-card .m-lead{color:var(--muted);margin:10px 0 24px}
.modal-x{position:absolute;top:18px;right:18px;width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:#fff;color:var(--text);font:400 1.5rem/1 var(--f-sans);cursor:pointer;display:grid;place-items:center;transition:background .15s}
.modal-x:hover{background:#F0F4F8}
.m-price{display:inline-flex;align-items:baseline;gap:6px;font:600 1.1rem var(--f-sans);color:var(--leaf);background:rgba(6,122,85,.09);padding:6px 12px;border-radius:999px;margin-bottom:14px}
.m-price small{font-weight:500;color:var(--muted)}
.m-ok{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;background:var(--grad);margin-bottom:18px}
.m-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.m-sum{margin-top:18px;max-height:180px;overflow:auto;white-space:pre-wrap;font:400 .82rem/1.55 var(--f-mono);background:#F3F6FA;border:1px solid var(--line);border-radius:14px;padding:14px 16px;color:#3A4757}
html.modal-open{overflow:hidden}
@media (max-width:960px){.plans{grid-template-columns:1fr}.join-grid{grid-template-columns:1fr}.join-aside{position:static}}
@media (max-width:600px){.fgrid{grid-template-columns:1fr}.plan{padding:28px}.plan .badge{position:static;width:fit-content}}
@media (prefers-reduced-motion:reduce){.modal,.modal-card{transition:none}}
'''

MODALS = r'''
<div class="modal" id="m-upgrade" role="dialog" aria-modal="true" aria-labelledby="m-upgrade-t" hidden>
  <div class="modal-bg" data-close></div>
  <div class="modal-card">
    <button class="modal-x" type="button" data-close aria-label="Close">&times;</button>
    <span class="m-price">$7 <small>per month</small></span>
    <h2 id="m-upgrade-t">Reserve Newton Max</h2>
    <p class="m-lead">Newton Max isn't billing yet. Tell us a little about yourself and we'll email you before it opens. You won't be charged for anything here.</p>
    <form class="form" data-mail data-subject="Newton Max early access" data-title="Newton Max early access request" data-done-title="Your request is ready to send" data-done-text="Send the email we just prepared and your spot is saved. We'll write back before anything is billed." novalidate>
      <div class="fgrid">
        <div class="fld"><label for="u-name">Full name</label><input id="u-name" name="name" type="text" autocomplete="name" required placeholder="Ada Lovelace"></div>
        <div class="fld"><label for="u-email">Email</label><input id="u-email" name="email" type="email" autocomplete="email" required placeholder="you@example.com"></div>
        <div class="fld"><label for="u-use">How do you use the terminal?</label><select id="u-use" name="use" required><option value="">Choose one</option><option>Student</option><option>Hobbyist</option><option>Software developer</option><option>DevOps or sysadmin</option><option>Data or research</option><option>Other</option></select></div>
        <div class="fld"><label for="u-ai">Which AI do you use today?</label><select id="u-ai" name="ai" required><option value="">Choose one</option><option>Claude</option><option>OpenAI or similar</option><option>Ollama (local)</option><option>None yet</option></select></div>
        <div class="fld full"><label for="u-note">What would make Max worth $7 to you? <span class="opt">Optional</span></label><textarea id="u-note" name="note" rows="3" style="min-height:96px" placeholder="Features, limits, anything on your mind"></textarea></div>
      </div>
      <label class="chk"><input type="checkbox" name="consent" required><span>Email me when Newton Max opens. I understand nothing is charged today.</span></label>
      <div class="m-actions" style="margin-top:0"><button class="btn btn-ink" type="submit">Reserve my spot</button><button class="btn btn-line" type="button" data-close>Not now</button></div>
    </form>
  </div>
</div>
<div class="modal" id="m-done" role="dialog" aria-modal="true" aria-labelledby="m-done-t" hidden>
  <div class="modal-bg" data-close></div>
  <div class="modal-card">
    <button class="modal-x" type="button" data-close aria-label="Close">&times;</button>
    <div class="m-ok" aria-hidden="true"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#04130B" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></div>
    <h2 id="m-done-t">Ready to send</h2>
    <p class="m-lead" id="m-done-p" style="margin-bottom:0"></p>
    <pre class="m-sum" id="m-done-sum" tabindex="0"></pre>
    <p class="m-lead" style="font-size:.9rem;margin:14px 0 0">This site has no server, so nothing is sent until you press Send in your email app. If it didn't open, copy the text and email <strong>tangriasteya@gmail.com</strong>.</p>
    <div class="m-actions"><a class="btn btn-ink" id="m-done-mail" href="#">Open email app</a><button class="btn btn-line" type="button" id="m-done-copy">Copy text</button></div>
  </div>
</div>
'''

JS = r'''<script>
(function(){
  "use strict";
  const TO="tangriasteya@gmail.com";
  const $=(s,r)=>(r||document).querySelector(s), $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
  let openEl=null,lastFocus=null;
  function openM(id){const m=document.getElementById(id);if(!m)return;if(openEl&&openEl!==m)closeM(true);clearTimeout(m._t);lastFocus=lastFocus||document.activeElement;m.hidden=false;requestAnimationFrame(()=>m.classList.add("open"));document.documentElement.classList.add("modal-open");openEl=m;setTimeout(()=>{const f=$("input,select,textarea,.btn",m);if(f)f.focus()},60)}
  function closeM(keep){if(!openEl)return;const m=openEl;m.classList.remove("open");m._t=setTimeout(()=>{m.hidden=true},200);openEl=null;if(!keep){document.documentElement.classList.remove("modal-open");if(lastFocus&&lastFocus.focus)lastFocus.focus();lastFocus=null}}
  document.addEventListener("click",e=>{const o=e.target.closest("[data-modal]");if(o){e.preventDefault();openM(o.dataset.modal);return}if(e.target.closest("[data-close]")){e.preventDefault();closeM()}});
  document.addEventListener("keydown",e=>{if(!openEl)return;if(e.key==="Escape"){closeM();return}
    if(e.key==="Tab"){const f=$$("a[href],button:not([disabled]),input,select,textarea,[tabindex='0']",openEl).filter(x=>x.offsetParent!==null);if(!f.length)return;const a=f[0],z=f[f.length-1];if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}});
  if(location.hash==="#upgrade")openM("m-upgrade");
  function labelOf(el){const l=el.id&&document.querySelector('label[for="'+el.id+'"]');if(!l)return el.name;const c=l.cloneNode(true);$$(".opt",c).forEach(x=>x.remove());return c.textContent.trim().replace(/\s+/g," ")}
  function setErr(el,msg){const f=el.closest(".fld")||el.closest(".chk")||el.parentElement;let e=$(".err",f);if(!msg){if(e)e.remove();el.removeAttribute("aria-invalid");return}
    if(!e){e=document.createElement("div");e.className="err";e.setAttribute("role","alert");f.appendChild(e)}e.textContent=msg;el.setAttribute("aria-invalid","true")}
  function check(el){const v=(el.type==="checkbox")?el.checked:el.value.trim();
    if(el.required&&!v)return el.type==="checkbox"?"Please tick this box to continue.":(el.tagName==="SELECT"?"Choose an option.":"This field is required.");
    if(v&&el.type==="email"&&!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v))return"Enter a valid email address.";
    if(v&&el.type==="url"&&!/^https?:\/\/\S+\.\S+/i.test(v))return"Enter a full link starting with https://";
    if(v&&el.minLength>0&&el.value.trim().length<el.minLength)return"Please write at least "+el.minLength+" characters ("+el.value.trim().length+" so far).";
    if(v&&el.type==="number"){const n=+el.value;if(el.min!==""&&n<+el.min||el.max!==""&&n>+el.max)return"Enter a number from "+el.min+" to "+el.max+"."}
    return""}
  $$("textarea[data-count]").forEach(t=>{const c=document.createElement("div");c.className="count";t.insertAdjacentElement("afterend",c);const min=Math.max(0,t.minLength);const up=()=>{const n=t.value.trim().length;c.textContent=n+" / "+t.maxLength+(min?" · minimum "+min:"");c.classList.toggle("ok",!min||n>=min)};t.addEventListener("input",up);t._up=up;up()});
  $$("form[data-mail]").forEach(form=>{
    const ctl=()=>$$("input,select,textarea",form);
    ctl().forEach(el=>{el.addEventListener("input",()=>{if(el.getAttribute("aria-invalid"))setErr(el,check(el))});el.addEventListener("change",()=>{if(el.getAttribute("aria-invalid"))setErr(el,check(el))});el.addEventListener("blur",()=>{if(el.value&&el.type!=="checkbox")setErr(el,check(el))})});
    form.addEventListener("submit",e=>{e.preventDefault();let first=null;ctl().forEach(el=>{const m=check(el);setErr(el,m);if(m&&!first)first=el});if(first){first.focus();first.scrollIntoView({block:"center",behavior:"smooth"});return}
      const lines=[form.dataset.title,"Sent from newton.sh on "+new Date().toLocaleString(),""];
      const seen={};ctl().forEach(el=>{if(el.type==="checkbox"){if(el.name==="consent")return;lines.push(labelOf(el)+": "+(el.checked?"Yes":"No"));return}const v=el.value.trim();if(!v)return;const L=labelOf(el);if(el.tagName==="TEXTAREA")lines.push("",L+":",v,"");else lines.push(L+": "+v)});
      const text=lines.join("\n").replace(/\n{3,}/g,"\n\n").trim();
      const body=text.length>1700?text.slice(0,1700)+"\n…(full text was copied; paste it here)":text;
      const href="mailto:"+TO+"?subject="+encodeURIComponent(form.dataset.subject)+"&body="+encodeURIComponent(body);
      $("#m-done-t").textContent=form.dataset.doneTitle;$("#m-done-p").textContent=form.dataset.doneText;$("#m-done-sum").textContent=text;
      const ml=$("#m-done-mail");ml.href=href;const cp=$("#m-done-copy");cp.textContent="Copy text";cp.onclick=async()=>{try{await navigator.clipboard.writeText(text);cp.textContent="Copied"}catch(x){const r=document.createRange();r.selectNodeContents($("#m-done-sum"));const s=getSelection();s.removeAllRanges();s.addRange(r);cp.textContent="Press Ctrl/Cmd+C"}};
      openM("m-done");form.reset();$$("textarea[data-count]",form).forEach(t=>t._up());
      setTimeout(()=>{try{ml.click()}catch(x){}},350)});
  });
})();
</script>'''

def plans(light=False, link_dl="download.html"):
    lt = " lt" if light else ""
    return f'''<div class="plans">
  <div class="plan{lt} spot rv">
    <div><h3>Newton Free</h3><p class="sub">Everything you need to live in the terminal.</p></div>
    <div class="price">$0<small>forever</small></div>
    <ul>
      <li><span>Tab turns plain English into a command</span></li>
      <li><span>Plan mode, ask, fix and commit</span></li>
      <li><span>zsh, bash and fish on macOS, Linux and WSL</span></li>
      <li><span>Local safety checks and secret redaction</span></li>
      <li><span>Bring your own AI: Claude, OpenAI-compatible, or free Ollama</span></li>
      <li><span>MIT licensed, no account, no telemetry</span></li>
    </ul>
    <a class="btn {"btn-ink" if light else "btn-ghost"}" href="{link_dl}">Download free</a>
  </div>
  <div class="plan max spot rv" style="--d:.08s">
    <span class="badge">Early access</span>
    <div><h3>Newton Max</h3><p class="sub">For people who use Newton all day.</p></div>
    <div class="price">$7<small>per month</small></div>
    <ul>
      <li><span>Everything in Free</span></li>
      <li><span>Hosted models included, no API key to set up <em>Planned</em></span></li>
      <li><span>Priority support by email <em>Planned</em></span></li>
      <li><span>Early access to new features <em>Planned</em></span></li>
      <li><span>Helps fund open development</span></li>
    </ul>
    <button class="btn btn-primary" type="button" data-modal="m-upgrade">Upgrade to Max</button>
    <p class="fineprint">Not billing yet. Reserve a spot and we'll email you first.</p>
  </div>
</div>'''

def pricing_section():
    return '''<section class="band dark" id="pricing" aria-labelledby="price-h">
  <div class="wrap">
    <div class="sec-head rv"><h2 id="price-h">Start free. Upgrade when you want more.</h2><p class="lead">Newton is free and open source. Newton Max is for people who want hosted models and priority help for $7 a month.</p></div>
    ''' + plans(False,"download.html") + '''
  </div>
</section>
'''
