import asyncio, os, json, subprocess, time, hmac, hashlib, base64, sys
from playwright.async_api import async_playwright
S=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.path.join(S,'..','..'))   # the built app (run build.py first)
SERVER=os.environ.get('THIRTEEN_SERVER',os.path.join(ROOT,'..','thirteen-server'))
os.makedirs(S+'/out',exist_ok=True)
def b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b'=').decode()
URL='https://test-project.supabase.co'; SECRET='test-secret'
def tok(sub,name):
    h=b64({'alg':'HS256','typ':'JWT'}); b=b64({'sub':sub,'aud':'authenticated','iss':URL+'/auth/v1','exp':int(time.time())+3600,'user_metadata':{'full_name':name}})
    sig=base64.urlsafe_b64encode(hmac.new(SECRET.encode(),(h+'.'+b).encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
    return h+'.'+b+'.'+sig
env=dict(os.environ,THIRTEEN_FAST='1',PORT='8099',ADMIN_IDS='aaaa-1',SUPABASE_URL=URL,SUPABASE_JWT_SECRET=SECRET,ALLOWED_ORIGINS='http://127.0.0.1:8098')
srv=subprocess.Popen(['node',os.path.join(SERVER,'src','server.js')],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
web=subprocess.Popen([sys.executable,'-m','http.server','8098','--bind','127.0.0.1','--directory',ROOT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
AUTO="""()=>{ if(window.__auto) return; window.__auto=setInterval(()=>{
  if(!G||!G.online||G.cur!==0||G.over||G.dealing||G.openPreview) return;
  const h=G.hands[0], T=G.table; let ps=allPlays(h).filter(p=>!T||beats(p,T));
  if(G.opening) ps=ps.filter(p=>p.cards.length===1&&p.cards[0].id===G.openCard.id);
  ps=ps.filter(p=>{const r=h.filter(c=>!p.cards.includes(c));return !(r.length===1&&r[0].id===51)});
  ps.sort((a,b)=>b.cards.length-a.cards.length||power(a)-power(b));
  if(ps.length){ sel.clear(); ps[0].cards.forEach(c=>sel.add(c.id)); G.confirmSpade=true; document.querySelector('#btn-play').click(); }
  else if(T) document.querySelector('#btn-pass').click();
},120); }"""

async def main():
    time.sleep(1.2)
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pages=[]; errs=[]
        for label in ['A','B']:
            ctx=await b.new_context(viewport={'width':390,'height':800},device_scale_factor=2)
            pg=await ctx.new_page(); pg.on('pageerror',lambda e,l=label:errs.append(l+': '+str(e)))
            await pg.goto('http://127.0.0.1:8098/index.html?server=ws://127.0.0.1:8099/play'); await pg.wait_for_timeout(500)
            pages.append(pg)
        A,B=pages
        for pg in pages: await pg.wait_for_function("typeof enterOnline==='function'",timeout=10000)
        await A.evaluate(f"()=>{{ enterOnline({{access_token:'{tok('aaaa-1','Ana')}',user:{{user_metadata:{{full_name:'Ana'}}}}}},false); }}")
        await B.evaluate(f"()=>{{ enterOnline({{access_token:'{tok('bbbb-2','Ben')}',user:{{user_metadata:{{full_name:'Ben'}}}}}},false); }}")
        await A.wait_for_function("NET.ready"); await B.wait_for_function("NET.ready")
        # Ben (not admin) never sees the admin options
        await B.click('#btn-lobby'); await B.click('#btn-newtable'); print('B sees admin block:', await B.evaluate("!$('#nt-admin').hidden")); await B.click('#nt-back')
        await A.click('#btn-lobby'); await A.click('#btn-newtable')
        print('A sees admin block:', await A.evaluate("!$('#nt-admin').hidden"))
        await A.evaluate("document.querySelector('#nt-admin').scrollIntoView()"); await A.screenshot(path=S+'/out/t_create_off.png')
        await A.click('#nt-tourney'); await A.click('#nt-tsize [data-v="4"]')
        await A.evaluate("()=>{const r=$('#nt-twins'); r.value=2; r.dispatchEvent(new Event('input'))}")
        await A.evaluate("document.querySelector('#btn-opentable').scrollIntoView()"); await A.screenshot(path=S+'/out/t_create_on.png')
        await A.click('#btn-opentable'); await A.wait_for_function("NET.table&&NET.table.tourney&&!$('#waiting').hidden")
        await B.wait_for_function("[...document.querySelectorAll('.tl-item')].some(b=>b.textContent.includes('tournament'))")
        await B.screenshot(path=S+'/out/t_lobby.png')
        await B.locator('.tl-item:has-text("tournament")').click(); await B.wait_for_function("NET.table&&NET.table.seats.length===2")
        await A.wait_for_function("NET.table.seats.length===2"); await A.screenshot(path=S+'/out/t_waiting.png')
        await A.click('#wr-bracket'); await A.wait_for_timeout(200); await A.screenshot(path=S+'/out/t_bracket_pre.png'); await A.click('#br-x')
        for pg in pages: await pg.evaluate(AUTO)
        await A.click('#wr-seats [data-add]'); await A.wait_for_timeout(200); await A.click('#wr-seats [data-add]')
        # wait until someone is on a decided-match summary
        await A.wait_for_function("()=>[...document.querySelectorAll('#ns-bracket')].length>0 || false",timeout=120000) if False else None
        async def done(pg):
            return await pg.evaluate("NET.table&&NET.table.tourney&&NET.table.tourney.state==='done'")
        shot=0
        for i in range(600):
            for nm,pg in (('A',A),('B',B)):
                st=await pg.evaluate("NET.table&&NET.table.summary&&NET.table.summary.champ>=0&&NET.table.tourney?NET.table.tourney.status:null")
                if st and shot<3 and not await pg.evaluate("window.__shot"):
                    await pg.evaluate("window.__shot=1"); await pg.wait_for_timeout(300)
                    await pg.screenshot(path=S+f'/out/t_summary_{nm}_{st}.png'); shot+=1
                    await pg.click('#ns-bracket'); await pg.wait_for_timeout(200); await pg.screenshot(path=S+f'/out/t_bracket_{nm}_{st}.png'); await pg.click('#br-x')
            if await done(A) or await done(B): break
            await A.wait_for_timeout(200)
        await A.wait_for_timeout(500)
        print('A status:', await A.evaluate("NET.table&&NET.table.tourney&&[NET.table.tourney.state,NET.table.tourney.status,NET.table.tourney.champion]"))
        print('B status:', await B.evaluate("NET.table&&NET.table.tourney&&[NET.table.tourney.state,NET.table.tourney.status,NET.table.tourney.champion]"))
        for nm,pg in (('A',A),('B',B)):
            if await done(pg):
                await pg.screenshot(path=S+f'/out/t_final_{nm}.png'); await pg.click('#ns-bracket'); await pg.wait_for_timeout(200); await pg.screenshot(path=S+f'/out/t_bracket_final_{nm}.png'); await pg.click('#br-x')
        for pg in pages:
            if await pg.evaluate("!!NET.table"): await pg.evaluate("NET.send({t:'leave'})")
        await A.wait_for_timeout(500)
        # 16 players: Ana + 15 CPUs; peek at the bracket mid-tournament
        await A.evaluate("show('lobby')"); await A.click('#btn-newtable'); await A.click('#nt-tsize [data-v="16"]')
        await A.evaluate("()=>{const r=$('#nt-twins'); r.value=1; r.dispatchEvent(new Event('input'))}")
        await A.click('#btn-opentable'); await A.wait_for_function("NET.table&&NET.table.max===16")
        for k in range(15): await A.evaluate("NET.send({t:'addCpu',level:1+Math.floor(Math.random()*5)})"); await A.wait_for_timeout(30)
        await A.wait_for_function("NET.table&&NET.table.max===2",timeout=10000); await A.wait_for_timeout(1500)
        await A.evaluate("openBracket()"); await A.wait_for_timeout(300); await A.screenshot(path=S+'/out/t_bracket16.png')
        print('16: rounds', await A.evaluate("NET.table.tourney.rounds.map(r=>r.length)"))
        print('page errors:', errs)
        await b.close()
try: asyncio.run(main())
finally:
    srv.terminate(); web.terminate()
    out=srv.stdout.read().decode()[-800:]; print('server log tail:', out)
