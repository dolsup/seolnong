#!/usr/bin/env python3
"""Build the release font from the shared drawing functions."""
from __future__ import annotations
import math
from pathlib import Path
import unicodedata
from datetime import datetime, timezone

from . import design
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.otBase import USE_HARFBUZZ_REPACKER
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

UPM = 1000
FAMILY, STYLE = 'Seolnong', 'Regular'
KOREAN_FAMILY = '설농체'
VERSION = '1.001'
POSTSCRIPT = 'Seolnong-Regular'
COPYRIGHT = 'Copyright (c) 2026 dolsup (https://github.com/dolsup/seolnong)'
LICENSE_DESCRIPTION = ('This Font Software is licensed under the SIL Open Font License, '
                       'Version 1.1. See OFL.txt or https://openfontlicense.org.')
RELEASE_TIMESTAMP = int(datetime(2026, 11, 15, tzinfo=timezone.utc).timestamp()) + 2082844800
SBASE, SCOUNT = 0xAC00, 11172
ASCENT, DESCENT = 900, -250
CAP_CONSONANTS = frozenset({'h', 'ch'})


def contains_cap(name, design):
    if name in design.PAIRS:
        return any(contains_cap(part, design) for part in design.PAIRS[name])
    return name in CAP_CONSONANTS


def alternate_jamos(design):
    for kind, names in [('L', design.L_NAMES), ('T', design.T_NAMES)]:
        for index, name in enumerate(names):
            if contains_cap(name, design):
                yield f'jamo{kind}{index:02d}', kind, index


def affected_glyphs(design):
    leading = {i for i, name in enumerate(design.L_NAMES) if contains_cap(name, design)}
    trailing = {i for i, name in enumerate(design.T_NAMES) if contains_cap(name, design)}
    for name, kind, index in alternate_jamos(design):
        yield name, 'draw_jamo', (kind, index)
    for cp in range(SBASE, SBASE + SCOUNT):
        l, rem = divmod(cp-SBASE, 21*28)
        v, t = divmod(rem, 28)
        if l in leading or t in trailing:
            yield f'uni{cp:04X}', 'draw_syllable', (l, v, t)


def draw_empty(pen):
    pass


def draw_notdef(pen):
    pen.moveTo((110, 0))
    for point in [(890, 0), (890, 800), (110, 800)]:
        pen.lineTo(point)
    pen.closePath()
    pen.moveTo((160, 50))
    for point in [(160, 750), (840, 750), (840, 50)]:
        pen.lineTo(point)
    pen.closePath()


def draw_dotted_circle(pen):
    k = 0.5522847498307936
    for i in range(16):
        angle = 2 * math.pi * i / 16
        x, y, r = 500+310*math.cos(angle), 420+310*math.sin(angle), 18
        pen.moveTo((x+r, y))
        pen.curveTo((x+r,y+k*r), (x+k*r,y+r), (x,y+r))
        pen.curveTo((x-k*r,y+r), (x-r,y+k*r), (x-r,y))
        pen.curveTo((x-r,y-k*r), (x-k*r,y-r), (x,y-r))
        pen.curveTo((x+k*r,y-r), (x+r,y-k*r), (x+r,y))
        pen.closePath()


def make_glyph(draw, *args, form=None):
    pen = TTGlyphPen(None)
    converted = Cu2QuPen(pen, max_err=0.45, reverse_direction=False)
    if form is None:
        advance = draw(*args, converted)
    else:
        advance = draw(*args, converted, form=form)
    return pen.glyph(), advance


def compat_jamo(cp):
    if cp == 0x3140:
        return 'T', 15
    if cp == 0x3144:
        return 'T', 18
    j = ord(unicodedata.normalize('NFKD', chr(cp))[0])
    if 0x1100 <= j <= 0x1112:
        return 'L', j-0x1100
    if 0x1161 <= j <= 0x1175:
        return 'V', j-0x1161
    if 0x11A8 <= j <= 0x11C2:
        return 'T', j-0x11A7
    raise ValueError(f'Unrecognized compatibility Jamo U+{cp:04X}')


def feature_source(pairs):
    return '\n'.join([
        'languagesystem DFLT dflt;',
        'languagesystem hang dflt;',
        'feature ss01 {',
        '  featureNames {',
        '    name "Upright Caps";',
        '    name 3 1 1042 "세로 꼭지 ㅎ·ㅊ";',
        '  };',
        *[f'  sub {base} by {alternate};' for base, alternate in pairs],
        '} ss01;',
    ]) + '\n'


