defs=open('mark_defs.txt').read().replace('<defs>','').replace('</defs>','')
body=open('mark_body.txt').read()
three=open('three.min.js').read().replace('</script','<\\/script')
import parts
s=open('v2.html').read().replace('</style>',parts.CSS+'</style>',1)
out=s.replace('{{MARK_DEFS}}','<defs>'+defs+'</defs>').replace('{{MARK_BODY}}',body).replace('{{THREE}}',three).replace('{{PRICING}}',parts.pricing_section()).replace('{{UI_MODALS}}',parts.MODALS).replace('{{UI_JS}}',parts.JS)
open('index.html','w').write(out); print(len(out)//1024,'KB')
