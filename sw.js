/* Thirteen service worker: the app works offline, and each new build replaces the old cache. */
const VERSION='20261103-132117';
const CACHE='thirteen-'+VERSION;
const CORE=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','maskable-512.png','apple-touch-icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'];

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(CORE.map(u=>c.add(new Request(u,{cache:'reload'})).catch(()=>{})))).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('thirteen-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET') return;
  const url=new URL(req.url);
  // The game page: try the network first so updates arrive, fall back to the cached copy offline.
  if(req.mode==='navigate'||(url.origin===location.origin&&url.pathname.endsWith('.html'))){
    e.respondWith(fetch(req).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put('index.html',copy));return r}).catch(()=>caches.match('index.html')));
    return;
  }
  // Everything else (icons, fonts, PDF library): cache first, then network, keeping a copy.
  e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(r=>{
    if(r&&(r.ok||r.type==='opaque')){const copy=r.clone();caches.open(CACHE).then(c=>c.put(req,copy))}
    return r;
  })));
});
