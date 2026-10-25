#!/usr/bin/env python3
"""Check ZIP structure, font mappings, PNGs, metadata, and distribution hashes."""
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive = ROOT / 'dist/DeathMine-RP.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        assert 'pack.mcmeta' in names and 'pack.png' in names
        assert all(not n.startswith(('/', 'pack/', '../')) and '..' not in n.split('/') for n in names)
        meta = json.loads(z.read('pack.mcmeta'))['pack']
        assert meta['pack_format'] == meta['min_format'] == 9
        assert meta['supported_formats'] == {'min_inclusive': 9, 'max_inclusive': 97}
        assert meta['max_format'] == [97, 1]
        font = json.loads(z.read('assets/minecraft/font/default.json'))
        assert font == json.loads(z.read('assets/deathmine/font/logo.json'))
        assert {p['chars'][0] for p in font['providers']} == {'\ue001', '\ue002'}
        for provider in font['providers']:
            assert provider['type'] == 'bitmap' and provider['ascent'] <= provider['height']
            namespace, path = provider['file'].split(':')
            data = z.read(f'assets/{namespace}/textures/{path}')
            assert data[:8] == b'\x89PNG\r\n\x1a\n'
            pos = 8
            compressed = b''
            while pos < len(data):
                length = struct.unpack('>I', data[pos:pos+4])[0]
                kind = data[pos+4:pos+8]
                payload = data[pos+8:pos+8+length]
                assert zlib.crc32(kind + payload) & 0xffffffff == struct.unpack('>I', data[pos+8+length:pos+12+length])[0]
                if kind == b'IHDR':
                    w, h, depth, color, *_ = struct.unpack('>IIBBBBB', payload)
                    assert depth == 8 and color == 6 and h == provider['height'] and w > h
                if kind == b'IDAT':
                    compressed += payload
                pos += length + 12
            pixels = zlib.decompress(compressed)
            assert len(pixels) == h * (w * 4 + 1)
            assert any(pixels)
            print(f"Font {ord(provider['chars'][0]):04X}: {w}x{h}, ascent {provider['ascent']}, PNG CRC OK")
        assert set(names) == {p.relative_to(ROOT / 'pack').as_posix() for p in (ROOT / 'pack').rglob('*') if p.is_file()}
        for name in names:
            assert z.read(name) == (ROOT / 'pack' / name).read_bytes()
    for algorithm in ['sha1', 'sha256']:
        expected = (ROOT / f'dist/DeathMine-RP.zip.{algorithm}').read_text().split()[0]
        assert hashlib.new(algorithm, archive.read_bytes()).hexdigest() == expected
    for name in ['TAB-modern.yml', 'TAB-legacy.yml']:
        text = (ROOT / 'examples' / name).read_text(encoding='utf-8')
        assert "'&f\ue001'" in text and "'&f\ue002'" in text
    print('PASS: archive, source parity, metadata, 2 font glyphs, 2 config examples, SHA-1/SHA-256')
    print('Minecraft client rendering and TAB integration require an in-game test; not executed here.')


if __name__ == '__main__':
    main()
