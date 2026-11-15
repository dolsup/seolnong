#!/usr/bin/env python3
"""Rebuild the release TTF, WOFF2, and four-file download ZIP.

From the repository root, run these commands in a Python 3.12 environment:
    python -m pip install -r requirements.txt
    python build.py
"""
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from src.font_builder import FAMILY, RELEASE_TIMESTAMP, VERSION, build

ROOT = Path(__file__).resolve().parent


def main():
    readme = ROOT / 'fonts' / 'README.txt'
    license_file = ROOT / 'OFL.txt'
    for path in (readme, license_file):
        if not path.is_file():
            raise FileNotFoundError(f'Required release document is missing: {path}')

    ttf, woff2 = build(ROOT / 'fonts')
    release_name = f'{FAMILY}-{VERSION}'
    archive_path = ROOT / 'downloads' / f'{release_name}.zip'
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    # Match the release date and file permissions independently of the host.
    date = datetime.fromtimestamp(RELEASE_TIMESTAMP - 2082844800, timezone.utc)
    date_tuple = (date.year, date.month, date.day, date.hour, date.minute, date.second)
    files = ((ttf, ttf.name), (woff2, woff2.name),
             (readme, 'README.txt'), (license_file, 'OFL.txt'))
    with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path, filename in files:
            entry = ZipInfo(f'{release_name}/{filename}', date_time=date_tuple)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes(), compresslevel=9)
    print(f'ZIP saved: {archive_path}', flush=True)


if __name__ == '__main__':
    main()
