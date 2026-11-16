#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Build the release font from the shared drawing functions."""
from __future__ import annotations
import math
from pathlib import Path
import unicodedata
from datetime import datetime, timezone

from . import design
from .layout_features import (PROPORTIONAL_WIDTHS, draw_slashed_zero,
                              feature_source, proportional_glyph, rotated_glyph)
from .outline_storage import factor_contours
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.woff2 import WOFF2FlavorData
from fontTools.ttLib.tables.otBase import USE_HARFBUZZ_REPACKER
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.otlLib.maxContextCalc import maxCtxFont

UPM = 1000
FAMILY, STYLE = 'Seolnong', 'Regular'
KOREAN_FAMILY = '설농체'
VERSION = '1.003'
POSTSCRIPT = 'Seolnong-Regular'
VENDOR_ID = 'dols'  # Unregistered vendor identifier for dolsup.
COPYRIGHT = 'Copyright (c) 2026 dolsup (https://github.com/dolsup/seolnong)'
LICENSE_DESCRIPTION = (Path(__file__).resolve().parents[1] / 'OFL.txt').read_text(encoding='utf-8').strip()
RELEASE_TIMESTAMP = int(datetime(2026, 11, 16, tzinfo=timezone.utc).timestamp()) + 2082844800
SBASE, SCOUNT = 0xAC00, 11172
ASCENT, DESCENT = 900, -250
VERTICAL_ORIGIN, VERTICAL_ADVANCE = 925, 1000
CAP_CONSONANTS = frozenset({'h', 'ch'})
SAMPLE_TEXT = ('야간의 체크인은 프런트 옆의 벨을 눌러 주십시오. '
               '휴게실의 물과 커피는 무료로 준비하고 있습니다.')


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


