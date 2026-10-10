"""M5: przygotowanie trzech arkuszy budynków (3 × 2), bez zmiany mechaniki poziomów."""
from pathlib import Path
from PIL import Image
from cut_bg import cut
ROOT = Path(__file__).resolve().parents[1]
ORDER = ['residence', 'cafe', 'nightclub', 'garage', 'club', 'hall']
for tier in range(1, 4):
    image = Image.open(ROOT / f'art_src/district/sheet_aligned_{tier}.jpg')
    w, h = image.size
    for i, name in enumerate(ORDER):
        x, y = i % 3, i // 3
        cell = image.crop((round(x*w/3)+4, round(y*h/2)+4, round((x+1)*w/3)-4, round((y+1)*h/2)-4))
        tmp = ROOT / f'art_src/district/crop_{name}_{tier}.jpg'
        cell.save(tmp, quality=97)
        cut(str(tmp), str(ROOT / f'assets/images/district/{name}_{tier}.png'), 420, 20)
        tmp.unlink()
