"""Shared Hieuh bowl geometry with horizontal and upright cap styles."""

from .cap_forms import cap_geometry, cap_profiles, draw_head


def h_geometry(box, width=60.0, role='initial'):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    _, large_head, mix = cap_profiles(box, width)
    # Compact model: 70 units for cap-to-bar, 75 for bar-to-bowl.
    # The bowl uses the remainder instead of a fixed tiny 45/50-unit radius.
    compact = {
        'cy': y0 + (h - 145) / 2,
        'rx': min(w * .42, 210),
        'ry': (h - 145) / 2,
    }
    bowl_gap = max(width + 15, h * .20)
    large_bar = large_head['bar_y']
    large_ry = min(h * .215, w * .46)
    large = {
        'cy': large_bar - bowl_gap - large_ry,
        'rx': w * .48,
        'ry': large_ry,
    }
    # Avoid a sudden change at the former 350-unit threshold.
    g = {key: compact[key] * (1 - mix) + large[key] * mix for key in compact}
    if g['ry'] <= width / 2:
        raise ValueError('Hieuh bowl has no open counter: ' + str(box))
    g.update(cap_geometry(box, width, role))
    return g


def draw_hieuh(d, box, width=60.0, role='initial', form='parallel'):
    g = h_geometry(box, width, role)
    draw_head(d, g, form)
    d.ellipse(g['cx'], g['cy'], g['rx'], g['ry'], width)