def remove_constant_segments(glyph):
    """Remove only segments whose every point equals their current point.

    Integer rounding can leave a redundant line or constant quadratic segment.
    Rebuild only a glyph that actually contains one, so ordinary outlines keep
    the exact original point order and byte representation. In particular, this
    does not simplify overlaps or discard meaningful off-curve control points.
    """
    if not glyph.numberOfContours or glyph.isComposite():
        return glyph, 0
    recording = RecordingPen()
    glyph.draw(recording, None)
    filtered, current, start, removed = [], None, None, 0
    for operation, points in recording.value:
        if (operation in {'lineTo', 'qCurveTo', 'curveTo'} and current is not None
                and points and all(point == current for point in points)):
            removed += 1
            continue
        filtered.append((operation, points))
        if operation == 'moveTo':
            current = start = points[0]
        elif operation in {'lineTo', 'qCurveTo', 'curveTo'}:
            current = points[-1] if points[-1] is not None else start
        elif operation in {'closePath', 'endPath'}:
            current = start = None
    if not removed:
        return glyph, 0
    recording.value = filtered
    pen = TTGlyphPen(None)
    recording.replay(pen)
    cleaned = pen.glyph()
    cleaned.recalcBounds(None)
    return cleaned, removed


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
    add('emspace', draw_empty, advance=1000, codepoints=(0x2003, 0x3000))
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

    # These optional figures preserve the existing default outlines and
    # advances. Proportional glyphs are translations, never scaled drawings.
    proportional_pairs, zero_pairs = [], []
    zero_name = cmap[ord('0')]
    add(zero_name + '.zero', draw_slashed_zero, (600,), advance=600)
    zero_pairs.append((zero_name, zero_name + '.zero'))
    for digit, width in PROPORTIONAL_WIDTHS.items():
        base = cmap[ord(digit)]
        alternate = base + '.pnum'
        glyphs[alternate] = proportional_glyph(glyphs[base], width)
        advances[alternate] = width
        proportional_pairs.append((base, alternate))
    proportional_zero = zero_name + '.pnum.zero'
    glyphs[proportional_zero] = proportional_glyph(glyphs[zero_name + '.zero'],
                                                 PROPORTIONAL_WIDTHS['0'])
    advances[proportional_zero] = PROPORTIONAL_WIDTHS['0']
    proportional_pairs.append((zero_name + '.zero', proportional_zero))
    zero_pairs.append((zero_name + '.pnum', proportional_zero))
    if 0xFF10 in cmap:
        fullwidth_zero = cmap[0xFF10]
        add(fullwidth_zero + '.zero', draw_slashed_zero, (1000,), advance=1000)
        zero_pairs.append((fullwidth_zero, fullwidth_zero + '.zero'))

    # Upright East Asian vertical forms use a consistent one-em cell.
    vertical_pairs = []
    for ch in design.VERTICAL_ALTERNATES:
        base = cmap[ord(ch)]
        alternate = base + '.vert'
        add(alternate, design.draw_vertical, (ch,), advance=1000)
        vertical_pairs.append((base, alternate))

    # Legacy vertical engines request vrt2 instead of rotating Latin runs.
    # Rotated forms preserve horizontal spacing, including proportional figures.
    rotation_pairs, rotation_advances = {}, {}
    rotate_names = [cmap[cp] for cp in range(0x21, 0x7F)]
    rotate_names += [alternate for _, alternate in proportional_pairs]
    rotate_names += [zero_name + '.zero']
    rotate_names += [cmap[cp] for cp in (0x00A5, 0x00B0, 0x2113)
                     if cp in cmap]
    for base in dict.fromkeys(rotate_names):
        alternate = base + '.vrt2'
        glyphs[alternate] = rotated_glyph(glyphs[base], VERTICAL_ORIGIN)
        advances[alternate] = UPM
        rotation_pairs[base] = alternate
        rotation_advances[alternate] = advances[base]

    hangul_names = [cmap[cp] for cp in range(SBASE, SBASE + SCOUNT)]
    hangul_names += [alternate for base, alternate in pairs
                    if base.startswith('uni')]
    preserved_hangul = set(hangul_names) | {
        name for name in glyphs if name.startswith('jamo')}
    cleaned_glyphs = []
    for name, glyph in glyphs.items():
        # The established Hangul masters retain their exact byte-level outline
        # representation; this release only cleans non-Hangul drawing artifacts.
        if name in preserved_hangul:
            continue
        glyphs[name], removed = remove_constant_segments(glyph)
        if removed:
            cleaned_glyphs.append((name, removed))
    if cleaned_glyphs:
        print('Removed constant outline segments: ' + ', '.join(
            f'{name} ({count})' for name, count in cleaned_glyphs), flush=True)

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
    upright_latin = {cmap[cp] for cp in [*range(0x30, 0x3A),
                                       *range(0x41, 0x5B), *range(0x61, 0x7B)]}
    upright_latin |= {cmap[cp + 0xFEE0] for cp in [*range(0x30, 0x3A),
                                                *range(0x41, 0x5B), *range(0x61, 0x7B)]
                      if cp + 0xFEE0 in cmap}
    upright_latin |= {alternate for _, alternate in proportional_pairs + zero_pairs}
    vertical_metrics = {}
    for name, glyph in glyphs.items():
        # Spaces retain their useful relative lengths; invisible controls must
        # not unexpectedly occupy a cell when the writing direction changes.
        height = (advances[name] if name in {'space', 'emspace', 'thinspace',
                                           'zerowidth'} else VERTICAL_ADVANCE)
        height = rotation_advances.get(name, height)
        origin = VERTICAL_ORIGIN
        if name in upright_latin:
            # Upright Latin occupies an em cell centered on its visible ink.
            # This also keeps g/p/q descenders out of the following cell. The
            # pre-rotated vrt2 forms retain their original spacing and origin.
            origin = round((height + glyph.yMin + glyph.yMax) / 2)
        vertical_metrics[name] = (height, origin - getattr(glyph, 'yMax', 0))
    fb.setupVerticalMetrics(vertical_metrics)
    fb.setupVerticalHeader(ascent=500, descent=-500, lineGap=0,
                           caretSlopeRise=0, caretSlopeRun=1)
    fb.setupNameTable({
        'familyName': FAMILY, 'styleName': STYLE,
        'uniqueFontIdentifier': f'{VERSION};{VENDOR_ID};{POSTSCRIPT}',
        'fullName': f'{FAMILY} {STYLE}', 'psName': POSTSCRIPT,
        'version': f'Version {VERSION}',
        'copyright': COPYRIGHT,
        'description': 'Hangul display typeface inspired by Korean lettering on signs in Osaka and Tsushima, Japan.',
        'manufacturer': 'dolsup',
        'designer': 'dolsup',
        'vendorURL': 'https://dolsup.github.io/seolnong/',
        'designerURL': 'https://github.com/dolsup',
        'licenseDescription': LICENSE_DESCRIPTION,
        'licenseInfoURL': 'https://openfontlicense.org',
    }, mac=False)
    names = fb.font['name']
    names.setName(FAMILY, 16, 3, 1, 0x409)
    names.setName(STYLE, 17, 3, 1, 0x409)
    names.setName('일본 오오사까와 쓰시마의 안내판에서 본 한글 모양을 바탕으로 만든 표시용 서체입니다.',
                  10, 3, 1, 0x412)
    for name_id, text in [(1, KOREAN_FAMILY), (2, STYLE),
                          (4, KOREAN_FAMILY+' '+STYLE),
                          (16, KOREAN_FAMILY), (17, STYLE)]:
        names.setName(text, name_id, 3, 1, 0x412)
    # Name ID 19 is an optional specimen for font viewers. Keep the Korean
    # text in a language-neutral Unicode record and a Korean Windows record.
    names.setName(SAMPLE_TEXT, 19, 0, 4, 0)
    names.setName(SAMPLE_TEXT, 19, 3, 1, 0x412)
    fb.setupOS2(version=4, sTypoAscender=ASCENT, sTypoDescender=DESCENT,
        sTypoLineGap=0, usWinAscent=950, usWinDescent=300,
        usWeightClass=400, usWidthClass=5, fsSelection=0xC0, fsType=0,
        achVendID=VENDOR_ID, sxHeight=glyphs[cmap[ord('x')]].yMax,
        sCapHeight=glyphs[cmap[ord('H')]].yMax,
        yStrikeoutSize=60, yStrikeoutPosition=440)
    # Legacy Windows language selection metadata follows actual Unicode
    # coverage. This does not claim support for Japanese or all Latin-1.
    fb.font['OS/2'].recalcCodePageRanges(fb.font)
    # The lower underline edge is -280, within the Win clipping margin of 300.
    # Normal line spacing remains the established Typo/hhea 900 / -250.
    fb.setupPost(keepGlyphNames=True, underlinePosition=-220,
                 underlineThickness=60)
    fb.setupMaxp()
    # Smart dropout control helps legacy monochrome rasterizers preserve very
    # small strokes without introducing point-moving TrueType hint programs.
    prep = newTable('prep')
    prep.program = Program()
    prep.program.fromAssembly(['PUSHW[]', '511', 'SCANCTRL[]',
                               'PUSHB[]', '4', 'SCANTYPE[]'])
    fb.font['prep'] = prep
    fb.font['maxp'].maxStackElements = 1
    gasp = newTable('gasp')
    gasp.version = 1
    gasp.gaspRange = {65535: 0x0A}  # grayscale + symmetric smoothing; no grid fit
    fb.font['gasp'] = gasp
    fb.font['head'].fontRevision = float(VERSION)
    fb.font['head'].created = RELEASE_TIMESTAMP
    fb.font['head'].modified = RELEASE_TIMESTAMP
    fb.font.recalcTimestamp = False
    features = feature_source(pairs, proportional_pairs, zero_pairs,
                              vertical_pairs, rotation_pairs, cmap, hangul_names)
    # Deliberately no ccmp L+V ligatures: compatibility Jamo must stay separate.
    addOpenTypeFeaturesFromString(fb.font, features)
    # Current Windows and macOS use Unicode names. Do not retain legacy
    # MacRoman records, including any introduced by feature-label helpers.
    names.names = [record for record in names.names if record.platformID != 1]
    fb.font['OS/2'].usMaxContext = maxCtxFont(fb.font)

    # Store identical contour shapes once. Original glyph IDs, drawn geometry,
    # advances and feature substitutions remain unchanged.
    storage = factor_contours(fb.font, vertical_origin=VERTICAL_ORIGIN)
    print(f"Shared outlines: {storage['components']} components for "
          f"{storage['glyphs']} glyphs", flush=True)

    ttf_path = output_dir/f'{POSTSCRIPT}.ttf'
    woff_path = output_dir/f'{POSTSCRIPT}.woff2'
    fb.save(ttf_path)
    print(f'TTF saved: {ttf_path}', flush=True)
    web = TTFont(ttf_path, recalcTimestamp=False)
    web.cfg[USE_HARFBUZZ_REPACKER] = True
    web.flavor = 'woff2'
    web.flavorData = WOFF2FlavorData(transformedTables={'glyf', 'loca', 'hmtx'})
    web.save(woff_path)
    web.close()
    print(f'WOFF2 saved: {woff_path}', flush=True)
    return ttf_path, woff_path
