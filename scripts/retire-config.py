#!/usr/bin/env python3
"""Retire unchanged withdrawn configuration files; never alter tmux."""
import argparse
import hashlib
from pathlib import Path
import sys

SHIPPED = {
    'themes/executive.tmTheme': 'ed391d50ecb3ad9ac3ee6808d3906b465de3bdfb9adb1e03bb32eb654379e15a',
    'themes/README.md': '16a553be9df9cad6b09efeb3446944a15590228657eb278ce8e19b5e5081e217',
    'themes/monokai-LICENSE.txt': 'b49f1b1dc97c416ae65a38497d251a0c90357473f93d6d2d224f24fea9eb8439',
    'statusline/preview.py': '84515a9934a46208150d7d3adfb4d898c858ef4c27e0cf89accb1f00cb1e9a58',
    'statusline/statusline.py': 'f9c3bb74e05cbcc0e524fdf6a07154a17a6eb8653a060abf93b51981b58c7bfa',
    'statusline/statusline.sh': '89c1dcb3914e45f5e01dc7c8114e3e9eec79e376f54370939416d02774a3f3cb',
}


def candidates(home):
    result = []
    for group in ('statusline', 'themes'):
        paths = [name for name in SHIPPED if name.startswith(group + '/') and (home / name).exists()]
        if not paths:
            continue
        if group == 'statusline' and any((home / 'statusline-cache').glob('preview-*.json')):
            print('Legacy preview state exists; retaining its restore helper. No tmux settings changed.', file=sys.stderr)
            continue
        if (home / group).is_symlink() or any(
            (home / name).is_symlink() or not (home / name).is_file() or
            hashlib.sha256((home / name).read_bytes()).hexdigest() != SHIPPED[name]
            for name in paths
        ):
            print(f'Retired {group} files were customized or linked; preserving them.', file=sys.stderr)
            continue
        result.extend(paths)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('home', type=Path)
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    for name in candidates(args.home):
        if args.remove:
            (args.home / name).unlink()
            print('removed retired config: ' + name)
        else:
            print(name)


if __name__ == '__main__':
    main()
