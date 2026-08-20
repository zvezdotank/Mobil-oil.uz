#!/usr/bin/env python3
"""Собирает иконки сайта из фирменного написания Mobil.

В бэйдже вкладки иконка рисуется 16x16 — слово из пяти букв там
превращается в пятно, каждая буква получает по три пикселя. Поэтому
детализация разная по размерам: в мелких иконках «Mo» с красной «о»
(узнаваемая часть написания, читается уже на 16 px), в крупной —
слово целиком.

Цвета взяты с сайта: фон #0f1113, синий #1159d4, красная «о» #da291c.

Запуск:  python3 tools/build-favicon.py
"""
import os
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC  = '/tmp/Archivo.ttf'          # переменный Archivo, тот же, что на сайте
BOLD = '/tmp/archivo-bold.ttf'

BG   = (15, 17, 19)
BLUE = (17, 89, 212)
RED  = (218, 41, 28)

MARK = [('M', BLUE), ('o', RED)]                    # для мелких размеров
WORD = [('M', BLUE), ('o', RED), ('bil', BLUE)]     # для крупных


def bold_font():
    if not os.path.exists(BOLD):
        f = instancer.instantiateVariableFont(TTFont(SRC), {'wght': 700, 'wdth': 100})
        f.save(BOLD)
    return BOLD


def icon(size, parts, ratio, radius=0):
    """Рисуем в восемь раз крупнее и уменьшаем — так края выходят чище."""
    S = size * 8
    im = Image.new('RGBA', (S, S), BG + (255,))
    d = ImageDraw.Draw(im)
    if radius:
        m = Image.new('L', (S, S), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, S - 1, S - 1], radius * 8, fill=255)
        im.putalpha(m)
    txt = ''.join(p[0] for p in parts)
    fnt = ImageFont.truetype(bold_font(), int(S * ratio))
    w = d.textlength(txt, font=fnt)
    box = d.textbbox((0, 0), txt, font=fnt)
    x = (S - w) / 2
    y = (S - (box[3] - box[1])) / 2 - box[1]
    for chunk, col in parts:
        d.text((x, y), chunk, font=fnt, fill=col + (255,))
        x += d.textlength(chunk, font=fnt)
    return im.resize((size, size), Image.LANCZOS)


def build():
    out = os.path.join(ROOT, 'img')
    # вкладка браузера: «Mo»
    sizes = [16, 32, 48, 64]
    ico = [icon(s, MARK, 0.55) for s in sizes]
    ico[0].save(os.path.join(ROOT, 'favicon.ico'), format='ICO',
                sizes=[(s, s) for s in sizes], append_images=ico[1:])
    icon(96, MARK, 0.55).save(os.path.join(out, 'favicon-96.png'))

    # ярлык на телефоне и крупные превью: слово целиком
    icon(180, WORD, 0.30).convert('RGB').save(os.path.join(out, 'apple-touch-icon.png'))
    icon(512, WORD, 0.30).convert('RGB').save(os.path.join(out, 'icon-512.png'))

    for p in ('favicon.ico', 'img/favicon-96.png', 'img/apple-touch-icon.png', 'img/icon-512.png'):
        print(f'  {p:28} {os.path.getsize(os.path.join(ROOT, p)):>6} байт')


if __name__ == '__main__':
    build()
