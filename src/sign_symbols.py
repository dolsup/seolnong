# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Signage punctuation and symbols sharing Seolnong's round, 60-unit pen.

Existing ASCII drawings are reused without scaling their stroke. The additions
live here so extending the character set cannot change the Hangul composition
rules or the original Latin outlines.
"""
from math import hypot

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen


SYMBOL_CHARACTERS = (
    '※÷−±¥￥°℃ℓ'
    '「」『』【】〈〉《》。、・〜'
    '○●□■△▲▽▼◆◇'
    '↖↗↙↘↔↕'
    '㎡㎞㎝㎜㎏'
)
FULLWIDTH_FIRST, FULLWIDTH_LAST = 0xFF01, 0xFF5E
EXTRA_CODEPOINTS = tuple(sorted({ord(ch) for ch in SYMBOL_CHARACTERS}
                              | set(range(FULLWIDTH_FIRST, FULLWIDTH_LAST + 1))
                              | {0x00D7}))

# Keys are horizontal Unicode characters. Values describe the alternate, not
# private-use codepoints; the builder emits unencoded .vert glyphs.
VERTICAL_ALTERNATES = {
    **{ch: 'bracket' for ch in '()[]{}（）［］｛｝「」『』【】〈〉《》'},
    **{ch: 'punctuation' for ch in '。、，．'},
    **{ch: 'centered_line' for ch in '…–—〜～'},
}


def supports(ch):
    return ch in SYMBOL_CHARACTERS or FULLWIDTH_FIRST <= ord(ch) <= FULLWIDTH_LAST


def _closed(d, points, solid=False):
    """Outline and filled shapes have exactly the same rounded silhouette."""
    commands = [('M', *points[0]), *[('L', *point) for point in points[1:]], ('Z',)]
    if not solid:
        d.stroke(commands)
        return
    import pathops
    outline = type(d)()
    outline.stroke(commands)
    p = pathops.Path()
    p.moveTo(*points[0])
    for point in points[1:]:
        p.lineTo(*point)
    p.close()
    # Union separate fill operands, so reversing a triangle cannot turn the
    # shared interior into a winding-rule hole.
    d.add(pathops.op(outline.path, p, pathops.PathOp.UNION))


def _disc(d, x, y, radius):
    # A diameter-long zero-length stroke is a true disk with the same pen
    # construction as the punctuation dots. A minute segment avoids empty
    # contours in stroke expanders.
    d.line(x, y, x, y + .01, 2 * radius)


def _arrow(d, start, end, double=False):
    d.line(*start, *end)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    head, spread = 240, 240
    for point, sign in ((end, -1), (start, 1)) if double else ((end, -1),):
        bx, by = point[0] + sign * head * ux, point[1] + sign * head * uy
        # 45-degree arms, matching the existing cardinal arrows.
        d.stroke([('M', bx - spread * uy, by + spread * ux),
                  ('L', *point),
                  ('L', bx + spread * uy, by - spread * ux)])


def _fullwidth(ch, pen):
    from .design import draw_ascii
    ascii_ch = chr(ord(ch) - 0xFEE0)
    recording = RecordingPen()
    advance = draw_ascii(ascii_ch, recording)
    offset = (1000 - advance) / 2
    vertical_offset = 0
    # Opening and closing fullwidth brackets embrace the neighboring text,
    # retaining the generous outer sidebearing of East Asian punctuation.
    if ascii_ch in '([{':
        offset = 430
        vertical_offset = 35
    elif ascii_ch in ')]}':
        offset = -30
        vertical_offset = 35
    elif ascii_ch in ',.':
        offset = 60
    recording.replay(TransformPen(pen, (1, 0, 0, 1, offset, vertical_offset)))
    return 1000


def draw_symbol(ch, pen):
    from .design import Drawing, transform
    from .ascii_shapes import LATIN, LOWER

    if FULLWIDTH_FIRST <= ord(ch) <= FULLWIDTH_LAST:
        return _fullwidth(ch, pen)

    d = Drawing()
    advance = 1000
    if ch == '※':
        d.line(205, 720, 795, 130)
        d.line(205, 130, 795, 720)
        for x, y in ((500, 790), (135, 425), (865, 425), (500, 60)):
            _disc(d, x, y, 38)
    elif ch in '÷−±':
        advance = 600
        if ch == '÷':
            d.line(80, 390, 520, 390)
            _disc(d, 300, 640, 34)
            _disc(d, 300, 140, 34)
        elif ch == '−':
            d.line(80, 380, 520, 380)
        else:
            d.line(100, 520, 500, 520)
            d.line(300, 320, 300, 720)
            d.line(100, 100, 500, 100)
    elif ch in '¥￥':
        if ch == '￥':
            recording = RecordingPen()
            draw_symbol('¥', recording)
            recording.replay(TransformPen(pen, (1, 0, 0, 1, 200, 0)))
            return 1000
        advance = 600
        for path in LATIN['Y']:
            d.stroke(transform(path, (100, 45, 500, 765)))
        d.line(75, 400, 525, 400)
        d.line(75, 260, 525, 260)
    elif ch == '°':
        advance = 360
        d.ellipse(160, 700, 75, 75)
    elif ch == '℃':
        d.ellipse(155, 700, 70, 70)
        for path in LATIN['C']:
            d.stroke(transform(path, (350, 45, 870, 765)))
    elif ch == 'ℓ':
        advance = 560
        d.stroke([('M', 95, 145), ('C', 210, 285, 435, 605, 385, 735),
                  ('C', 342, 845, 205, 740, 225, 525),
                  ('C', 241, 348, 275, 185, 440, 90)])
    elif ch in '「」『』':
        closing = ch in '」』'
        paths = [[('M', 875, 790), ('L', 625, 790), ('L', 625, 60)]]
        if ch in '『』':
            paths = [[('M', 905, 790), ('L', 590, 790), ('L', 590, 60)],
                     [('M', 905, 655), ('L', 725, 655), ('L', 725, 60)]]
        for path in paths:
            if closing:
                path = [(c[0], *[1000 - v if i % 2 == 0 else 850 - v
                                for i, v in enumerate(c[1:])]) for c in path]
            d.stroke(path)
    elif ch in '【】':
        # Lenticular brackets use a broad exterior with a curved inner edge;
        # they remain visibly different from fullwidth square brackets.
        import pathops
        p = pathops.Path()
        p.moveTo(900, 820)
        p.lineTo(615, 820)
        p.lineTo(615, 30)
        p.lineTo(900, 30)
        p.cubicTo(705, 225, 705, 625, 900, 820)
        p.close()
        if ch == '】':
            rec = RecordingPen()
            p.draw(rec)
            q = pathops.Path()
            rec.replay(TransformPen(q.getPen(), (-1, 0, 0, -1, 1000, 850)))
            p = q
        d.add(p)
    elif ch in '〈〉《》':
        closing = ch in '〉》'
        for x in ([585, 795] if ch in '《》' else [715]):
            path = [('M', x + 125, 790), ('L', x - 120, 425), ('L', x + 125, 60)]
            if closing:
                path = [(c[0], *[1000 - v if i % 2 == 0 else v
                                for i, v in enumerate(c[1:])]) for c in path]
            d.stroke(path)
    elif ch == '。':
        d.ellipse(220, 100, 90, 90)
    elif ch == '、':
        d.line(145, 145, 285, 15)
    elif ch == '・':
        _disc(d, 500, 425, 45)
    elif ch == '〜':
        d.stroke([('M', 100, 380), ('C', 330, 675, 670, 175, 900, 470)])
    elif ch in '○●':
        if ch == '●':
            _disc(d, 500, 425, 330)
        else:
            d.ellipse(500, 425, 300, 300)
    elif ch in '□■':
        _closed(d, [(185, 110), (185, 740), (815, 740), (815, 110)], ch == '■')
    elif ch in '△▲▽▼':
        points = [(500, 785), (160, 140), (840, 140)]
        if ch in '▽▼':
            points = [(x, 850 - y) for x, y in points]
        _closed(d, points, ch in '▲▼')
    elif ch in '◆◇':
        _closed(d, [(500, 790), (155, 425), (500, 60), (845, 425)], ch == '◆')
    elif ch in '↖↗↙↘':
        sx, sy = (1 if ch in '↗↘' else -1), (1 if ch in '↖↗' else -1)
        _arrow(d, (500 - sx * 300, 390 - sy * 300),
               (500 + sx * 300, 390 + sy * 300))
    elif ch == '↔':
        _arrow(d, (100, 380), (900, 380), double=True)
    elif ch == '↕':
        _arrow(d, (500, 0), (500, 780), double=True)
    elif ch in '㎞㎝㎜㎏':
        letters = {'㎞': 'km', '㎝': 'cm', '㎜': 'mm', '㎏': 'kg'}[ch]
        for letter, box in zip(letters, ((75, 145, 425, 800), (555, 145, 905, 800))):
            for path in LOWER[letter]:
                d.stroke(transform(path, box))
    elif ch == '㎡':
        for path in LOWER['m']:
            d.stroke(transform(path, (80, 80, 615, 810)))
        for path in LATIN['2']:
            d.stroke(transform(path, (720, 465, 930, 805)))
    else:
        raise ValueError(f'Unsupported signage symbol {ch!r}')
    d.finish(pen)
    return advance


def draw_vertical(ch, pen):
    """Draw an upright vertical form in a cell with origin y=925.

    The em cell is centered at (500,425), matching the visual center of the
    original Hangul. All alternates are full-em wide and advance one em down.
    """
    from .design import Drawing, draw_ascii
    if ch not in VERTICAL_ALTERNATES:
        raise ValueError(f'No vertical alternate for {ch!r}')
    d = Drawing()
    if ch == '。':
        d.ellipse(780, 720, 90, 90)
    elif ch == '、':
        d.line(705, 795, 845, 665)
    elif ch == '．':
        _disc(d, 780, 720, 30)
    elif ch == '，':
        _disc(d, 780, 740, 30)
        d.line(780, 740, 720, 625)
    elif ch == '…':
        for y in (85, 425, 765):
            d.line(500, y, 500, y + 2)
    elif ch in '–—':
        half = 300 if ch == '–' else 420
        d.line(500, 425 - half, 500, 425 + half)
    elif ch in '〜～':
        d.stroke([('M', 455, 825), ('C', 750, 595, 250, 255, 545, 25)])
    else:
        recording = RecordingPen()
        # ASCII brackets use the fullwidth source only in vertical layout;
        # this keeps horizontal ASCII unchanged and avoids cramped end caps.
        source = chr(ord(ch) + 0xFEE0) if ch in '()[]{}' else ch
        draw_ascii(source, recording)
        recording.replay(TransformPen(pen, (0, -1, 1, 0, 75, 925)))
        return 1000
    d.finish(pen)
    return 1000
