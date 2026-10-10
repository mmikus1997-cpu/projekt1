"""Wycięcie jednolitego jasnego tła z grafiki budynku (flood fill od krawędzi) → PNG z przezroczystością, przycięty do zawartości.
Użycie: python3 tools/cut_bg.py wejście.png wyjście.png [max_szerokość]"""
import sys
from collections import deque
from PIL import Image, ImageFilter

def cut(src, dst, maxw=420, tol=34):
    im = Image.open(src).convert('RGBA')
    w, h = im.size
    px = im.load()
    bg = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ref = tuple(sum(c[i] for c in bg) // 4 for i in range(3))
    def near(c): return abs(c[0] - ref[0]) + abs(c[1] - ref[1]) + abs(c[2] - ref[2]) <= tol * 3
    seen = bytearray(w * h)
    q = deque((x, y) for x in range(w) for y in (0, h - 1))
    q.extend((x, y) for y in range(h) for x in (0, w - 1))
    mask = Image.new('L', (w, h), 255); m = mask.load()
    while q:
        x, y = q.popleft()
        i = y * w + x
        if seen[i]: continue
        seen[i] = 1
        if not near(px[x, y]): continue
        m[x, y] = 0
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]: q.append((nx, ny))
    # zamknięte „dziury” tła (np. biel między palmami): duże, niemal czysto białe skupiska → przezroczyste
    def white(c): return min(c[0], c[1], c[2]) >= 238
    for sy in range(0, h, 2):
        for sx in range(0, w, 2):
            i = sy * w + sx
            if seen[i] or not white(px[sx, sy]): continue
            comp = []; dq = deque([(sx, sy)]); seen[i] = 1
            while dq:
                x, y = dq.popleft(); comp.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and white(px[nx, ny]):
                        seen[ny * w + nx] = 1; dq.append((nx, ny))
            if len(comp) >= 350:
                for x, y in comp: m[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))  # gładka krawędź bez białej obwódki
    im.putalpha(mask)
    im = im.crop(mask.getbbox())
    if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    im.save(dst, optimize=True)
    return im.size

if __name__ == '__main__':
    print(cut(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 420))
