#!/usr/bin/env python3
"""Build the DeathMine bitmap font and reproducible ZIP using Python 3 only."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'pack'
GLYPHS = {
    'D': ['11110','10001','10001','10001','10001','10001','11110'],
    'e': ['00000','00000','01110','10001','11111','10000','01111'],
    'a': ['00000','00000','01110','00001','01111','10001','01111'],
    't': ['010','010','111','010','010','010','001'],
    'h': ['10000','10000','10110','11001','10001','10001','10001'],
    '☠': ['001111100','011111110','011010110','001111100','000101000','100111001','011000110'],
    'M': ['10001','11011','10101','10101','10001','10001','10001'],
    'i': ['1','0','1','1','1','1','1'],
    'n': ['00000','00000','11110','10001','10001','10001','10001'],
}


def png(path, width, height, rgba):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + bytes(rgba[y * width * 4:(y + 1) * width * 4]) for y in range(height))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def draw_logo(scale):
    text = 'Death☠Mine'
    width = sum(len(GLYPHS[c][0]) for c in text) + len(text) - 1
    height = 8  # one transparent row below the seven-pixel lettering
    data = bytearray(width * height * scale * scale * 4)
    cursor = 0
    colors = [(255,220,60),(255,199,32),(255,177,12),(255,153,0),(255,132,0),(248,108,0),(232,78,0)]
    for c in text:
        for y, row in enumerate(GLYPHS[c]):
            for x, bit in enumerate(row):
                if bit == '1':
                    for sy in range(scale):
                        for sx in range(scale):
                            i = (((y * scale + sy) * width * scale) + (cursor + x) * scale + sx) * 4
                            data[i:i + 4] = bytes((*colors[y], 255))
        cursor += len(GLYPHS[c][0]) + 1
    return width * scale, height * scale, data


def main():
    providers = []
    for name, char, scale, ascent in [('tab', '\ue001', 2, 13), ('scoreboard', '\ue002', 1, 7)]:
        w, h, pixels = draw_logo(scale)
        png(PACK / f'assets/deathmine/textures/font/{name}.png', w, h, pixels)
        providers.append({'type': 'bitmap', 'file': f'deathmine:font/{name}.png', 'ascent': ascent, 'height': h, 'chars': [char]})
    for relative in ['assets/minecraft/font/default.json', 'assets/deathmine/font/logo.json']:
        p = PACK / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({'providers': providers}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (PACK / 'pack.mcmeta').write_text(json.dumps({'pack': {
        'pack_format': 9,
        'supported_formats': {'min_inclusive': 9, 'max_inclusive': 97},
        'min_format': 9,
        'max_format': [97, 1],
        'description': 'Death☠Mine | TAB + Scoreboard | Java 1.19–26.3'
    }}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not (PACK / 'pack.png').is_file():
        raise SystemExit('Missing pack/pack.png; restore the tracked icon first.')
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    archive = out / 'DeathMine-RP.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(PACK.rglob('*')):
            if p.is_file():
                info = zipfile.ZipInfo(p.relative_to(PACK).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, p.read_bytes())
    for name in ['sha1', 'sha256']:
        digest = hashlib.new(name, archive.read_bytes()).hexdigest()
        (out / f'DeathMine-RP.zip.{name}').write_text(f'{digest}  DeathMine-RP.zip\n', encoding='ascii')
        print(f'{name}: {digest}')
    print(f'Built {archive} ({archive.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
