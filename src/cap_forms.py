# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Shared horizontal and upright cap geometry for Hieuh and Chieuch."""


def cap_profiles(box, width=60.0):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    compact = {
        'bar_y': y1 - 70,
        'cap_width': max(80, min(140, w * .18)),
        'bar_x0': x0 + w * .08, 'bar_x1': x0 + w * .92,
    }
    large = {
        'bar_y': y1 - max(width + 10, h * .21),
        'cap_width': max(width * 1.5, min(170, w * .30)),
        'bar_x0': x0 + w * .03, 'bar_x1': x0 + w * .97,
    }
    mix = max(0.0, min(1.0, (h - 340) / 100))
    return compact, large, mix


def cap_geometry(box, width=60.0, role='initial'):
    compact, large, mix = cap_profiles(box, width)
    g = {key: compact[key] * (1 - mix) + large[key] * mix
         for key in compact}
    g.update({
        'cx': (box[0] + box[2]) / 2,
        'cap_y': box[3], 'width': width,
        'role': role, 'compact_mix': 1 - mix,
    })
    return g


def draw_cap(d, geometry, form='parallel'):
    """Draw only the changing head stroke; its support is a separate primitive."""
    g = geometry
    if form == 'parallel':
        d.line(g['cx'] - g['cap_width'] / 2, g['cap_y'],
               g['cx'] + g['cap_width'] / 2, g['cap_y'], g['width'])
    elif form == 'upright':
        d.line(g['cx'], g['bar_y'], g['cx'], g['cap_y'], g['width'])
    else:
        raise ValueError('Unknown cap form: ' + str(form))


def draw_head(d, geometry, form='parallel'):
    draw_cap(d, geometry, form)
    g = geometry
    d.line(g['bar_x0'], g['bar_y'], g['bar_x1'], g['bar_y'], g['width'])
