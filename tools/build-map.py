#!/usr/bin/env python3
"""Рисует схемы проезда в стиле сайта: img/map.svg и img/map-mobile.svg.

Данные: OpenStreetMap через Overpass API (кэшируются в tools/osm-*.json,
чтобы не дёргать сервер при каждой правке оформления).

Карта рисуется сразу в тех пикселях, в которых показывается на сайте,
иначе подписи ужимаются вместе с картинкой и становятся нечитаемыми.
Отсюда два варианта: широкий кадр 9 км для десктопа (влезают все шесть
станций метро и магистрали) и узкий 6 км для телефона, где под карту
всего ~340 px ширины.

Запуск:  python3 tools/build-map.py
"""
import json, math, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LAT, LON = 41.263343, 69.315835        # склад и сервис, Ферганское шоссе, 570

# (файл, ширина px, высота px, ширина кадра в метрах)
PROFILES = [('map.svg', 760, 400, 9000),
            ('map-mobile.svg', 380, 380, 6000)]

W = H = MW = KM = DLON = DLAT = None    # задаются профилем в build()
MLON = 111320 * math.cos(math.radians(LAT))
MLAT = 111132

BG = '#0f1113'
ACTION = '#1159d4'

# слои: чем выше order, тем позже рисуется
TIER = {
    'motorway':     (4, 1.7,  '#7c878e'),
    'trunk':        (4, 1.7,  '#7c878e'),
    'primary':      (3, 1.2,  '#59626a'),
    'secondary':    (2, 0.75, '#394147'),
    'tertiary':     (1, 0.6,  '#2b3237'),
    'residential':  (0, 0.5,  '#242a2e'),
    'unclassified': (0, 0.5,  '#242a2e'),
}

# подписываем только то, по чему ориентируются; остальное — фон
LABEL = ['Ферганское шоссе', 'Ханабадтепа проспект', 'Ахангаранское шоссе',
         'Малая кольцевая дорога', 'Ташкентская кольцевая автодорога']
SHORT = {'Ташкентская кольцевая автодорога': 'Ташкентская кольцевая'}

QUERIES = {
    'osm-major.json': '''[out:json][timeout:90];
(
  way["highway"~"^(motorway|trunk|primary|secondary)$"]({bbox});
  node["station"="subway"]({bbox});
  way["waterway"="river"]({bbox});
);
out geom;''',
    'osm-minor.json': '''[out:json][timeout:90];
(
  way["highway"~"^(tertiary|residential|unclassified)$"]({bbox});
);
out geom;''',
}


def bbox():
    """Один кэш на все профили — качаем по самому широкому кадру."""
    w = max(p[3] for p in PROFILES)
    dlon = (w / 2) / MLON
    dlat = (w / 2 / max(p[1] / p[2] for p in PROFILES)) / MLAT
    return f'{LAT-dlat:.4f},{LON-dlon:.4f},{LAT+dlat:.4f},{LON+dlon:.4f}'


def fetch(name, query):
    """Скачивает и кэширует ответ Overpass. Сервер бывает занят — повторяем."""
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        return json.load(open(path))
    body = query.format(bbox=bbox()).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                'https://overpass-api.de/api/interpreter', data=body,
                headers={'User-Agent': 'mobil-oil.uz map builder'})
            data = json.loads(urllib.request.urlopen(req, timeout=120).read())
            json.dump(data, open(path, 'w'))
            return data
        except Exception as e:
            print(f'  Overpass занят ({e}), жду и пробую ещё раз', file=sys.stderr)
            time.sleep(20)
    sys.exit('Overpass не ответил — попробуйте позже')


def px(lon, lat):
    return ((lon - (LON - DLON)) / (2 * DLON) * W,
            (((LAT + DLAT) - lat)) / (2 * DLAT) * H)


def visible(x, y, m=30):
    return -m < x < W + m and -m < y < H + m


def thin(pts, eps):
    """Прореживание: точки ближе eps пикселей схлопываем в одну."""
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= eps:
            out.append(p)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def collect():
    els = []
    for name, q in QUERIES.items():
        els += fetch(name, q)['elements']

    roads, rivers, metro, named = [], [], [], {}
    for e in els:
        tags = e.get('tags', {})
        if tags.get('station') == 'subway':
            x, y = px(e['lon'], e['lat'])
            if visible(x, y, -16):
                metro.append([x, y, tags.get('name:ru') or tags.get('name')])
            continue
        geom = e.get('geometry')
        if not geom:
            continue
        hw = tags.get('highway')
        river = tags.get('waterway') == 'river'
        if not river and hw not in TIER:
            continue
        faint = not river and TIER[hw][0] < 2
        run = []
        for p in [px(g['lon'], g['lat']) for g in geom] + [None]:
            if p and visible(*p):
                run.append(p)
                continue
            if len(run) > 1:
                eps = 5.0 if faint else (1.6 if hw == 'secondary' else 0.9)
                pts = thin(run, eps)
                if len(pts) > 1:
                    fmt = '{:.0f} {:.0f}'
                    d = 'M' + ' L'.join(fmt.format(x, y) for x, y in pts)
                    if river:
                        rivers.append(d)
                    else:
                        roads.append((TIER[hw], d))
                        n = tags.get('name:ru') or tags.get('name')
                        if n in LABEL:
                            named.setdefault(n, []).extend(zip(run, run[1:]))
            run = []
    roads.sort(key=lambda r: r[0][0])
    return roads, rivers, metro, named


