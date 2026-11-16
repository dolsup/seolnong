# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Small, explicit layout rules for Seolnong's finished glyphs.

These rules never alter the Hangul composition drawings. Proportional figures,
the slashed zero and rotated Latin forms are unencoded alternatives; the
existing Unicode glyphs and their horizontal advances remain the defaults.
"""
from copy import deepcopy

from . import design


# Optical widths for the existing numeral outlines, not a horizontal scaling.
# In particular, the narrow 1 no longer has the same empty sides as the 8.
PROPORTIONAL_WIDTHS = dict(zip('0123456789', (560, 440, 560, 540, 560,
                                           560, 580, 560, 560, 580)))

# Conservative Latin pairs. Numeric punctuation is deliberately excluded so
# default prices and times retain the predictable tabular numeral spacing.
LATIN_KERN = {
    'AV': -70, 'AW': -45, 'AY': -65, 'AT': -35,
    'VA': -70, 'WA': -45, 'YA': -65, 'TA': -40,
    'LT': -40, 'LV': -40, 'LW': -30, 'LY': -45,
    **{f'T{ch}': -60 for ch in 'aoecs'},
    **{f'V{ch}': -45 for ch in 'aoe'},
    **{f'W{ch}': -30 for ch in 'aoe'},
    **{f'Y{ch}': -60 for ch in 'aoe'},
    **{f'{ch}{stop}': value for ch, value in
       [('F', -55), ('P', -55), ('T', -55), ('V', -55),
        ('W', -40), ('Y', -60)] for stop in '.,'},
}


def shifted_glyph(glyph, dx=0, dy=0):
    """Translate a simple TrueType outline without re-approximating curves."""
    shifted = deepcopy(glyph)
    if shifted.numberOfContours:
        shifted.coordinates.translate((dx, dy))
        shifted.recalcBounds(None)
    return shifted


def proportional_glyph(glyph, width):
    """Keep the exact numeral outline and center it in its optical advance."""
    glyph.recalcBounds(None)
    dx = round((width - glyph.xMin - glyph.xMax) / 2)
    return shifted_glyph(glyph, dx)


def rotated_glyph(glyph, origin=925):
    """Clockwise quarter-turn for engines using vrt2's pre-rotated forms.

    y'=origin-x means that topSideBearing equals the original left sidebearing.
    The builder also preserves the original horizontal advance as the rotated
    glyph's vertical advance, as required by the vrt2 specification.
    """
    rotated = deepcopy(glyph)
    if rotated.numberOfContours:
        for index, (x, y) in enumerate(rotated.coordinates):
            rotated.coordinates[index] = (y + 75, origin - x)
        rotated.recalcBounds(None)
    return rotated


def draw_slashed_zero(advance, pen):
    """The original 0 with a round 60-unit diagonal through its counter."""
    offset = (advance - 600) / 2
    drawing = design.Drawing()
    for path in design.LATIN['0']:
        drawing.stroke(design.transform(path, (100 + offset, 45,
                                              500 + offset, 765)))
    drawing.line(170 + offset, 165, 430 + offset, 645)
    drawing.finish(pen)
    return advance


def feature_source(ss01_pairs, proportional_pairs, zero_pairs,
                   vertical_pairs, rotation_pairs, cmap, hangul_names):
    """Build the standard OpenType features in deliberate lookup order."""
    lines = [
        'languagesystem DFLT dflt;',
        'languagesystem hang dflt;',
        'languagesystem latn dflt;',
        # Expose the already drawn alternatives to a glyph-selection UI.
        'feature aalt {',
        '  feature ss01;',
        '  feature pnum;',
        '  feature zero;',
        '} aalt;',
        'feature ss01 {',
        '  featureNames {',
        '    name "Upright tops";',
        '    name 3 1 1042 "세로 꼭지 ㅎ·ㅊ";',
        '    name 3 1 1041 "縦の頭画 ㅎ・ㅊ";',
        '  };',
        *[f'  sub {base} by {alternate};' for base, alternate in ss01_pairs],
        '} ss01;',
        'feature pnum {',
        *[f'  sub {base} by {alternate};'
          for base, alternate in proportional_pairs],
        '} pnum;',
        # tnum explicitly restores the defaults, including a slashed zero.
        # In the invalid case where both width modes are requested, tnum wins.
        'feature tnum {',
        *[f'  sub {alternate} by {base};'
          for base, alternate in proportional_pairs],
        '} tnum;',
        'feature zero {',
        *[f'  sub {base} by {alternate};' for base, alternate in zero_pairs],
        '} zero;',
        'feature vert {',
        *[f'  sub {base} by {alternate};' for base, alternate in vertical_pairs],
        '} vert;',
    ]
    # vrt2 is a complete superset: East Asian punctuation plus pre-rotated
    # proportional Latin. Its substitution lookup is last in GSUB.
    vrt2 = dict(vertical_pairs)
    vrt2.update(rotation_pairs)
    for base, vertical in vertical_pairs:
        if base in rotation_pairs:
            vrt2[vertical] = rotation_pairs[base]
    lines.extend([
        'feature vrt2 {',
        *[f'  sub {base} by {alternate};' for base, alternate in vrt2.items()],
        '} vrt2;',
    ])
    kern_pairs = [(cmap[ord(pair[0])], cmap[ord(pair[1])], value)
                  for pair, value in LATIN_KERN.items()]
    lines.extend([
        '@Hangul = [' + ' '.join(hangul_names) + '];',
        'feature kern {',
        *[f'  pos {left} {right} {value};'
          for left, right, value in kern_pairs],
        # Keep Hangul's em-cell rhythm. Only neighboring ASCII punctuation
        # receives a restrained fit; never kern Hangul against Hangul.
        *[f'  pos {cmap[ord(ch)]} @Hangul -65;' for ch in '([{'],
        *[f'  pos @Hangul {cmap[ord(ch)]} -65;' for ch in ')]}'],
        *[f'  pos {cmap[ord(ch)]} @Hangul -30;' for ch in '\"\'‘“'],
        *[f'  pos @Hangul {cmap[ord(ch)]} -30;' for ch in '\"\'’”'],
        '} kern;',
        'feature vkrn {',
        # OpenType vertical advance adjustments use the same sign as horizontal
        # kern. The shaping engine converts the result to a negative TTB vector.
        *[f'  pos {rotation_pairs[left]} {rotation_pairs[right]} <0 0 0 {value}>;'
          for left, right, value in kern_pairs
          if left in rotation_pairs and right in rotation_pairs],
        '} vkrn;',
    ])
    return '\n'.join(lines) + '\n'
