"""Kontaktówka 4 etapy × 3 warianty; kontrola granic parceli wszystkich 72 kombinacji."""
import re
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'lib/features/district/district_visual.dart').read_text().split('const _plotsByStage')[1].split('Rect? plotFor')[0]
canvas=Image.new('RGB',(1500,1200),'#101827')
for stage in range(1,5):
    block=s.split(f'  {stage}: {{')[1].split('},')[0]
    plots={k:tuple(map(float,v.split(','))) for k,v in re.findall(r"'(\w+)': Rect.fromLTWH\(([^)]+)\)",block)}
    for tier in range(1,4):
        bg=Image.open(ROOT/f'assets/images/district/ground_{stage}.jpg').convert('RGBA').resize((1000,560))
        for name,(x,y,w,h) in plots.items():
            art=Image.open(ROOT/f'assets/images/district/{name}_{tier}.png').convert('RGBA')
            art.thumbnail((int(w-12),int(h-10)),Image.Resampling.LANCZOS)
            pos=(round(x+(w-art.width)/2),round(y+h-6-art.height))
            assert pos[0]>=x and pos[1]>=y and pos[0]+art.width<=x+w and pos[1]+art.height<=y+h
            bg.alpha_composite(art,pos)
        thumb=bg.convert('RGB').resize((500,280),Image.Resampling.LANCZOS)
        ox,oy=(tier-1)*500,(stage-1)*300
        canvas.paste(thumb,(ox,oy+20));ImageDraw.Draw(canvas).text((ox+12,oy+4),f'ETAP {stage} / WARIANT {tier}',fill='white')
canvas.save(ROOT/'shots/district-art-72.jpg',quality=90)
print('PASS: 72 obrazy mieszczą się w parcelach; kontaktówka zapisana.')
