# Developing Thirteen

`dev/thirteen.html` is the **source** of the app (one file: markup, styles, game engine, online client).
Everything at the repo root is **built** from it. Never edit `index.html` by hand.

## Build and release
```bash
python3 build.py                 # dev/thirteen.html -> index.html, stamps a new version into sw.js
git add -A && git commit -m "…" && git push origin HEAD:main   # GitHub Pages serves it in about a minute
```
Installed copies pick up the new version the next time they're opened.

## The game server
Private repo `masterhastur1/thirteen-server` (Node, no dependencies), auto-deployed by Render on every push to main.
It runs the same rules engine as the app: after changing game rules or CPU logic in `dev/thirteen.html`, run
`python3 tools/extract-engine.py ../thirteen/dev/thirteen.html` in the server repo to regenerate `src/engine.js`.
Server tests: `node test/sim.js`, `node test/clock.js`, `node test/tourney.js`, `node test/strength.js 500 5 only`.

## Browser tests (`dev/browser-tests/`)
Playwright (Python) with Chrome at `/usr/bin/google-chrome`. Run `python3 build.py` first, since they test the built `index.html`.
The online tests start a local copy of the server from `../thirteen-server` (override with `THIRTEEN_SERVER=/path`),
using test-only tokens (admin = `aaaa-1`). Screenshots go to `dev/browser-tests/out/`.

| Script | Checks |
|---|---|
| `e2e_tour.py` | Admin-only tournament creation, bracket, a full 4-player and a 16-player tournament |
| `e2e_sess.py` | Session tally: a player who leaves stays on the scoreboard; Players tab current/previous sessions |
| `e2e_adm.py` | Admin screen: Invisible button hides you from the online count; All tables fold |
| `hr_test.py` | Hand ranking chart: setting, How to play button, in-game button (portrait + landscape) |
| `hold_off.py` | Offline game: 1s auto-passes, unbeatable play stays 2.7s |
