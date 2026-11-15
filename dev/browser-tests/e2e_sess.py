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
        await A.click('#btn-lobby'); await A.click('#btn-newtable')
        await A.evaluate("draft.tourney=false; draft.seats=4; draft.match='endless'; renderNewTable()")
        await A.click('#btn-opentable'); await A.wait_for_function("NET.table&&!$('#waiting').hidden")
        await B.click('#btn-lobby'); await B.wait_for_timeout(300)
        tid=await A.evaluate("NET.table.id"); await B.evaluate(f"NET.send({{t:'join',id:'{tid}'}})"); await B.wait_for_function("NET.table&&NET.table.seats.length===2")
        await A.click('#wr-seats [data-add]'); await A.wait_for_timeout(200); await A.click('#wr-seats [data-add]')
        for pg in pages: await pg.evaluate(AUTO)
        await B.wait_for_function("NET.table&&NET.table.state==='summary'",timeout=120000)
        print('dbg', await A.evaluate("JSON.stringify([NET.table.rules,NET.table.state,!!NET.table.session])"))
        print('session after game 1:', await A.evaluate("JSON.stringify(NET.table.session.rows.map(r=>[r.name,r.net,r.here]))"))
        await B.evaluate("NET.send({t:'leave'})")
        # wait for A's next summary (game 2)
        await A.wait_for_function("NET.table&&NET.table.state==='playing'",timeout=60000)
        await A.wait_for_function("NET.table&&NET.table.state==='summary'",timeout=120000)
        await A.evaluate("NET.ws.onmessage=null"); await A.wait_for_timeout(400)
        print('session after game 2:', await A.evaluate("JSON.stringify(NET.table.session.rows.map(r=>[r.name,r.net,r.here]))"))
        print('gone rows on scoreboard:', await A.evaluate("document.querySelectorAll('.results tr.gone').length"))
        await A.screenshot(path=S+'/out/s_summary.png')
        # profile → Players tab while seated (current session)
        await A.evaluate("$('#overlay').hidden=true; show('profile')"); await A.wait_for_timeout(200)
        await A.screenshot(path=S+'/out/s_dbg.png')
        await A.evaluate("document.querySelector('[data-pf=\"players\"],[data-v=\"players\"]').click()"); await A.wait_for_timeout(300)
        await A.screenshot(path=S+'/out/s_players_live.png')
        await A.evaluate("NET.send({t:'leave'}); NET.table=null; NET.lobby=[]"); await A.wait_for_timeout(500)
        await A.evaluate("show('profile'); renderPlayers(true)"); await A.wait_for_timeout(200)
        await A.evaluate("document.querySelector('details.ss')&&(document.querySelector('details.ss').open=true)"); await A.wait_for_timeout(100)
        await A.screenshot(path=S+'/out/s_players_prev.png')
        print('B stored sessions:', await B.evaluate("loadSessions().length"))
        print('page errors:', errs)
        await b.close()
try: asyncio.run(main())
finally:
    srv.terminate(); web.terminate()
