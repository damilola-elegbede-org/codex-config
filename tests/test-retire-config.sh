#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import hashlib, importlib.util, pathlib, sys, tempfile
spec = importlib.util.spec_from_file_location('retire', pathlib.Path(sys.argv[1]) / 'scripts/retire-config.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as temporary:
    home = pathlib.Path(temporary)
    (home / 'statusline').mkdir()
    (home / 'themes').mkdir()
    for name in m.SHIPPED:
        content = name.encode()
        (home / name).write_bytes(content)
        m.SHIPPED[name] = hashlib.sha256(content).hexdigest()
    assert set(m.candidates(home)) == set(m.SHIPPED)
    # One customized dependency preserves the entire bundle.
    (home / 'statusline/statusline.py').write_text('custom implementation')
    assert all(name.startswith('themes/') for name in m.candidates(home))
    (home / 'statusline/statusline.py').write_bytes(b'statusline/statusline.py')
    # Saved preview state preserves the ability to restore it manually.
    (home / 'statusline-cache').mkdir()
    (home / 'statusline-cache/preview-test.json').write_text('{}')
    assert all(name.startswith('themes/') for name in m.candidates(home))
    (home / 'statusline-cache/preview-test.json').unlink()
    assert len(m.candidates(home)) == 6
    # A symlink is never deleted as if it were an owned deployed file.
    (home / 'statusline/preview.py').unlink()
    (home / 'copy').write_bytes(b'statusline/preview.py')
    (home / 'statusline/preview.py').symlink_to(home / 'copy')
    assert all(name.startswith('themes/') for name in m.candidates(home))
    # A linked parent must not allow deletion outside the Codex home.
    (home / 'statusline/preview.py').unlink()
    (home / 'statusline/preview.py').write_bytes(b'statusline/preview.py')
    (home / 'statusline').rename(home / 'external')
    (home / 'statusline').symlink_to(home / 'external', target_is_directory=True)
    assert all(name.startswith('themes/') for name in m.candidates(home))
    assert len(list((home / 'external').iterdir())) == 3
print('PASS: retirement preserves customized bundles, active restore state, and symlinks')
PY
