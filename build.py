"""Build the installable Thirteen web app from the shared game source.

Usage: python3 build.py            (reads dev/thirteen.html)
       python3 build.py path/to/thirteen.html
Writes index.html (full document + app manifest + offline support) and stamps sw.js with a new version,
so installed copies pick up the update on their next launch.
"""
import sys, re, time, pathlib

here = pathlib.Path(__file__).parent
src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else here / 'dev' / 'thirteen.html').read_text()

title = re.search(r'<title>.*?</title>\n?', src).group(0)
body = src.replace(title, '', 1).replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
version = time.strftime('%Y%m%d-%H%M%S')

head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{title.strip()}
<meta name="theme-color" content="#0c100d">
<meta name="description" content="Thirteen: a spades-high shedding card game for 2 to 4 players.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
:root{{color-scheme:dark;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
html,body{{height:100%}}
body{{margin:0;font:14px system-ui,sans-serif}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
</head>
<body>
"""

tail = f"""
<script>
/* Offline support + automatic updates (build {version}) */
if('serviceWorker' in navigator){{
  window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{{}}));
  let reloaded=false;
  navigator.serviceWorker.addEventListener('controllerchange',()=>{{
    // a new version took over: reload only while no game is in progress
    if(reloaded) return;
    if(typeof G==='undefined'||!G||G.over){{reloaded=true;location.reload()}}
  }});
}}
</script>
</body>
</html>
"""

(here / 'index.html').write_text(head + body + tail)
sw = (here / 'sw.js').read_text()
(here / 'sw.js').write_text(re.sub(r"const VERSION='[^']*'", f"const VERSION='{version}'", sw))
print('built', version)
