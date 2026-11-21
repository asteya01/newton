from build_pages import page, hero, code
import parts, iris_demo

main = hero("Iris · included in Newton 2.3", "An agent that gets things done on your computer.",
  "Tab turns a sentence into one command. Iris takes on a whole task: it looks around, runs the steps, reads what happens, and tells you the result, in a chat window that runs on your own machine.",
  '<div class="pg-actions"><a class="btn btn-primary" href="download.html">Download Newton</a><a class="btn btn-ghost" href="#demo">Try the demo</a></div>')

main += '''
<section class="band dark" id="demo" aria-labelledby="demo-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="demo-h">See how it works.</h2><p class="lead">Pick a request. Iris runs a few steps and explains what it found. The last one shows how it asks before it changes anything.</p></div>
  <div class="rv">''' + iris_demo.DEMO + '''</div>
</div></section>

<section class="band light" aria-labelledby="how-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="how-h">How Iris works.</h2><p class="lead">You ask in plain English. Iris plans one step at a time and shows you each one.</p></div>
  <div class="cards two">
    <div class="cd spot rv"><h3>It runs the steps itself</h3><p>Iris picks a command, runs it in a shell that remembers your folder, reads the output, and decides what to do next. It stops when it has an answer, or after a safe limit of steps.</p></div>
    <div class="cd spot rv" style="--d:.06s"><h3>You see every command</h3><p>Each step appears as a card with the exact command and its output. Open a card to read the full result.</p></div>
    <div class="cd spot rv" style="--d:.12s"><h3>Uses your AI</h3><p>Iris uses the provider you set up for Newton: Claude, an OpenAI-compatible service with your own key, or Ollama on your own computer for free.</p></div>
    <div class="cd spot rv" style="--d:.18s"><h3>Keeps your chats</h3><p>Conversations are saved only on your computer, so you can come back to them from the sidebar. Delete any of them at any time.</p></div>
  </div>
</div></section>

<section class="band dark" aria-labelledby="safe-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="safe-h">What runs on its own, and what asks first.</h2><p class="lead">Iris is built so it can look freely and can only change things with your say-so.</p></div>
  <div class="tbl rv"><table>
    <thead><tr><th>Kind of step</th><th>What happens</th></tr></thead>
    <tbody>
      <tr><td>Looking: listing files, reading a git log, checking disk use</td><td>Runs on its own</td></tr>
      <tr><td>Anything that could create, change or delete something</td><td>Shows the command and waits for Allow or Deny</td></tr>
      <tr><td>Commands the safety rules flag, such as <code>git reset --hard</code></td><td>Always asks, and says why it is risky</td></tr>
      <tr><td>Writing a file</td><td>Always asks</td></tr>
      <tr><td>Secret files such as <code>.env</code>, SSH keys and <code>.pem</code> files</td><td>Never read</td></tr>
    </tbody>
  </table></div>
  <p class="prose rv" style="margin-top:22px;color:var(--muted-d)">Prefer to approve everything? Turn on <b>Ask before every command</b> in the sidebar, or start with <code>newton agent --ask</code>. Command output is redacted for secrets before the AI sees it. The app only listens on your own computer and answers only to a private link.</p>
</div></section>

<section class="band light" id="start" aria-labelledby="start-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="start-h">Start in a minute.</h2><p class="lead">Iris comes with Newton 2.3. Install or update Newton, then run one command.</p></div>
  <div class="rv" style="max-width:760px">''' + code("newton agent") + '''
    <p class="prose" style="margin-top:14px">It opens Iris in your browser, working in the current folder. Use <code>--dir</code> to pick another folder, and <code>newton config agent_name</code> if you want to call it something else.</p>
    <div class="iris-cta" style="justify-content:flex-start"><a class="btn btn-ink" href="download.html">Download Newton 2.3</a><a class="btn btn-line" href="docs.html#iris">Read the docs</a></div>
  </div>
</div></section>

<section class="band light" aria-labelledby="faq-h"><div class="wrap">
  <div class="sec-head rv"><h2 id="faq-h">Good to know.</h2></div>
  <div class="faq rv">
    <details name="faq" open><summary>Does Iris need the internet?</summary><div class="ans"><p>Only to reach your AI provider. With Ollama running on your computer, nothing leaves your machine.</p></div></details>
    <details name="faq"><summary>Which model should I use?</summary><div class="ans"><p>Iris works best with a capable model such as Claude. Small local models can be slower and sometimes need a nudge to follow the step-by-step format.</p></div></details>
    <details name="faq"><summary>Can it break my computer?</summary><div class="ans"><p>Anything that could change or delete something asks you first, and risky commands always ask with a reason. Read the command on the card before you press Allow, as you would for any command.</p></div></details>
    <details name="faq"><summary>Is the demo on this page the real thing?</summary><div class="ans"><p>No. The demo plays scripted sample output so you can see how Iris looks and behaves. The real Iris runs on your computer with your own AI and your own files.</p></div></details>
    <p class="faq-more">Have another question? Email <a href="mailto:tangriasteya@gmail.com">tangriasteya@gmail.com</a>.</p>
  </div>
</div></section>
'''
page('iris.html','Iris, the Newton agent','Iris is a chat app that runs on your computer, does tasks step by step, runs read-only steps on its own and asks before it changes anything. Included in Newton 2.3.', main, iris_demo.JS)
s=open('iris.html').read()
s=s.replace('<li><a href="iris.html">Iris</a></li>','<li><a href="iris.html" class="cur" aria-current="page">Iris</a></li>',1)
open('iris.html','w').write(s)
