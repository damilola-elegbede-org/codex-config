---
name: "watch"
description: "Read, transcribe, summarize, or research a video from captions and optional frames. Use for a video URL or local recording; transcript-only is the default."
license: "MIT. LICENSE has complete terms"
metadata: {"source-repository": "damilola-elegbede-org/claude-config", "source-commit": "cb257acb72ef568efc5d9dc2c25c365b179383b0", "source-path": "system-configs/.claude/skills/watch/SKILL.md"}
---

# watch

Read guide.md for options and dependencies. Resolve watch.py next to this SKILL.md and inspect --help. Default to --no-whisper transcript-only when available captions answer the request. Add --with-frames only when the visual layer matters, then inspect frames in order with the available image tool. Reuse existing transcripts in the session and cite timestamps. Missing yt-dlp/ffmpeg is a dependency to report, not authorization for installation. Audio transcription through Groq/OpenAI requires an explicit requested/configured workflow; never expose keys or silently upload a private recording. Use existing authorized credentials without copying them into the repo.

Follow the host’s instructions and current authorization. Tool names, delegation, models, sandboxing, and question availability come from the running Codex session; this skill does not override them. Resolve helpers from this SKILL.md’s actual directory (SKILL_DIR in examples is a variable you set, not a Codex substitution).