def text(x, y, s, fill, size=12, anchor='middle', dy=0, rot=None,
         family='JetBrains Mono,monospace', weight=None, halo=4):
    a = [f'<text x="{x:.0f}" y="{y:.0f}"']
    if rot is not None:
        a.append(f'transform="rotate({rot:.1f} {x:.0f} {y:.0f})"')
    if dy:
        a.append(f'dy="{dy}"')
    a.append(f'fill="{fill}" text-anchor="{anchor}" font-family="{family}" font-size="{size}"')
    if weight:
        a.append(f'font-weight="{weight}"')
    if halo:
        a.append(f'paint-order="stroke" stroke="{BG}" stroke-width="{halo}" stroke-linejoin="round"')
    return ' '.join(a) + f'>{esc(s)}</text>'


def build(filename, w, h, frame):
    global W, H, MW, KM, DLON, DLAT
    W, H, MW = w, h, frame
    KM = W / MW * 1000
    DLON = (MW / 2) / MLON
    DLAT = (MW / 2 / (W / H)) / MLAT

    roads, rivers, metro, named = collect()
    cx, cy = px(LON, LAT)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Где мы находимся: Ферганское шоссе, 570, Мирабадский район Ташкента">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    for d in rivers:
        out.append(f'<path d="{d}" fill="none" stroke="#1d2f37" stroke-width="2" stroke-linecap="round"/>')
    for (_, w, c), d in roads:
        out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}" '
                   f'stroke-linecap="round" stroke-linejoin="round"/>')

    # В узкий кадр подпись сбоку от маркера не помещается — уводим её вниз.
    side = cx + 32 + 155 < W - 8

    # занятые подписями места — прямоугольниками (x, y, полуширина, полувысота),
    # чтобы повёрнутая вдоль улицы строка считалась вертикальной, а не горизонтальной
    taken = [(cx + 95, cy + 6, 110, 16) if side else (cx, cy + 34, 85, 24),
             (cx, cy, 30, 30)]                       # кружок маркера со свечением
    def free(x, y, hw, hh=7):
        return all(not (abs(x - a) < hw + c and abs(y - b) < hh + d) for a, b, c, d in taken)

    # Станции подписываем первыми: их место задано точкой на местности,
    # а у улицы вариантов много — пусть уступает она.
    metro.sort(key=lambda m: m[0])
    metro_out = []
    for x, y, name in metro:
        label = 'М ' + name
        half = len(label) * 3.6 + 6
        # пробуем: над точкой, справа, слева, под точкой
        spots = [(x, y - 11, 'middle'), (x + half + 7, y + 4, 'start'),
                 (x - half - 7, y + 4, 'end'), (x, y + 18, 'middle')]
        inframe = [s for s in spots if half + 6 < s[0] < W - half - 6 and 12 < s[1] < H - 8]
        pick = next((s for s in inframe if free(s[0], s[1], half)),
                    inframe[0] if inframe else spots[0])
        bx, ly, anchor = pick
        lx = bx if anchor == 'middle' else (bx - half if anchor == 'start' else bx + half)
        taken.append((bx, ly, half, 7))
        metro_out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{BG}" '
                         f'stroke="#9aa2a8" stroke-width="1.3"/>')
        metro_out.append(text(lx, ly, label, '#9aa2a8', anchor=anchor))

    # подписи улиц — вдоль самого длинного свободного видимого отрезка
    for name in LABEL:
        if name not in named:
            continue
        label = SHORT.get(name, name)
        half = len(label) * 3.6 + 6
        best = None
        for (x1, y1), (x2, y2) in named[name]:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            a = math.atan2(y2 - y1, x2 - x1)
            ex = abs(half * math.cos(a))             # габарит повёрнутой строки
            ey = abs(half * math.sin(a)) + 5
            if not (ex + 10 < mx < W - ex - 10 and ey + 8 < my < H - ey - 26):
                continue
            if not free(mx, my, ex + 2, ey + 2):
                continue
            score = math.hypot(x2 - x1, y2 - y1) - .05 * abs(my - H / 2)
            if best is None or score > best[0]:
                best = (score, mx, my, math.degrees(a), ex, ey)
        if not best:
            continue
        _, mx, my, ang, ex, ey = best
        taken.append((mx, my, ex, ey))
        ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
        out.append(text(mx, my, label, '#828c93', dy=-5, rot=ang))

    out += metro_out

    # наша точка
    out += [f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="26" fill="{ACTION}" opacity=".13"/>',
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="14" fill="none" stroke="{ACTION}" stroke-width="1.3" opacity=".85"/>',
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="6" fill="{ACTION}"/>',
            text(cx + 32 if side else cx, cy - 1 if side else cy + 30, 'Mobil Uzbekistan',
                 '#edeae5', size=17, anchor='start' if side else 'middle',
                 family='Archivo,Helvetica,sans-serif', weight=600, halo=5),
            text(cx + 32 if side else cx, cy + 16 if side else cy + 47, 'Ферганское шоссе, 570',
                 '#9aa2a8', anchor='start' if side else 'middle', halo=5)]

    # масштаб и копирайт
    x0 = W - 24 - KM
    out += [f'<g stroke="#4d565c" stroke-width="1.2" fill="none">'
            f'<path d="M{x0:.0f} {H-22}h{KM:.0f}"/><path d="M{x0:.0f} {H-26}v8"/>'
            f'<path d="M{x0+KM:.0f} {H-26}v8"/></g>',
            text(x0 + KM / 2, H - 31, '1 км', '#4d565c', halo=0),
            text(12, H - 12, '© OpenStreetMap', '#3a4349', size=11, anchor='start', halo=4),
            '</svg>']

    path = os.path.join(ROOT, 'img', filename)
    open(path, 'w').write('\n'.join(out))
    print(f'{filename}: {W}x{H}, кадр {MW/1000:g} км, {len(roads)} линий, '
          f'{len(metro)} станций, {os.path.getsize(path)//1024} КБ')


if __name__ == '__main__':
    for profile in PROFILES:
        build(*profile)
