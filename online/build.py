"""Bundle the browser UI. index.html still requires the same-origin API server."""
from pathlib import Path
p=Path(__file__).resolve().parent/'web'
html=(p/'template.html').read_text()
for marker,filename in [('STYLE','style.css'),('GAMECSS','game.css'),('ONLINECSS','online.css'),('ENGINE','engine.js'),('FX','effects.js'),('APP','app.js'),('GAMECORE','game-core.js'),('AVATAR','avatar.js'),('NETWORK','network.js'),('EXTRAS','extras.js'),('GAMEUI','online-game.js')]:
 html=html.replace('/*__'+marker+'__*/',(p/filename).read_text())
assert '/*__' not in html,'Unresolved build marker'
(p/'index.html').write_text(html)
print('Built network UI:',p/'index.html')