def build(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    glyphs, cmap, advances = {}, {}, {}

    def add(name, draw, args=(), advance=1000, codepoints=(), form=None):
        glyph, returned = make_glyph(draw, *args, form=form)
        glyphs[name] = glyph
        if isinstance(returned, (int, float)) and returned > 0:
            advance = round(returned)
        advances[name] = advance
        for cp in codepoints:
            cmap[cp] = name

    add('.notdef', draw_notdef)
    add('space', draw_empty, advance=500, codepoints=(0x20,0xA0))
    add('emspace', draw_empty, advance=1000, codepoints=(0x2003,))
    add('thinspace', draw_empty, advance=200, codepoints=(0x2009,0x202F))
    add('zerowidth', draw_empty, advance=0,
        codepoints=(0x200B,0x200C,0x200D,0x2060,0xFEFF))
    add('uni25CC', draw_dotted_circle, codepoints=(0x25CC,))
    for cp in range(0x21, 0x7F):
        add(f'uni{cp:04X}', design.draw_ascii, (chr(cp),), advance=600,
            codepoints=(cp,))
    for cp in getattr(design, 'EXTRA_CODEPOINTS', ()):
        if cp not in cmap:
            add(f'uni{cp:04X}', design.draw_ascii, (chr(cp),), codepoints=(cp,))
    for kind, first, count, index_first in [
        ('L',0x1100,19,0), ('V',0x1161,21,0), ('T',0x11A8,27,1)
    ]:
        for n in range(count):
            index = index_first+n
            add(f'jamo{kind}{index:02d}', design.draw_jamo, (kind,index),
                codepoints=(first+n,), form='parallel')
    for cp in range(0x3131, 0x3164):
        kind, index = compat_jamo(cp)
        cmap[cp] = f'jamo{kind}{index:02d}'

    for offset in range(SCOUNT):
        l, rest = divmod(offset, 21*28)
        v, t = divmod(rest, 28)
        cp = SBASE+offset
        add(f'uni{cp:04X}', design.draw_syllable, (l,v,t),
            codepoints=(cp,), form='parallel')
        if (offset+1) % 2000 == 0:
            print(f'Drawn {offset+1}/{SCOUNT} modern Hangul defaults', flush=True)
    pairs = []
    for name, method, args in affected_glyphs(design):
        alternate = name+'.ss01'
        add(alternate, getattr(design, method), args,
            advance=advances[name], form='upright')
        pairs.append((name, alternate))
    assert len(pairs) == 2610

    fb = FontBuilder(UPM, isTTF=True)
    fb.font.cfg[USE_HARFBUZZ_REPACKER] = True
    fb.setupGlyphOrder(list(glyphs))
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({
        name: (advances[name], getattr(glyph,'xMin',0))
        for name, glyph in glyphs.items()
    })
    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    fb.setupNameTable({
        'familyName': FAMILY, 'styleName': STYLE,
        'uniqueFontIdentifier': f'{VERSION};SLSG;{POSTSCRIPT}',
        'fullName': f'{FAMILY} {STYLE}', 'psName': POSTSCRIPT,
        'version': f'Version {VERSION}',
        'copyright': COPYRIGHT,
        'description': 'Original Hangul display typeface using general Jamo composition rules, inspired by Osaka and Tsushima signs. Release 1.001 shortens the English family name and preserves the approved prototype v2 letterforms.',
        'manufacturer': 'dolsup',
        'licenseDescription': LICENSE_DESCRIPTION,
        'licenseInfoURL': 'https://openfontlicense.org',
    })
    names = fb.font['name']
    for platform, encoding, language in [(3, 1, 0x409), (1, 0, 0)]:
        names.setName(FAMILY, 16, platform, encoding, language)
        names.setName(STYLE, 17, platform, encoding, language)
    for name_id, text in [(1, KOREAN_FAMILY), (2, STYLE),
                          (4, KOREAN_FAMILY+' '+STYLE),
                          (16, KOREAN_FAMILY), (17, STYLE)]:
        names.setName(text, name_id, 3, 1, 0x412)
    fb.setupOS2(version=4, sTypoAscender=ASCENT, sTypoDescender=DESCENT,
        sTypoLineGap=0, usWinAscent=950, usWinDescent=250,
        usWeightClass=400, usWidthClass=5, fsSelection=0xC0, fsType=0,
        achVendID='SLSG', sxHeight=520, sCapHeight=700)
    fb.setupPost(keepGlyphNames=True)
    fb.setupMaxp()
    fb.font['head'].fontRevision = float(VERSION)
    fb.font['head'].created = RELEASE_TIMESTAMP
    fb.font['head'].modified = RELEASE_TIMESTAMP
    fb.font.recalcTimestamp = False
    features = feature_source(pairs)
    # Deliberately no ccmp L+V ligatures: compatibility Jamo must stay separate.
    addOpenTypeFeaturesFromString(fb.font, features)

    ttf_path = output_dir/f'{POSTSCRIPT}.ttf'
    woff_path = output_dir/f'{POSTSCRIPT}.woff2'
    fb.save(ttf_path)
    print(f'TTF saved: {ttf_path}', flush=True)
    web = TTFont(ttf_path, recalcTimestamp=False)
    web.cfg[USE_HARFBUZZ_REPACKER] = True
    web.flavor = 'woff2'
    web.save(woff_path)
    web.close()
    print(f'WOFF2 saved: {woff_path}', flush=True)
    return ttf_path, woff_path
