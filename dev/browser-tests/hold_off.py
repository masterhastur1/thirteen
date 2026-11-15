import asyncio, subprocess, time, os
from playwright.async_api import async_playwright
S=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.path.join(S,'..','..'))   # the built app (run build.py first)
SERVER=os.environ.get('THIRTEEN_SERVER',os.path.join(ROOT,'..','thirteen-server'))
os.makedirs(S+'/out',exist_ok=True)
web=subprocess.Popen(['python3','-m','http.server','8098','-d',ROOT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
async def main():
    time.sleep(1)
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await (await b.new_context(viewport={'width':390,'height':800},device_scale_factor=2)).new_page(); errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8098/index.html'); await pg.wait_for_timeout(800)
        # offline game vs 3 CPUs, quick pace; record timings of auto passes and holds
        await pg.evaluate("""()=>{ settings.pace='quick'; window.__ev=[]; const op=doPass; doPass=function(i,a){ if(a) __ev.push(['auto',performance.now()]); return op.apply(this,arguments); };
          setInterval(()=>{ if(G&&G.hold&&!window.__h){ window.__h=performance.now(); __ev.push(['hold',__h]); } if(G&&!G.hold&&window.__h){ __ev.push(['clear',performance.now()]); window.__h=0; } },20);
          // you: always pass or play the lowest legal option so the game moves on
          setInterval(()=>{ if(G&&!G.over&&G.cur===0&&!G.dealing&&!G.openPreview&&!G.hold){ const ps=allPlays(G.hands[0],G.table,G.opening?G.openCard:null); if(ps.length) { doPlay(0,ps[0]); } else doPass(0,false); } },300); }""")
        await pg.evaluate("(newMatch(),show('game'),deal())")
        await pg.wait_for_timeout(500)
        print('started:', await pg.evaluate("!!G"))
        for i in range(120):
            await pg.wait_for_timeout(1000)
            n=await pg.evaluate("__ev.filter(e=>e[0]==='clear').length")
            if n>=1: break
        await pg.screenshot(path=S+'/out/hold.png') 
        print(await pg.evaluate("""(()=>{ const ev=__ev; const out=[]; for(let k=0;k<ev.length;k++){ if(ev[k][0]==='hold'){ const c=ev.slice(k).find(e=>e[0]==='clear'); const autos=ev.slice(0,k).filter(e=>e[0]==='auto').slice(-3).map(e=>e[1]); out.push({hold_ms: c?Math.round(c[1]-ev[k][1]):null, gaps_between_autos: autos.slice(1).map((t,j)=>Math.round(t-autos[j]))}); } } return JSON.stringify(out.slice(0,3)); })()"""))
        print('errors:', errs)
        await b.close()
try: asyncio.run(main())
finally: web.terminate()
