#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 dolsup
# SPDX-License-Identifier: OFL-1.1
"""Verify the distributable fonts, shaping, website links, and optional rebuild.

    python verify.py
    python verify.py --rebuild
    python verify.py --baseline /path/to/previous/Seolnong-Regular.ttf

Reports are printed to the terminal; no generated reports enter the repository.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit
import zipfile

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import uharfbuzz as hb

ROOT = Path(__file__).resolve().parent
FONT = ROOT / 'fonts' / 'Seolnong-Regular.ttf'
WEBFONT = FONT.with_suffix('.woff2')
SIGNAGE = '※×÷−±¥￥°℃「」『』【】（）〈〉《》。、・○●□■△▲▽▼◆◇↖↗↙↘↔↕'
REQUIRED_FEATURES = {'aalt', 'ss01', 'pnum', 'tnum', 'zero', 'vert', 'vrt2', 'kern', 'vkrn'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path, self.ids, self.urls, self.textareas = path, [], [], []
        self.textarea = None
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for attr in ('href', 'src'):
            if attr in attrs:
                self.urls.append(attrs[attr])
        if tag == 'textarea':
            self.textarea = {'id': attrs.get('id'), 'text': ''}

    def handle_data(self, data):
        if self.textarea is not None:
            self.textarea['text'] += data

    def handle_endtag(self, tag):
        if tag == 'textarea' and self.textarea is not None:
            self.textareas.append(self.textarea)
            self.textarea = None


def shaped(font, text, features=None, direction='ltr', script='hang'):
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction, buffer.script, buffer.language = direction, script, 'ko'
    hb.shape(font, buffer, features or {})
    return [(info.codepoint, pos.x_advance, pos.y_advance, pos.x_offset, pos.y_offset)
            for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions)]


def inspect_font():
    font = TTFont(FONT, recalcTimestamp=False, checkChecksums=2)
    web = TTFont(WEBFONT, recalcTimestamp=False, checkChecksums=2)
    cmap = font.getBestCmap()
    names = font['name']
    version = names.getDebugName(5).removeprefix('Version ')
    require(abs(font['head'].fontRevision - float(version)) < 1 / 65536,
            'Version string and head.fontRevision disagree')
    require(font.getBestCmap() == web.getBestCmap(), 'TTF / WOFF2 character maps differ')
    for tag in ('glyf', 'hmtx', 'vmtx', 'GSUB', 'GPOS', 'name', 'OS/2', 'post'):
        require(font.getTableData(tag) == web.getTableData(tag), f'TTF / WOFF2 {tag} differs')
    require(set(range(0xAC00, 0xD7A4)) <= cmap.keys(), 'A modern Hangul syllable is missing')
    require(set(range(0x3131, 0x3164)) <= cmap.keys(), 'A compatibility Jamo is missing')
    require(set(range(0xFF01, 0xFF5F)) <= cmap.keys(), 'A fullwidth ASCII character is missing')
    require({ord(ch) for ch in SIGNAGE} | {0x3000} <= cmap.keys(), 'A signage symbol is missing')
    license_text = (ROOT / 'OFL.txt').read_text(encoding='utf-8').strip()
    require(names.getDebugName(0) == license_text.splitlines()[0],
            'Font copyright differs from OFL.txt')
    require(names.getDebugName(13) == license_text and names.getDebugName(14),
            'Embedded license does not match OFL.txt')
    require(names.getDebugName(3).split(';')[1] == font['OS/2'].achVendID,
            'Unique font identifier and vendor ID disagree')
    require(names.getDebugName(11), 'Project URL is missing')
    require(font['OS/2'].fsType == 0, 'Unexpected document-embedding restriction')
    require(font['OS/2'].fsSelection & 0xC0 == 0xC0, 'Regular / typo metrics flags missing')
    require(font['OS/2'].ulCodePageRange1 or font['OS/2'].ulCodePageRange2,
            'Legacy character-set metadata is empty')
    require(all(record.platformID != 1 for record in names.names), 'Obsolete MacRoman name record')
    require('prep' in font and 'gasp' in font, 'Unhinted rasterization preferences are missing')
    require(font['post'].underlineThickness > 0 and font['post'].underlinePosition < 0,
            'Underline metrics are not set')
    require(font['OS/2'].yStrikeoutSize > 0 and font['OS/2'].yStrikeoutPosition > 0,
            'Strikeout metrics are not set')
    require(font['OS/2'].sxHeight == font['glyf'][cmap[ord('x')]].yMax,
            'x-height does not match x')
    require(font['OS/2'].sCapHeight == font['glyf'][cmap[ord('H')]].yMax,
            'Cap height does not match H')
    feature_tags = {item.FeatureTag for tag in ('GSUB', 'GPOS') if tag in font
                    for item in font[tag].table.FeatureList.FeatureRecord}
    require(REQUIRED_FEATURES <= feature_tags, 'A documented OpenType feature is missing')
    ss = next(item.Feature for item in font['GSUB'].table.FeatureList.FeatureRecord
              if item.FeatureTag == 'ss01')
    label_id = ss.FeatureParams.UINameID
    require(names.getName(label_id, 3, 1, 0x412) is not None, 'Korean ss01 label missing')
    ss_mapping = {}
    for index in ss.LookupListIndex:
        lookup = font['GSUB'].table.LookupList.Lookup[index]
        for subtable in lookup.SubTable:
            ss_mapping.update(getattr(subtable, 'mapping', {}))
    require(len(ss_mapping) == 2610, 'ss01 no longer covers all original top variants')
    samples = [item.toUnicode() for item in names.names if item.nameID == 19]
    require(samples and len(set(samples)) == 1, 'Sample text is missing or inconsistent')
    page = Page(ROOT / 'index.html')
    require(any(' '.join(item['text'].split()) == samples[0] for item in page.textareas),
            'Website default text and font sample text differ')
    for cp in range(0xAC00, 0xD7A4):
        glyph = cmap[cp]
        require(font['hmtx'][glyph][0] == 1000, f'Hangul width changed: U+{cp:04X}')
        require(font['vmtx'][glyph][0] == 1000, f'Hangul vertical advance: U+{cp:04X}')
        require(font['vmtx'][glyph][1] + font['glyf'][glyph].yMax == 925,
                f'Inconsistent Hangul vertical origin: U+{cp:04X}')
    for glyph in font.getGlyphOrder():
        outline = font['glyf'][glyph]
        if outline.numberOfContours:
            require(outline.yMax <= font['OS/2'].usWinAscent,
                    f'Upper clipping boundary exceeded by {glyph}')
            require(outline.yMin >= -font['OS/2'].usWinDescent,
                    f'Lower clipping boundary exceeded by {glyph}')
    return font, version, feature_tags


def inspect_shaping(font):
    face = hb.Face(FONT.read_bytes())
    engine = hb.Font(face)
    engine.scale = (font['head'].unitsPerEm,) * 2
    hb.ot_font_set_funcs(engine)
    syllables = ''.join(map(chr, range(0xAC00, 0xD7A4)))
    for alternate in (False, True):
        features = {'ss01': alternate}
        nfc = shaped(engine, syllables, features)
        nfd = shaped(engine, unicodedata.normalize('NFD', syllables), features)
        require(nfc == nfd, f'NFC / NFD mismatch with ss01={alternate}')
        require(len(nfc) == 11172 and all(item[0] != 0 for item in nfc),
                'Missing glyph in modern Hangul shaping')
    require(len(shaped(engine, 'ㄱㅏ')) == 2, 'Compatibility Jamo incorrectly joined')
    require(len(shaped(engine, '\u1100\u1161')) == 1, 'Conjoining Jamo did not compose')
    require(shaped(engine, '휴체않싫', {'ss01': 0}) != shaped(engine, '휴체않싫', {'ss01': 1}),
            'ss01 does not affect the test text')
    for direction in ('ltr', 'ttb'):
        feature = {'ss01': 1}
        require(shaped(engine, '휴체않싫', feature, direction)
                == shaped(engine, unicodedata.normalize('NFD', '휴체않싫'), feature, direction),
                f'NFC / NFD mismatch in {direction}')
    digits = shaped(engine, '0123456789', script='latn')
    require({item[1] for item in digits} == {600}, 'Default digits are no longer tabular')
    proportional = shaped(engine, '0123456789', {'pnum': 1}, script='latn')
    require(len({item[1] for item in proportional}) > 1, 'pnum does not provide proportional widths')
    require(shaped(engine, '0123456789', {'tnum': 1}, script='latn') == digits,
            'tnum does not preserve default tabular digits')
    for proportional_flag in (False, True):
        base = shaped(engine, '0', {'pnum': proportional_flag}, script='latn')
        alternate = shaped(engine, '0', {'pnum': proportional_flag, 'zero': 1}, script='latn')
        require(base[0][0] != alternate[0][0], 'Slashed zero substitution missing')
        require(base[0][1:] == alternate[0][1:], 'Slashed zero changes digit metrics')
    require(shaped(engine, 'AVTo', {'kern': 1}, script='latn')
            != shaped(engine, 'AVTo', {'kern': 0}, script='latn'), 'Latin kerning is ineffective')
    for tag in ('vert', 'vrt2'):
        before = shaped(engine, '「안내」', {'vert': 0, 'vrt2': 0}, 'ttb')
        after = shaped(engine, '「안내」', {tag: 1, 'vrt2' if tag == 'vert' else 'vert': 0}, 'ttb')
        require(before[0][0] != after[0][0] and before[-1][0] != after[-1][0],
                f'{tag} does not substitute corner brackets')
    required = shaped(engine, SIGNAGE)
    require(all(item[0] != 0 for item in required), 'A signage symbol shapes to .notdef')
    return {'engine': f'HarfBuzz {hb.version_string()}', 'hangul_nfc_nfd': 11172,
            'ss01': 'pass', 'numeric_features': 'pass', 'vertical_features': 'pass'}


def inspect_site():
    pages = {path.resolve(): Page(path) for path in ROOT.glob('*.html')}
    count = 0
    for path, page in pages.items():
        require(len(page.ids) == len(set(page.ids)), f'Duplicate HTML id in {path.name}')
        for url in page.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            require(dest.exists(), f'Broken local reference: {path.name}: {url}')
            if parsed.fragment and dest in pages:
                require(parsed.fragment in pages[dest].ids, f'Broken fragment: {path.name}: {url}')
            count += 1
    for path in (ROOT / 'assets').glob('*.css'):
        for raw in re.findall(r'url\(\s*[\"\']?([^\"\')]+)', path.read_text()):
            parsed = urlsplit(raw.strip())
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            require((path.parent / unquote(parsed.path)).is_file(), f'Broken CSS asset: {raw}')
            count += 1
    return count


def inspect_archive(version):
    path = ROOT / 'downloads' / f'Seolnong-{version}.zip'
    expected = {'Seolnong-Regular.ttf': FONT, 'Seolnong-Regular.woff2': WEBFONT,
                'README.txt': ROOT / 'fonts' / 'README.txt', 'OFL.txt': ROOT / 'OFL.txt'}
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, 'ZIP CRC error')
        require(set(archive.namelist()) == {f'Seolnong-{version}/{name}' for name in expected},
                'Download ZIP must contain exactly the four public font files')
        for name, file in expected.items():
            require(archive.read(f'Seolnong-{version}/{name}') == file.read_bytes(),
                    f'Download ZIP has a stale {name}')
    return path


def inspect_baseline(font, baseline):
    old = TTFont(baseline, recalcTimestamp=False)
    current_names = set(font.getGlyphOrder())
    cleaned, repacked = [], []
    for name in old.getGlyphOrder():
        require(name in current_names, f'Previous glyph removed: {name}')
        if old['glyf'][name].compile(old['glyf']) != font['glyf'][name].compile(font['glyf']):
            before = old['glyf'][name].getCoordinates(old['glyf'])
            after = font['glyf'][name].getCoordinates(font['glyf'])
            if all(a == b for a, b in zip(before, after)):
                # Composite storage must expand to the same ordered points,
                # contour boundaries, and on/off-curve flags.
                repacked.append(name)
            else:
                # A zero-length line/quadratic has no visible ink. Its removal
                # is allowed; any change to a real segment still fails.
                require(canonical_outline(old, name) == canonical_outline(font, name),
                        f'Previous outline changed: {name}')
                cleaned.append(name)
        require(old['hmtx'][name] == font['hmtx'][name], f'Previous glyph metrics changed: {name}')
    for cp, name in old.getBestCmap().items():
        require(font.getBestCmap().get(cp) == name, f'Previous encoding changed: U+{cp:04X}')
    return {'count': len(old.getGlyphOrder()), 'storage_repacked': len(repacked),
            'zero_length_cleanup': cleaned}


def canonical_outline(font, name):
    glyphs = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyphs)
    glyphs[name].draw(pen)
    current = None
    output = []
    for command, points in pen.value:
        if (command in {'lineTo', 'qCurveTo', 'curveTo'} and points
                and current is not None and all(point == current for point in points)):
            continue
        output.append((command, points))
        if command in {'moveTo', 'lineTo', 'qCurveTo', 'curveTo'}:
            current = points[-1]
        elif command in {'closePath', 'endPath'}:
            current = None
    return output


def inspect_rebuild(archive):
    with tempfile.TemporaryDirectory(prefix='seolnong-rebuild-') as directory:
        destination = Path(directory)
        shutil.copytree(ROOT / 'src', destination / 'src',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (destination / 'fonts').mkdir()
        for relative in ('build.py', 'requirements.txt', 'OFL.txt', 'fonts/README.txt'):
            shutil.copy2(ROOT / relative, destination / relative)
        subprocess.run([sys.executable, 'build.py'], cwd=destination, check=True, stdout=sys.stderr)
        for path in (FONT, WEBFONT, archive):
            relative = path.relative_to(ROOT)
            require(sha(path) == sha(destination / relative), f'Rebuild differs: {relative}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--rebuild', action='store_true', help='Rebuild in a temporary directory and compare bytes')
    parser.add_argument('--baseline', type=Path, help='Verify that all earlier outlines and default widths are preserved')
    args = parser.parse_args()
    font, version, tags = inspect_font()
    result = {'version': version, 'glyphs': len(font.getGlyphOrder()),
              'features': sorted(tags), 'shaping': inspect_shaping(font),
              'local_references': inspect_site()}
    archive = inspect_archive(version)
    if args.baseline:
        result['preserved_glyphs'] = inspect_baseline(font, args.baseline)
    if args.rebuild:
        inspect_rebuild(archive)
        result['source_only_rebuild'] = 'byte-identical'
    result['files'] = {str(path.relative_to(ROOT)): sha(path) for path in (FONT, WEBFONT, archive)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
