#!/usr/bin/env python3
"""Install/restore a session-local tmux footer, preserving existing status rows."""
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess

from statusline import atomic_json, load_json


def tmux(*args):
    return subprocess.check_output(['tmux', *args], text=True).strip()


def local_option(session, option):
    # Querying a missing array index directly prints an empty entry, so test
    # existence against the actual local option listing first.
    present = any(line.startswith(option + ' ') for line in
                  tmux('show-options', '-t', session).splitlines())
    return tmux('show-options', '-qv', '-t', session, option) if present else None


def set_option(session, option, value):
    if value is None:
        tmux('set-option', '-qu', '-t', session, option)
    else:
        tmux('set-option', '-q', '-t', session, option, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'restore'])
    parser.add_argument('--pane', required=True, help='tmux pane ID, e.g. %%23')
    args = parser.parse_args()
    session = tmux('display-message', '-p', '-t', args.pane, '#{session_id}')
    socket = tmux('display-message', '-p', '-t', args.pane, '#{socket_path}')
    incarnation = tmux('display-message', '-p', '-t', args.pane, '#{pid}:#{session_created}')
    key = hashlib.sha256((socket + session + incarnation).encode()).hexdigest()[:20]
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    state_file = home / 'statusline-cache' / ('preview-' + key + '.json')
    state = load_json(state_file)
    if args.action == 'restore':
        if not state:
            print('No saved preview for this tmux session.')
            return
        for option, expected in state['installed'].items():
            if local_option(session, option) != expected:
                raise SystemExit(f'{option} changed since preview installation; leaving it untouched.')
        if state.get('format_snapshot') is not None and tmux('show-options', '-q', '-t', session, 'status-format') != state['format_snapshot']:
            raise SystemExit('Status rows changed since preview installation; leaving them untouched.')
        for option, value in state['original'].items():
            set_option(session, option, value)
        if not state.get('format_was_local', True):
            set_option(session, 'status-format', None)
        state_file.unlink()
        print('Restored the previous tmux status rows.')
        return
    if state:
        print('Preview is already installed; synced renderer changes apply on the next refresh.')
        return
    effective = tmux('show-options', '-Av', '-t', session, 'status')
    rows = {'on': 1, 'off': 0}.get(effective)
    if rows is None:
        rows = int(effective)
    if rows >= 5:
        raise SystemExit('All five tmux status rows are in use; existing rows left untouched.')
    option = f'status-format[{rows}]'
    script = Path(__file__).resolve().with_name('statusline.sh')
    # Only pane IDs enter the shell command at runtime, never names or paths
    # supplied by a conversation. tmux expands the active pane for this client.
    callback = f"#({shlex.quote(str(script))} --pane '#{{pane_id}}' --format tmux)"
    # A local array shadows the inherited array as a whole. Materialize each
    # existing visible row before adding ours, or the default window bar vanishes.
    installed = {f'status-format[{i}]': tmux('show-options', '-Av', '-t', session,
                                          f'status-format[{i}]') for i in range(rows)}
    installed[option] = '#[align=left,bg=#272822,fg=#909090]' + callback
    installed['status'] = str(rows + 1)
    original = {key: local_option(session, key) for key in installed}
    # tmux canonicalizes a status row count of 1 to 'on'.
    if installed['status'] == '1':
        installed['status'] = 'on'
    state = dict(original=original, installed=installed,
                 format_was_local=bool(tmux('show-options', '-q', '-t', session, 'status-format')))
    atomic_json(state_file, state)
    try:
        for key, value in installed.items():
            set_option(session, key, value)
    except subprocess.SubprocessError:
        for key, value in original.items():
            set_option(session, key, value)
        if not state['format_was_local']:
            set_option(session, 'status-format', None)
        state_file.unlink()
        raise
    state['format_snapshot'] = tmux('show-options', '-q', '-t', session, 'status-format')
    atomic_json(state_file, state)
    print(f'Preview installed in tmux session {session}; existing rows preserved.')


if __name__ == '__main__':
    main()
