import glob,re
for f in glob.glob('*.html'):
    if f in('v2.html','template.html','index.html'): continue
    s=open(f).read()
    if 'pricing.html' not in s.split('<main')[0]:
        s=s.replace('<li><a href="index.html#faq">FAQ</a></li></ul>','<li><a href="pricing.html">Pricing</a></li><li><a href="index.html#faq">FAQ</a></li><li><a href="join.html">Join</a></li></ul>',1)
        s=s.replace('<li><a href="download.html">Download</a></li></ul></div>\n    <div><h3>Company','<li><a href="download.html">Download</a></li><li><a href="pricing.html">Pricing</a></li></ul></div>\n    <div><h3>Company',1)
        s=s.replace('<li><a href="donate.html">Donate</a></li></ul></div>','<li><a href="donate.html">Donate</a></li><li><a href="join.html">Join</a></li></ul></div>',1)
    for pg in('pricing','join'):
        if f==pg+'.html': s=s.replace(f'<a href="{pg}.html">{pg.title()}</a></li>',f'<a href="{pg}.html" class="cur" aria-current="page">{pg.title()}</a></li>',1)
    open(f,'w').write(s)
print('ok')

# Theo, the helper widget: on every page, once
import theo
for f in glob.glob('*.html'):
    if f in('v2.html','template.html'): continue
    s=open(f).read()
    if 'id="theoFab"' in s: continue
    i=s.index('</style>'); s=s[:i]+theo.CSS+s[i:]
    j=s.rfind('</body>'); s=s[:j]+theo.HTML+'\n'+theo.JS+'\n'+s[j:]
    open(f,'w').write(s)
print('theo ok')
