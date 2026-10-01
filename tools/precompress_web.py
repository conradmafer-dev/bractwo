"""Build gzip sidecars that aiohttp serves through Accept-Encoding negotiation.

Run during the image build, after copying web assets. Originals remain available
for clients that do not accept gzip; binary images are already compressed.
"""
import argparse
import gzip
from io import BytesIO
from pathlib import Path


TEXT_SUFFIXES = {'.js', '.css', '.svg'}


def precompress_web(root: Path) -> tuple[int, int, int]:
    """Return file count, original bytes and gzip bytes for generated sidecars."""
    if not root.is_dir():
        raise NotADirectoryError(root)

    count = original_bytes = gzip_bytes = 0
    for path in sorted(root.rglob('*')):
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        source = path.read_bytes()
        buffer = BytesIO()
        # Omit both the timestamp and filename so repeated builds are identical.
        with gzip.GzipFile(fileobj=buffer, mode='wb', filename='', mtime=0,
                           compresslevel=9) as compressed:
            compressed.write(source)
        payload = buffer.getvalue()
        sidecar = path.with_name(path.name + '.gz')
        if len(payload) >= len(source):
            sidecar.unlink(missing_ok=True)
            continue
        sidecar.write_bytes(payload)
        count += 1
        original_bytes += len(source)
        gzip_bytes += len(payload)
    return count, original_bytes, gzip_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('web'))
    args = parser.parse_args()
    count, original_bytes, gzip_bytes = precompress_web(args.directory)
    print(f'Precompressed {count} web assets: {original_bytes:,} -> '
          f'{gzip_bytes:,} bytes ({original_bytes - gzip_bytes:,} bytes saved).')


if __name__ == '__main__':
    main()
