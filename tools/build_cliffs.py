"""Builds assets/tiles/cliffs.png: seamless cliff pieces for game.js (palette sampled from the embedded tilesets).

Layout (world px, 1 tile = 48):
  face  x   0..191, y 0..119  south cliff face, 4 tiles wide, wraps horizontally (tile i uses slice i % 4)
  side  x 192..207, y 0..191  east-coast rock edge, 4 tiles tall, wraps vertically (tile j uses slice j % 4; flipped for west)
  cap   x 208..223, y 0..119  outer corner where a south face run ends on the east (flipped for west)
Every piece is generated with wrap-around noise, so neighbouring slices always share identical edges.
Usage: python3 tools/build_cliffs.py   (deterministic; rerun after tweaking constants)
"""
import random
from pathlib import Path
from PIL import Image

T, FW, FH, SW, SH = 48, 192, 120, 16, 192
LIP, ROCK_BOTTOM = 9, 100
OUT = Path(__file__).resolve().parent.parent / 'assets' / 'tiles' / 'cliffs.png'

hexc = lambda h, a=255: (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)
GRASS = [hexc(c) for c in ('#8cc512', '#78c30c', '#73b909', '#8aba11', '#93c726', '#91d317')]
GRASS_EDGE, GRASS_DARK = hexc('#52760c'), hexc('#3d5a08')
ROCK = [hexc(c) for c in ('#424957', '#3c4352', '#303848')]
ROCK_LIGHT, ROCK_TOP, ROCK_SHADE = hexc('#515866'), hexc('#6f7684'), hexc('#232b3b')
CREVICE, OUTLINE = hexc('#0e192c'), hexc('#010817')
FOAM, FOAM2, SURF = hexc('#ffffff'), hexc('#6bd8f7'), (0x2e, 0xb8, 0xf0)

rng = random.Random(1745)


def shade(c, k):
    return (max(0, min(255, int(c[0] * k))), max(0, min(255, int(c[1] * k))), max(0, min(255, int(c[2] * k))), c[3])


