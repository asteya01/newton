from build_pages import page, hero
import parts

def ck(v):
    if v is True: return '<span class="yes" aria-label="Included">&#10003;</span>'
    if v is False: return '<span class="no" aria-label="Not included">&ndash;</span>'
    return v
cmp_rows=[("Tab: plain English to command",True,True),("Plan mode, ask, fix and commit",True,True),("zsh, bash and fish",True,True),("Local safety checks and secret redaction",True,True),("Bring your own AI (Claude, OpenAI-compatible, Ollama)",True,True),("No account, no telemetry",True,True),("Hosted models, no API key to set up",False,"Planned"),("Priority support by email",False,"Planned"),("Early access to new features",False,"Planned"),("Price","$0","$7 / month")]
cmp_html='<div class="tbl"><table><tr><th scope="col">&nbsp;</th><th scope="col">Free</th><th scope="col">Max</th></tr>'+''.join(f'<tr><td>{a}</td><td>{ck(b)}</td><td>{ck(c)}</td></tr>' for a,b,c in cmp_rows)+'</table></div>'

pr=hero("Pricing","Free to use. Max when you want more.","Newton is free and open source. Newton Max adds hosted models and priority help for $7 a month, and it's opening soon.",
 '<div class="pg-actions"><a class="btn btn-primary" href="#plans">See plans</a><button class="btn btn-ghost" type="button" data-modal="m-upgrade">Reserve Newton Max</button></div>')
pr+='''
<section class="band light" id="plans" aria-labelledby="pl-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="pl-h">Two plans. No tricks.</h2><p class="lead">Free is the full tool, not a trial. Max is for people who want us to run the AI for them.</p></div>
  '''+parts.plans(True)+'''
</div></section>
<section class="band white" aria-labelledby="cmp-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="cmp-h">Compare plans.</h2></div>
  <div class="cmp rv">'''+cmp_html+'''</div>
  <p class="fine rv" style="margin-top:18px">Items marked Planned aren't available yet and may change before Max launches. Your own AI provider may charge for usage on the Free plan; Ollama runs on your computer at no cost.</p>
</div></section>
<section class="band dark" aria-labelledby="pq-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="pq-h">Pricing questions.</h2></div>
  <div class="cards">
    <div class="cd d spot rv"><h3>Is Free really free?</h3><p>Yes. Newton is MIT licensed, with no account and no usage limit from us. If you connect Claude or another paid AI, that provider bills you. Ollama is free.</p></div>
    <div class="cd d spot rv" style="--d:.06s"><h3>When does Max open?</h3><p>Soon. Reserve a spot and we'll email you before anything is billed. Reserving is free and you can walk away at any time.</p></div>
    <div class="cd d spot rv" style="--d:.12s"><h3>Do I need Max?</h3><p>No. Everything Newton does today works on Free. Max is for people who'd rather not manage an API key.</p></div>
  </div>
  <div class="cta-row rv" style="margin-top:28px"><div><h3>Questions about pricing?</h3><p>Email <a href="mailto:tangriasteya@gmail.com" style="color:var(--mint)">tangriasteya@gmail.com</a> and we'll write back.</p></div><button class="btn btn-primary" type="button" data-modal="m-upgrade">Upgrade to Max</button></div>
</div></section>'''
page('pricing.html','Pricing · Newton','Newton is free. Newton Max adds hosted models and priority support for $7 a month. Reserve early access.',pr,parts.MODALS+parts.JS)

def sel(id,name,label,opts,req=True):
    o=''.join(f'<option>{x}</option>' for x in opts)
    return f'<div class="fld"><label for="{id}">{label}</label><select id="{id}" name="{name}"{" required" if req else ""}><option value="">Choose one</option>{o}</select></div>'
def inp(id,name,label,typ="text",ph="",req=True,full=False,extra="",ac=""):
    a=f' autocomplete="{ac}"' if ac else ''
    return f'<div class="fld{" full" if full else ""}"><label for="{id}">{label}{"" if req else " <span class=opt>Optional</span>"}</label><input id="{id}" name="{name}" type="{typ}" placeholder="{ph}"{" required" if req else ""} {extra}{a}></div>'

