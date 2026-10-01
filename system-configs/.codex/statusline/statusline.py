#!/usr/bin/env python3
"""Read-only Codex telemetry renderer. No credentials or network requests."""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

COLORS = dict(session='#C9B1FF', model='#FF5555', branch='#FF8700',
              folder='#ADD8E6', style='#FFFF00', green='#28FE14',
              gray='#909090', blue='#00AFFF', yellow='#FFFF00',
              orange='#FF8700', red='#FF5555')
WEEK_MINUTES = 10080
STALE_AFTER = 900  # Show snapshot age; suppress burn after 15 minutes.


def command(args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL,
                                       timeout=3).strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.statusline-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(data, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def epoch(value):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError, AttributeError):
        return 0


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def context_used(info):
    window = info.get('model_context_window')
    used = (info.get('last_token_usage') or {}).get('total_tokens')
    if not number(window) or not number(used) or used < 0 or window <= 0:
        return None
    # Codex TokenUsage::percent_of_context_window_remaining, including its
    # 12k baseline and positive half-up rounding (not Python's banker's round).
    if window <= 12000:
        return 100
    remaining = max(0, window - 12000 - max(0, used - 12000)) / (window - 12000)
    return 100 - math.floor(min(1, remaining) * 100 + 0.5)


def weekly_window(rates):
    if rates.get('limit_id') not in (None, 'codex'):
        return None
    for key in ('primary', 'secondary'):
        window = rates.get(key) or {}
        if window.get('window_minutes') == WEEK_MINUTES:
            used, reset = window.get('used_percent'), window.get('resets_at')
            if number(used) and 0 <= used <= 100 and number(reset):
                return window
    return None


def burn(window, now, observed):
    if not window or not observed or now - observed > STALE_AFTER or observed > now + 60:
        return None, 'gray'
    duration = window['window_minutes'] * 60
    elapsed = now - (window['resets_at'] - duration)
    if not 0 < elapsed < duration:
        return None, 'gray'
    value = math.floor((window['used_percent'] / 100 * duration / elapsed) * 10 + 0.5) / 10
    tier = ('blue' if value < .5 else 'green' if value < 1.1 else
            'yellow' if value < 1.3 else 'orange' if value < 1.5 else 'red')
    return value, tier


def bar(percent):
    filled = min(5, max(0, math.floor((percent + 10) / 20)))
    return '▓' * filled + '░' * (5 - filled)


def clean(value):
    # Strip terminal controls/newlines. Escape tmux syntax separately.
    return ''.join(c for c in str(value) if c.isprintable())


def styled(value, color, mode):
    value = clean(value)
    if mode == 'tmux':
        return f'#[fg={COLORS[color]}]' + value.replace('#', '##')
    if mode == 'ansi':
        rgb = ';'.join(str(int(COLORS[color][i:i+2], 16)) for i in (1, 3, 5))
        return f'\033[38;2;{rgb}m{value}\033[0m'
    return value


def sessions(home):
    latest = {}
    try:
        with (home / 'session_index.jsonl').open() as source:
            for line in source:
                try:
                    item = json.loads(line)
                    latest[item['id']] = item
                except (ValueError, KeyError):
                    continue
    except OSError:
        pass
    return latest


def resolve_thread(index, title):
    # Titles are "[spinner ]conversation | folder". Never guess between two
    # conversations with the same name; suppress metrics if ambiguous.
    title = title.rsplit(' | ', 1)[0]
    matches = []
    for ident, item in index.items():
        name = item.get('thread_name', '')
        if name and (title == name or (len(title) == len(name) + 2 and title[1:] == ' ' + name)):
            matches.append(ident)
    return matches[0] if len(matches) == 1 else None


def telemetry(home, ident):
    if not ident or not re.fullmatch(r'[0-9a-fA-F-]{36}', ident):
        return {}
    cache_path = home / 'statusline-cache' / (ident + '.json')
    cache = load_json(cache_path)
    path = Path(cache.get('path', '/nonexistent'))
    # Never trust a cache pointer outside the sessions directory.
    if not path.is_relative_to(home / 'sessions') or not path.is_file():
        paths = list((home / 'sessions').glob(f'**/rollout-*-{ident}.jsonl'))
        if len(paths) != 1:
            return {}
        path = paths[0]
    stat = path.stat()
    if cache.get('inode') != stat.st_ino or cache.get('offset', 0) > stat.st_size:
        cache = {}
    offset = cache.get('offset', 0)
    state = cache.get('state', {})
    with path.open('rb') as source:
        source.seek(offset)
        while True:
            line = source.readline()
            if not line or not line.endswith(b'\n'):
                break  # A writer may still be appending this event.
            offset = source.tell()
            try:
                item = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            payload = item.get('payload') or {}
            kind = item.get('type')
            if kind == 'turn_context':
                for key in ('cwd', 'model', 'effort'):
                    if payload.get(key):
                        state[key] = payload[key]
            elif kind == 'event_msg' and payload.get('type') == 'token_count':
                if payload.get('info'):
                    state['info'] = payload['info']
                if payload.get('rate_limits'):
                    state['rates'] = payload['rate_limits']
                    state['observed'] = epoch(item.get('timestamp'))
    if offset != cache.get('offset'):
        atomic_json(cache_path, dict(path=str(path), inode=stat.st_ino, offset=offset, state=state))
    return state