def wrap_noise(n, lo, hi, step):
    """Smooth-ish integer noise of length n that wraps (value[n] == value[0])."""
    keys = [rng.randint(lo, hi) for _ in range(n // step)]
    out = []
    for i in range(n):
        a, b = keys[(i // step) % len(keys)], keys[(i // step + 1) % len(keys)]
        out.append(round(a + (b - a) * (i % step) / step))
    return out


def partition(n, lo, hi):
    """Split n into widths in [lo, hi] that sum exactly to n."""
    ws = []
    while sum(ws) < n:
        ws.append(rng.randint(lo, hi))
    over = sum(ws) - n
    while over:
        k = rng.randrange(len(ws))
        if ws[k] > lo:
            ws[k] -= 1
            over -= 1
    return ws


def grass(px, x, y):
    px[x, y] = GRASS[(x * 7 + y * 13 + rng.randint(0, 2)) % len(GRASS)] if rng.random() < .55 else GRASS[0]


def surf_alpha(d, length):
    return int(150 * max(0.0, 1 - d / length) ** 1.5)


def build_face(img):
    px = img.load()
    lip = wrap_noise(FW, LIP - 2, LIP + 3, 4)
    bottoms, x = [], 0
    for w in partition(FW, 6, 12):                                   # basalt columns
        tone, b = rng.choice(ROCK), ROCK_BOTTOM + rng.randint(-2, 2)
        joints = sorted(rng.sample(range(LIP + 16, b - 14), rng.randint(1, 2)))
        for xx in range(x, x + w):
            bottoms.append(b)
            for y in range(FH):
                if y < lip[xx] or y >= b:
                    continue
                c = tone
                if xx == x: c = CREVICE                              # crevice between columns
                elif xx == x + 1: c = ROCK_LIGHT                     # lit left edge
                elif xx >= x + w - 2: c = ROCK_SHADE                 # shaded right edge
                for jy in joints:                                    # horizontal breaks: dark seam + lit step
                    if y == jy: c = CREVICE
                    elif jy < y <= jy + 2 and xx not in (x,): c = ROCK_TOP if y == jy + 1 else ROCK_LIGHT
                if y < lip[xx] + 4: c = shade(c, .55 + .1 * (y - lip[xx]))   # occlusion under the grass lip
                if y > b - 8: c = shade(c, .85)                      # wet base
                if rng.random() < .04 and c not in (CREVICE,): c = shade(c, .8)
                px[xx, y] = c
        x += w
    for xx in range(FW):                                             # grass lip with a dark hanging edge
        for y in range(lip[xx]):
            grass(px, xx, y)
        px[xx, lip[xx] - 1] = GRASS_EDGE
        if rng.random() < .25: px[xx, lip[xx]] = GRASS_DARK          # little hanging tufts
        b = bottoms[xx]                                              # foam line hugging each column base, then fading surf
        px[xx, b - 1] = FOAM2
        px[xx, b] = FOAM if rng.random() < .8 else FOAM2
        px[xx, b + 1] = FOAM2
        for d in range(2, 14):
            if b + d < FH:
                px[xx, b + d] = (*SURF, surf_alpha(d - 2, 12))


def build_side(img, ox):
    px = img.load()
    edge = wrap_noise(SH, 2, 4, 6)                                   # grass overhang width per row
    rock = wrap_noise(SH, 11, 13, 8)                                  # where the rock ends and the surf starts
    breaks, y = [], 0
    for h in partition(SH, 7, 14):
        breaks.append(y)
        y += h
    for y in range(SH):
        tone = ROCK[(sum(1 for b in breaks if b <= y)) % len(ROCK)]
        for x in range(SW):
            if x < edge[y]:
                grass(px, ox + x, y)
                if x == edge[y] - 1: px[ox + x, y] = GRASS_EDGE
            elif x < rock[y]:
                c = tone
                if y in breaks: c = CREVICE
                elif y - 1 in breaks: c = ROCK_TOP
                if x == edge[y]: c = shade(c, .6)
                if x == rock[y] - 1: c = ROCK_SHADE
                px[ox + x, y] = c
            elif x == rock[y]:
                px[ox + x, y] = FOAM if rng.random() < .8 else FOAM2
            else:
                px[ox + x, y] = (*SURF, surf_alpha(x - rock[y] - 1, SW - rock[y]))


def build_cap(img, ox):
    """East end of a south face: the rock wraps round the corner and the surf curls round its foot."""
    px = img.load()
    for y in range(FH):
        if y < LIP:
            e = 3
            for x in range(e):
                grass(px, ox + x, y)
            px[ox + e - 1, y] = GRASS_EDGE
            continue
        fade = max(0, (y - (ROCK_BOTTOM - 22)) / 22)                 # corner rounds off toward the water
        r = round(10 - 6 * fade * fade)
        for x in range(SW):
            if y < ROCK_BOTTOM and x < r:
                c = ROCK_SHADE if x >= r - 2 else ROCK[1]
                if x == 0: c = CREVICE
                if (y - LIP) % 13 == 0: c = CREVICE
                elif (y - LIP) % 13 == 1: c = ROCK_LIGHT
                px[ox + x, y] = shade(c, .8)
            elif y < ROCK_BOTTOM and x == r:
                px[ox + x, y] = FOAM
            elif y < ROCK_BOTTOM + 14:
                d = max(x - r - 1, y - ROCK_BOTTOM) if y >= ROCK_BOTTOM else x - r - 1
                if y == ROCK_BOTTOM and x <= r: px[ox + x, y] = FOAM
                else: px[ox + x, y] = (*SURF, surf_alpha(d, 12))


def main():
    img = Image.new('RGBA', (FW + 2 * SW, SH), (0, 0, 0, 0))
    build_face(img)
    build_side(img, FW)
    build_cap(img, FW + SW)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
