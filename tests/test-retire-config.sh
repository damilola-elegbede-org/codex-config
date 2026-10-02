#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT" <<'PY'
import hashlib, importlib.util, pathlib, sys, tempfile
from unittest.mock import patch
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
    # Dangling links still protect their entire bundle.
    (home / 'copy').unlink()
    assert (home / 'statusline/preview.py').is_symlink()
    assert not (home / 'statusline/preview.py').exists()
    assert set(m.candidates(home)) == {name for name in m.SHIPPED if name.startswith('themes/')}
    # A linked parent must not allow deletion outside the Codex home.
    (home / 'statusline/preview.py').unlink()
    (home / 'statusline/preview.py').write_bytes(b'statusline/preview.py')
    (home / 'statusline').rename(home / 'external')
    (home / 'statusline').symlink_to(home / 'external', target_is_directory=True)
    assert all(name.startswith('themes/') for name in m.candidates(home))
    assert len(list((home / 'external').iterdir())) == 3
with tempfile.TemporaryDirectory() as temporary:
    home = pathlib.Path(temporary)
    for name in m.SHIPPED:
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_bytes(name.encode())
    marker = home / 'statusline-cache/preview-test.json'
    marker.parent.mkdir()
    marker.write_text('{}')
    plan = home / 'retirement-plan'
    plan.write_text('\n'.join(m.candidates(home)) + '\n')
    assert set(plan.read_text().splitlines()) == {name for name in m.SHIPPED if name.startswith('themes/')}
    # The bundle becomes eligible AFTER the backup plan is made. It must survive.
    marker.unlink()
    with patch.object(sys, 'argv', ['retire-config.py', str(home), '--remove', '--plan', str(plan)]):
        m.main()
    assert all((home / name).exists() for name in m.SHIPPED if name.startswith('statusline/'))
    assert all(not (home / name).exists() for name in m.SHIPPED if name.startswith('themes/'))
    # An empty plan authorizes no removal; omitting the plan is rejected.
    plan.write_text('')
    with patch.object(sys, 'argv', ['retire-config.py', str(home), '--remove', '--plan', str(plan)]):
        m.main()
    with patch.object(sys, 'argv', ['retire-config.py', str(home), '--remove']):
        try:
            m.main()
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError('removal without a backup plan was accepted')
    assert all((home / name).exists() for name in m.SHIPPED if name.startswith('statusline/'))
print('PASS: linked bundles survive; removal stays within the original backup plan')
PY
