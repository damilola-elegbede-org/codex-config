import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('statusline', ROOT / 'system-configs/.codex/statusline/statusline.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CompanionTests(unittest.TestCase):
    def window(self, pct=50, elapsed=302400):
        now = 1000000
        return dict(used_percent=pct, resets_at=now + 604800 - elapsed,
                    window_minutes=10080)

    def test_context_uses_last_turn_and_codex_rounding(self):
        self.assertEqual(m.context_used(dict(model_context_window=258400,
            last_token_usage=dict(total_tokens=135200),
            total_token_usage=dict(total_tokens=99999999))), 50)
        self.assertEqual(m.context_used(dict(model_context_window=258400,
            last_token_usage=dict(total_tokens=12000))), 0)
        self.assertIsNone(m.context_used({}))
        self.assertIsNone(m.context_used(dict(model_context_window=258400)))

    def test_weekly_can_be_primary_or_secondary(self):
        window = self.window()
        for key in ['primary', 'secondary']:
            self.assertEqual(m.weekly_window(dict(limit_id='codex', **{key:window})), window)
        self.assertIsNone(m.weekly_window(dict(primary=dict(window_minutes=300))))
        self.assertIsNone(m.weekly_window(dict(limit_id='other', primary=window)))

    def test_burn_rounds_before_color(self):
        for percent, expected, color in [(20,.4,'blue'), (50,1,'green'),
                (54.5,1.1,'yellow'), (64.5,1.3,'orange'), (74.5,1.5,'red')]:
            self.assertEqual(m.burn(self.window(percent),1000000,1000000),(expected,color))

    def test_no_claude_warmup_and_missing_reset(self):
        self.assertEqual(m.burn(self.window(19,6000),1000000,1000000),(19.2,'red'))
        for elapsed in [0,-1,604800,700000]:
            self.assertEqual(m.burn(self.window(elapsed=elapsed),1000000,1000000),(None,'gray'))
        self.assertEqual(m.burn(self.window(),1000000,999000),(None,'gray'))
        self.assertEqual(m.burn(None,1000000,1000000),(None,'gray'))

    def test_bars_and_control_escaping(self):
        self.assertEqual(m.bar(9),'░░░░░')
        self.assertEqual(m.bar(10),'▓░░░░')
        self.assertEqual(m.bar(100),'▓▓▓▓▓')
        rendered=m.styled('#[fg=red]#{pane_id}\n\033', 'session','tmux')
        self.assertIn('##[fg=red]##{pane_id}',rendered)
        self.assertNotIn('\n',rendered)
        self.assertNotIn('\033',rendered)

    def test_selection_tracks_title_and_rejects_ambiguity(self):
        index={'a':dict(thread_name='codex-config'),'b':dict(thread_name='rewrite')}
        self.assertEqual(m.resolve_thread(index,'⠸ codex-config | BareClaude'),'a')
        self.assertEqual(m.resolve_thread(index,'rewrite | BareClaude'),'b')
        self.assertIsNone(m.resolve_thread(index,'unknown | BareClaude'))
        index['c']=dict(thread_name='rewrite')
        self.assertIsNone(m.resolve_thread(index,'rewrite | BareClaude'))

    def test_incremental_cache_handles_partial_appends_and_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary)
            (home/'sessions').mkdir()
            ident='00000000-0000-0000-0000-000000000001'
            path=home/'sessions'/f'rollout-test-{ident}.jsonl'
            first=json.dumps(dict(type='turn_context',payload=dict(cwd='/tmp',model='gpt-6-astra')))+'\n'
            second=json.dumps(dict(type='turn_context',payload=dict(effort='high')))+'\n'
            path.write_text(first+second[:20])
            self.assertNotIn('effort',m.telemetry(home,ident))
            with path.open('a') as f:f.write(second[20:])
            self.assertEqual(m.telemetry(home,ident)['effort'],'high')
            self.assertEqual(m.telemetry(home,ident)['model'],'gpt-6-astra')
            path.write_text(second)
            self.assertNotIn('model',m.telemetry(home,ident))
            self.assertEqual(m.telemetry(home,ident)['effort'],'high')


if __name__ == '__main__':
    unittest.main()
