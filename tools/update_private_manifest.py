from __future__ import annotations

import hashlib
import json
from pathlib import Path

root = Path('private/rollpig-pjsk')
manifest_path = root / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))

def meta(path: str) -> dict[str, object]:
    file_path = root / path
    data = file_path.read_bytes()
    return {'path': path, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

manifest['pig_json'] = meta('pig.json')
manifest.setdefault('optional_files', {})['pig_rules'] = meta('pig_rules.json')
manifest.setdefault('optional_files', {})['pig_overrides'] = meta('pig_overrides.json')
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(manifest_path)
