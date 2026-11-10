"""Exercise the installed hook wire interface without model or network calls."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "system-configs/.codex/hooks/codex-hooks.py"


class HookTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.cwd = self.root / "repo"
        self.cwd.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "CODEX_HOME": str(self.home / ".codex"),
                    "CODEX_SKILLS_HOME": str(self.home / ".agents/skills"),
                    "CODEX_HOOKS_JEV": str(self.root / "jev-mock")}
        self.mock = Path(self.env["CODEX_HOOKS_JEV"])
        self.mock.write_text('#!/usr/bin/env python3\nimport sys\nsys.exit(3)\n')
        self.mock.chmod(0o700)

    def invoke(self, event, **kwargs):
        payload = {"hook_event_name": event, "session_id": "session-1", "turn_id": "turn-1",
                   "cwd": str(self.cwd), **kwargs}
        result = subprocess.run(["python3", str(SCRIPT)], input=json.dumps(payload),
                                env=self.env, text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout or "{}")

    def context(self, output):
        return output.get("hookSpecificOutput", {}).get("additionalContext", "")

    def bash(self, command, event="PreToolUse", **kwargs):
        return self.invoke(event, tool_name="Bash", tool_input={"command": command}, **kwargs)

    def test_git_guard_matches_commands_not_quoted_examples(self):
        for command in ['git commit --no-verify -m fix', 'git -C /tmp commit --no-verify',
                        'env FOO=bar git push --no-verify origin branch',
                        'sh -c "git commit --no-verify -m fix"']:
            output = self.bash(command)
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny", command)
        for command in ['echo "git commit --no-verify"', "printf '%s' 'git commit --no-verify'",
                        'git log --grep=--no-verify', 'git commit -m "explain --no-verify"']:
            self.assertNotIn("permissionDecision", self.bash(command).get("hookSpecificOutput", {}), command)

    def test_destructive_git_and_bulk_stage_advice_do_not_invent_approval(self):
        for command in ['git reset --hard', 'git push --force origin feature', 'git add .']:
            output = self.bash(command)
            self.assertIn("authorization", self.context(output))
            self.assertNotIn("permissionDecision", output.get("hookSpecificOutput", {}))
        self.assertEqual(self.bash('git push --force-with-lease origin feature'), {})

    def test_git_hook_bypass_long_option_abbreviations(self):
        for command in ['git commit --no-veri -m change', 'git push --no-veri origin feature',
                        'git am --no-v patch.mbox', 'git commit --no-verif -m change']:
            output = self.bash(command)
            self.assertEqual(output.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny', command)
        for command in ['git commit --no-verbose -m change', 'git push --no-verbose origin feature',
                        'echo "git commit --no-veri"', "printf '%s' 'git am --no-v'",
                        'git commit -m "--no-veri"', 'git commit --message=--no-veri',
                        'git commit -m--no-veri']:
            self.assertNotIn('permissionDecision', self.bash(command).get('hookSpecificOutput', {}), command)

    def test_apply_patch_secret_guard_only_added_production_content(self):
        token = 'ghp_' + 'A' * 36
        patch = '*** Begin Patch\n*** Add File: app.py\n+TOKEN = "' + token + '"\n*** End Patch'
        output = self.invoke("PreToolUse", tool_name="apply_patch", tool_input={"command": patch})
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn(token, json.dumps(output))
        for safe in [patch.replace('app.py', 'tests/test_tokens.py'), patch.replace('+TOKEN', '-TOKEN')]:
            output = self.invoke("PreToolUse", tool_name="apply_patch", tool_input={"command": safe})
            self.assertNotIn("permissionDecision", output.get("hookSpecificOutput", {}))

    def test_added_temporary_document_gets_advice_not_rejection(self):
        patch = '*** Begin Patch\n*** Add File: analysis-report.md\n+# Results\n*** End Patch'
        output = self.invoke("PreToolUse", tool_name="apply_patch", tool_input={"command": patch})
        self.assertIn('.tmp/', self.context(output))
        self.assertNotIn('permissionDecision', output.get('hookSpecificOutput', {}))

    def test_session_start_reports_real_worktree_and_compaction_reminder(self):
        subprocess.run(['git', 'init', '-q', str(self.cwd)], check=True)
        output = self.invoke('SessionStart', source='compact')
        self.assertIn(str(self.cwd), self.context(output))
        self.assertIn('acceptance', self.context(output))
        self.assertNotIn('continue', output)

    def test_retry_counter_requires_known_exit_and_preserves_tool_result(self):
        first = self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1, 'output': 'failed'}, tool_use_id='1')
        self.assertIn('failure 1', self.context(first))
        self.assertEqual(self.bash('make test', 'PostToolUse', tool_response='uncertain'), {})
        second = self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1, 'output': 'failed'}, tool_use_id='2')
        self.assertIn('failure 2', self.context(second))
        self.assertNotIn('decision', second)
        self.assertNotIn('continue', second)
        self.assertEqual(self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1}, tool_use_id='2'), {})
        self.bash('make test', 'PostToolUse', tool_response={'exit_code': 0})
        reset = self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1})
        self.assertIn('failure 1', self.context(reset))

    def test_jev_skill_suggestion_is_from_known_catalog_not_model_text(self):
        skills = Path(self.env['CODEX_SKILLS_HOME'])
        (skills / 'verify').mkdir(parents=True)
        (skills / 'verify/SKILL.md').write_text('---\nname: "verify"\ndescription: "Verify checks and failures"\n---\nbody')
        self.mock.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"answers":{k:{"probability":.95} for k in r["questions"]}}))\n')
        output = self.invoke('UserPromptSubmit', prompt='Please verify all checks and fix failures')
        self.assertIn('verify', self.context(output))
        self.assertIn('available', self.context(output))
        self.assertNotIn('permissionDecision', json.dumps(output))

    def test_native_stdout_never_supplies_exit_status_even_when_it_looks_structured(self):
        envelope = 'Chunk ID: c83abc\nWall time: 0.002 seconds\nProcess exited with code 7\nFinal output:\nfixture\n'
        for result in [envelope, {'type':'text','text':envelope}, {'output':envelope},
                       '{"exit_code":0}', 'command says Process exited with code 7', 'prefix\n' + envelope]:
            self.assertEqual(self.bash('unknown', 'PostToolUse', tool_response=result), {})
        # Captured from native Codex 0.166.0: even exit 7 supplies only stdout.
        self.assertEqual(self.bash("printf 'fixture\\n'; exit 7", 'PostToolUse', tool_response='fixture\n'), {})
        diagnostic = self.bash('pytest', 'PostToolUse', tool_response='AssertionError: expected true\n')
        self.assertIn('exit status is unavailable', self.context(diagnostic))
        self.assertNotIn('Command failure', self.context(diagnostic))

    def test_automatic_jev_egress_contains_only_fixed_labels(self):
        record = self.root / 'request.json'
        self.mock.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nopen(' + repr(str(record)) + ',"w").write(json.dumps(r))\nprint("{}")\n')
        marker = 'PRIVATE-CONTENT-8723'
        self.bash('cat ~/work/private; exit 7', 'PostToolUse',
                  tool_response={'exit_code':7, 'output':'AssertionError: ' + marker})
        request = json.loads(record.read_text())
        self.assertEqual(request['state']['diagnostic_markers'], ['assertion'])
        self.assertNotIn(marker, record.read_text())
        self.assertNotIn('cat', record.read_text())
        skills = Path(self.env['CODEX_SKILLS_HOME'])
        (skills / 'verify').mkdir(parents=True)
        (skills / 'verify/SKILL.md').write_text('---\nname: verify\ndescription: ' + marker + '\n---')
        self.invoke('UserPromptSubmit', prompt='Please verify checks; pasted Slack: ' + marker)
        request = json.loads(record.read_text())
        self.assertIn('verify', request['state']['intent_tags'])
        self.assertNotIn(marker, record.read_text())

    def test_git_guard_preserves_heredoc_body_but_checks_following_commands(self):
        literal = "cat <<'DOC'\ngit commit --no-verify\nDOC\n"
        self.assertEqual(self.bash(literal), {})
        self.assertEqual(self.bash('cat <<-"DOC"\n\tgit commit -n\n\tDOC\n'), {})
        output = self.bash(literal + 'git commit -n -m change\n')
        self.assertEqual(output['hookSpecificOutput']['permissionDecision'], 'deny')
        for command in ['git commit -an -m change', 'git commit -anm change', 'cat <<<"data"\ngit commit -an -m change']:
            output = self.bash(command)
            self.assertEqual(output['hookSpecificOutput']['permissionDecision'], 'deny', command)
        for command in ['git commit -mnot-a-flag', 'git commit -amnot-a-flag']:
            self.assertEqual(self.bash(command), {}, command)
        self.assertEqual(self.bash('git push -n origin feature'), {})

    def test_failures_in_other_worktrees_do_not_share_counter(self):
        self.bash('make test', 'PostToolUse', tool_response={'exit_code':1})
        other = self.root / 'other'
        other.mkdir()
        output = self.bash('make test', 'PostToolUse', cwd=str(other), tool_response={'exit_code':1})
        self.assertIn('failure 1', self.context(output))

    def test_hook_disable_git_flag_and_semicolon_inside_quotes(self):
        output = self.bash('git -c core.hooksPath=/dev/null commit -m fix')
        self.assertEqual(output['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(self.bash('printf "%s" "; git commit --no-verify"'), {})

    def test_unsafe_jev_answers_do_not_become_instructions(self):
        marker = self.root / 'must-not-exist'
        self.mock.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"answers":{"test_failure":{"probability":True},"injected":{"probability":.99}},"text":"touch ' + str(marker) + '"}))\n')
        output = self.bash('make test', 'PostToolUse', tool_response={'exit_code':1})
        self.assertNotIn('Jev suggests', self.context(output))
        self.assertNotIn(str(marker), json.dumps(output))
        self.assertFalse(marker.exists())

    def test_jev_failure_is_advisory_and_bad_probabilities_ignored(self):
        self.mock.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"answers":{"test_failure":{"probability":.98},"transient_failure":{"probability":"yes"}}}))\n')
        output = self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1, 'output': 'AssertionError'})
        self.assertIn('Jev', self.context(output))
        self.assertIn('confirm', self.context(output))
        self.assertNotIn('transient', self.context(output))

    def test_stop_shadow_is_bounded_and_machine_output_is_exempt(self):
        self.bash('git push origin feature', 'PostToolUse', tool_response={'exit_code': 0})
        output = self.invoke('Stop', last_assistant_message='Done.')
        self.assertIn('systemMessage', output)
        self.assertIn('CI', output['systemMessage'])
        self.assertNotIn('decision', output)
        self.assertEqual(self.invoke('Stop', last_assistant_message='Done.'), {})
        self.assertEqual(self.invoke('Stop', turn_id='turn-2', last_assistant_message='{"ok":true}'), {})
        self.assertEqual(self.invoke('Stop', turn_id='turn-3', stop_hook_active=True, last_assistant_message='Done.'), {})

    def test_concurrent_updates_do_not_lose_failure_counts(self):
        def invoke(number):
            return self.bash('make test', 'PostToolUse', tool_response={'exit_code': 1}, tool_use_id=str(number))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outputs = list(pool.map(invoke, range(8)))
        counts = [int(self.context(output).split('failure ')[1].split(':')[0]) for output in outputs]
        self.assertEqual(sorted(counts), list(range(1, 9)))

    def test_untrusted_payload_is_data_and_invalid_event_reports_failure(self):
        marker = self.root / 'must-not-exist'
        output = self.invoke('SessionStart', session_id='../../outside', source='startup', cwd='$(touch ' + str(marker) + ')')
        self.assertFalse(marker.exists())
        self.assertNotIn('permissionDecision', json.dumps(output))
        result = subprocess.run(['python3', str(SCRIPT)], input='{"hook_event_name": []}',
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('invalid', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_state_symlink_is_refused_without_touching_target(self):
        target = self.root / 'foreign'
        target.mkdir()
        home = Path(self.env['CODEX_HOME'])
        home.mkdir()
        (home / '.codex-config-hook-state').symlink_to(target, target_is_directory=True)
        result = subprocess.run(['python3', str(SCRIPT)], input=json.dumps({
            'hook_event_name':'PostCompact','session_id':'session-1','cwd':str(self.cwd)}),
            env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