def model_name(model, effort):
    label = model.upper().replace('-', ' ')
    # Keep familiar GPT-6 typography and readable product names.
    label = re.sub(r'^GPT (\d+(?:\.\d+)?)', r'GPT-\1', label).title().replace('Gpt-', 'GPT-')
    return label + (' ' + effort.title() if effort else '')


def snapshot(home, thread=None, pane=None):
    index = sessions(home)
    title = ''
    width = 180
    version = '--'
    if pane:
        details = command(['tmux', 'display-message', '-p', '-t', pane,
                           '#{pane_current_command}\n#{pane_title}\n#{pane_width}']).splitlines()
        if len(details) != 3 or details[0] != 'codex':
            return None
        title, width = details[1], int(details[2])
        thread = resolve_thread(index, title)
        # The rendered footer reports the actual running client version;
        # session_meta.cli_version can belong to a different resumed client.
        screen = command(['tmux', 'capture-pane', '-p', '-t', pane, '-S', '-5'])
        for line in reversed(screen.splitlines()):
            if ' · ' in line:
                match = re.search(r' · (\d+\.\d+\.\d+(?:[-+][\w.]+)?)(?: · |$)', line.strip())
                if match:
                    version = match[1]
                    break
    state = telemetry(home, thread)
    name = index.get(thread, {}).get('thread_name') or title.rsplit(' | ', 1)[0] or '--'
    cwd = state.get('cwd')
    branch = '--'
    if cwd and Path(cwd).is_dir():
        branch = command(['git', '-C', cwd, 'symbolic-ref', '--short', '-q', 'HEAD'])
        if not branch:
            sha = command(['git', '-C', cwd, 'rev-parse', '--short', 'HEAD'])
            branch = ('detached:' + sha) if sha else 'no-git'
    now = time.time()
    window = weekly_window(state.get('rates', {}))
    observed = state.get('observed', 0)
    stale = bool(window and now - observed > STALE_AFTER)
    if window and window['resets_at'] <= now:
        window = None  # An expired quota snapshot is not a new week's usage.
    value, tier = burn(window, now, observed)
    return dict(session=name, model=model_name(state.get('model', '--'), state.get('effort', '')),
                branch=branch, folder=Path(cwd).name if cwd else '--', style='Executive',
                version=version, context=context_used(state.get('info', {})),
                usage=window['used_percent'] if window else None,
                burn=value, burn_color=tier, stale=stale,
                age_minutes=max(0, int((now - observed) / 60)) if observed else None,
                width=width, thread=thread)


def render(data, mode='plain'):
    if data is None:
        return ''
    parts = []
    for key, color in [('session', 'session'), ('model', 'model'), ('branch', 'branch'),
                       ('folder', 'folder'), ('style', 'style'), ('version', 'green')]:
        parts.append(styled(data[key], color, mode))
    for key, label in [('context', 'Context'), ('usage', 'Usage')]:
        value = data[key]
        text = '--' if value is None else f'{value:g}%'
        if value is not None and data['width'] >= 175:
            text = bar(value) + ' ' + text
        suffix = styled(' weekly', 'gray', mode) if key == 'usage' else ''
        parts.append(styled(label + ' ', 'gray', mode) + styled(text, 'green' if value is not None else 'gray', mode) + suffix)
    text = '--' if data['burn'] is None else f"{data['burn']:.1f}x"
    parts.append(styled('Burn ', 'gray', mode) + styled(text, data['burn_color'], mode))
    if data['stale']:
        parts.append(styled(f"quota {data['age_minutes']}m old", 'gray', mode))
    result = styled(' · ', 'gray', mode).join(parts)
    return result + ('#[default]' if mode == 'tmux' else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))))
    parser.add_argument('--thread')
    parser.add_argument('--pane')
    parser.add_argument('--format', choices=['plain', 'ansi', 'tmux', 'json'], default='plain')
    args = parser.parse_args()
    try:
        data = snapshot(args.home.resolve(), args.thread, args.pane)
        print(json.dumps(data) if args.format == 'json' else render(data, args.format))
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Keep the footer usable during partial writes or unavailable telemetry.
        print(styled('Codex status unavailable', 'gray', args.format))
        if args.format != 'tmux':
            raise SystemExit(str(error))


if __name__ == '__main__':
    main()