form=f'''<form class="form" data-mail data-subject="Newton team application" data-title="Newton team application" data-done-title="Your application is ready to send" data-done-text="Send the email we just prepared and we'll read it. Thank you for wanting to build Newton with us." novalidate>
<fieldset><legend>About you</legend><div class="fgrid">
{inp("j-name","name","Full name",ac="name",ph="Ada Lovelace")}
{inp("j-email","email","Email","email",ac="email",ph="you@example.com")}
{inp("j-loc","location","Country and time zone",ph="Canada, UTC-5")}
{sel("j-role","role","Where would you like to help?",["Engineering","Design","Documentation and writing","Community and testing","Not sure yet"])}
</div></fieldset>
<fieldset><legend>Education</legend><div class="fgrid">
{sel("j-level","education","Highest level of education",["High school (in progress)","High school (completed)","College or university (in progress)","Bachelor's degree","Master's degree","PhD","Self-taught","Other"])}
{inp("j-years","years_education","Years of education","number","Total years, e.g. 14",extra='min="0" max="40" inputmode="numeric"')}
{inp("j-school","school","School or university",ph="Name of your school")}
{inp("j-major","major","Major or field of study",ph="Computer science, design, self-directed")}
{inp("j-grad","grad","Graduation year","number","Actual or expected, e.g. 2028",req=False,extra='min="1970" max="2040" inputmode="numeric"')}
{sel("j-code","coding_years","Years of coding experience",["Less than 1","1 to 2","3 to 5","6 to 10","More than 10"])}
</div></fieldset>
<fieldset><legend>Your work</legend><div class="fgrid">
{inp("j-skills","skills","Skills and tools",ph="Python, shell, UI design, technical writing",full=True)}
{inp("j-gh","github","GitHub or portfolio","url","https://github.com/you")}
{inp("j-li","linkedin","LinkedIn","url","https://linkedin.com/in/you",req=False)}
{inp("j-cv","resume","Link to resume","url","https://example.com/resume",req=False,full=True)}
<div class="fld full"><label for="j-proj">Projects, hackathons or things you've built <span class="opt">Optional</span></label><textarea id="j-proj" name="projects" maxlength="800" data-count style="min-height:110px" placeholder="What you made, what you used, and what happened."></textarea></div>
</div></fieldset>
<fieldset><legend>Why you</legend><div class="fgrid">
<div class="fld full"><label for="j-why">Why should we choose you?</label><textarea id="j-why" name="why" required minlength="60" maxlength="1200" data-count placeholder="Tell us what you'd bring to Newton and what you'd want to work on. Specific beats polished."></textarea></div>
{sel("j-hours","hours","Hours per week you could give",["Less than 5","5 to 10","10 to 20","20 or more"])}
{sel("j-start","start","When could you start?",["Right away","Within a month","In a few months"])}
</div></fieldset>
<label class="chk"><input type="checkbox" name="consent" required><span>I confirm this information is accurate, and I'm happy for Newton to contact me about my application.</span></label>
<div class="form-actions"><button class="btn btn-ink" type="submit">Send application</button><p class="note">Your answers aren't stored on this site. We build an email with them, and you send it.</p></div>
</form>'''
jn=hero("Join","Help us build the future of the command line.","Newton is small, fast-moving and open. If you care about tools that respect people's time, we'd like to meet you.",
 '<div class="pg-actions"><a class="btn btn-primary" href="#apply">Apply now</a><a class="btn btn-ghost" href="team.html">Meet the team</a></div>')
jn+='''
<section class="band light" aria-labelledby="w-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="w-h">Where you could help.</h2><p class="lead">Newton is early, so one person can change a lot. Pick what fits you best.</p></div>
  <div class="cards two">
    <div class="cd spot rv"><h3>Engineering</h3><p>Shell integration, safety rules, provider support and the test suite that drives real terminals.</p></div>
    <div class="cd spot rv" style="--d:.06s"><h3>Design</h3><p>How Newton looks and reads in the terminal, plus this website and everything people see first.</p></div>
    <div class="cd spot rv" style="--d:.12s"><h3>Documentation and writing</h3><p>Guides, examples and release notes that make a new user successful in their first five minutes.</p></div>
    <div class="cd spot rv" style="--d:.18s"><h3>Community and testing</h3><p>Try Newton on your setup, report what breaks, and help others get started.</p></div>
  </div>
</div></section>
<section class="band white" id="apply" aria-labelledby="ap-h"><div class="wrap"><div class="join-grid">
  <aside class="join-aside rv"><span class="kicker"><i></i>Applications open</span><h2 id="ap-h">Tell us about you.</h2><p class="lead">It takes about ten minutes. Be specific and be yourself.</p>
    <ol class="jsteps"><li><div><strong>Fill in the form</strong>Education, experience and why you.</div></li><li><div><strong>Send the email</strong>We prepare it for you in one click.</div></li><li><div><strong>We reply</strong>We read every application and write back by email.</div></li></ol>
  </aside>
  <div class="form-card rv">'''+form+'''</div>
</div></div></section>'''
page('join.html','Join · Newton','Apply to join the Newton team: tell us about your education, experience and why you would be a great fit.',jn,parts.MODALS+parts.JS)
