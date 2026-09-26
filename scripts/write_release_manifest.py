#!/usr/bin/env python3
"""Attach source revision and content hashes to an already built release directory."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    root = args.directory.resolve(strict=True)
    if len(args.revision) != 40 or any(char not in '0123456789abcdef' for char in args.revision):
        parser.error('revision must be a full Git commit SHA')
    (root / 'REVISION').write_text(args.revision + '\n', encoding='utf-8')
    files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(root.rglob('*')) if path.is_file() and path.name != 'BUILD_INFO.json'}
    manifest = {'revision': args.revision, 'builtAt': datetime.now(timezone.utc).isoformat(), 'sha256': files}
    (root / 'BUILD_INFO.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{root.name}: recorded {len(files)} file hashes for {args.revision[:12]}')


if __name__ == '__main__':
    main()
