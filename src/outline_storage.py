# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Store repeated outlines once without changing Seolnong's drawn geometry.

Run after drawing and feature compilation. Existing glyph IDs and metrics stay
in place; only unencoded, zero-advance contour components are appended. This is
storage optimization, not a change to Hangul composition or shaping behavior.
"""
from __future__ import annotations

from array import array

from fontTools.ttLib.tables._g_l_y_f import (
    Glyph, GlyphComponent, GlyphCoordinates, UNSCALED_COMPONENT_OFFSET,
)
from fontTools.ttLib.tables.ttProgram import Program


def factor_contours(font, *, vertical_origin=925):
    """Share identical, translated contours from unhinted simple glyphs.

    Contour point order, winding, coordinates and on-curve flags are preserved
    exactly. Components have identity transforms and integer design-space
    offsets; neither device-grid rounding nor metric inheritance is enabled.
    Hinted and existing composite glyphs are deliberately left alone.
    """
    if 'fvar' in font or 'gvar' in font:
        raise ValueError('Contour sharing requires a static font; instantiate variations first')
    glyf = font['glyf']
    original_order = list(font.getGlyphOrder())
    shapes, sources, placements = {}, {}, {}
    # Do not indirectly change existing composite depth or hint execution by
    # replacing one of its children. The current release starts with flat glyphs.
    existing_children = {
        component.glyphName for name in original_order
        if glyf[name].isComposite() for component in glyf[name].components
    }

    for name in original_order:
        glyph = glyf[name]
        if (glyph.numberOfContours <= 0 or name.startswith('_part')
                or name in existing_children):
            continue
        program = getattr(glyph, 'program', None)
        if program is not None and program.getBytecode():
            continue
        coords, ends, flags = glyph.getCoordinates(glyf)
        sources[name] = glyph
        placements[name] = []
        start = 0
        for end in ends:
            points = tuple(coords[start:end + 1])
            point_flags = bytes(flags[start:end + 1])
            x = min(point[0] for point in points)
            y = min(point[1] for point in points)
            key = (tuple((px - x, py - y) for px, py in points), point_flags)
            if key not in shapes:
                leaf_name = f'_part{len(shapes):04d}'
                if leaf_name in glyf:
                    raise ValueError(f'Reserved component name already exists: {leaf_name}')
                # Keep the first occurrence's coordinates. Internal glyphs then
                # fit the existing bounds without enlarging the head bounding box.
                shapes[key] = (leaf_name, x, y, points, point_flags)
            leaf_name, anchor_x, anchor_y, _, _ = shapes[key]
            placements[name].append((leaf_name, x - anchor_x, y - anchor_y))
            start = end + 1

    for leaf_name, _, _, points, point_flags in shapes.values():
        leaf = Glyph()
        leaf.numberOfContours = 1
        leaf.coordinates = GlyphCoordinates(points)
        leaf.endPtsOfContours = [len(points) - 1]
        leaf.flags = array('B', point_flags)
        leaf.program = Program()
        leaf.program.fromBytecode([])
        leaf.recalcBounds(glyf)
        glyf[leaf_name] = leaf
        # Components never appear in text and do not inherit into parent metrics.
        # Zero advances also keep OS/2.xAvgCharWidth's nonzero-width mean intact.
        font['hmtx'].metrics[leaf_name] = (0, leaf.xMin)
        if 'vmtx' in font:
            font['vmtx'].metrics[leaf_name] = (0, vertical_origin - leaf.yMax)

    for name, components in placements.items():
        glyph = Glyph()
        glyph.numberOfContours = -1
        glyph.components = []
        for leaf_name, x, y in components:
            component = GlyphComponent()
            component.glyphName = leaf_name
            component.x, component.y = x, y
            component.flags = UNSCALED_COMPONENT_OFFSET
            glyph.components.append(component)
        expected = sources[name].getCoordinates(glyf)
        actual = glyph.getCoordinates(glyf)
        if expected[0] != actual[0] or expected[1] != actual[1] or expected[2] != actual[2]:
            raise ValueError(f'Contour sharing changed geometry: {name}')
        glyf[name] = glyph

    leaf_order = [shape[0] for shape in shapes.values()]
    font.setGlyphOrder(original_order + leaf_order)
    return {'glyphs': len(placements), 'components': len(leaf_order)}
