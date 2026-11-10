#!/usr/bin/env node
// Adapted from claude-config e1c3210b3938d4ac0a6452baf85b9089e9267371.
// Direct, bounded Codex Jev client. No daemon, Claude state, or auth mutation.
// stdin: {rule,state,questions,untrusted?,untrusted_source?,cwd?,paths?,timeout_ms?}
// stdout: {answers,model,latency_ms,cost_usd}; exit 0 success, 3 unavailable, 2 invalid input.
// JEV_MOCK/JEV_BACKEND_FIXTURE are offline test boundaries; exclusions still apply.
// JEV_RECORD writes redacted bounded request data only when explicitly set for debugging.
// JEV_STATE_DIR, JEV_CONFIG, JEV_RULES, JEV_DEPENDENCIES_DIR support isolated installations.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const T_START = Date.now() - Math.round(process.uptime() * 1000);

const EXIT_OK = 0;
const EXIT_BAD_INPUT = 2;
const EXIT_UNAVAILABLE = 3;

class JevError extends Error {
  constructor(exit, reason) {
    super(reason);
    this.exit = exit;
    this.reason = reason;
  }
}
const unavailable = (reason) => new JevError(EXIT_UNAVAILABLE, reason);
const badInput = (reason) => new JevError(EXIT_BAD_INPUT, reason);

// ---------------------------------------------------------------- paths/config

const home = () => process.env.HOME || os.homedir();
const codexHome = () => process.env.CODEX_HOME || path.join(home(), ".codex");
const stateDir = () => process.env.JEV_STATE_DIR || codexHome();
// The kill switch is a REGULAR FILE (not a directory or symlink): `mkdir ~/.codex/jev.off` must not disable Jev.
const killSwitchOn = () => {
  try {
    return fs.lstatSync(path.join(stateDir(), "jev.off")).isFile();
  } catch {
    return false;
  }
};

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}
const CONFIG_FILE = () => process.env.JEV_CONFIG || path.join(HERE, "jev-config.json");
const CONFIG_INVALID = Symbol("config_invalid");
// Missing or unreadable configuration refuses requests: exclusions cannot be honored.
const config = () => {
  if (!fs.existsSync(CONFIG_FILE())) return { [CONFIG_INVALID]: true };
  const c = readJson(CONFIG_FILE(), CONFIG_INVALID);
  if (!c || typeof c !== "object" || Array.isArray(c)
      || !Array.isArray(c.exclude_paths) || !c.exclude_paths.every((p) => typeof p === "string")
      || typeof c.model !== "string" || !c.model.trim()
      || !Number.isInteger(c.default_timeout_ms) || c.default_timeout_ms < 50 || c.default_timeout_ms > 60000
      || !Number.isInteger(c.max_state_tokens) || c.max_state_tokens < 250 || c.max_state_tokens > 28000) {
    return { [CONFIG_INVALID]: true };
  }
  return c;
};
const configInvalid = () => Boolean(config()[CONFIG_INVALID]);

// Only this Codex client's rules are loaded. A JEV_RULES override is a complete registry.
function rulesRegistry() {
  const file = process.env.JEV_RULES_FILE || process.env.JEV_RULES || path.join(HERE, "jev-rules.json");
  const raw = readJson(file, {});
  const rules = raw?.rules;
  return { rules: rules && typeof rules === "object" && !Array.isArray(rules) ? rules : {} };
}
function flatRegistry() { return rulesRegistry().rules; }

// ------------------------------------------------------------------------- key

const KEY_ENV = ["AI_GATEWAY_API_KEY", "VERCEL_AI_GATEWAY_TOKEN", "VERCEL_AI_GATEWAY_KEY"];

function resolveKey() {
  for (const n of KEY_ENV) {
    const v = process.env[n];
    if (v && v.trim()) return v.trim();
  }
  let txt;
  try {
    txt = fs.readFileSync(process.env.JEV_ZSHRC || path.join(home(), ".zshrc"), "utf8");
  } catch {
    return null;
  }
  const re = /^[ \t]*export[ \t]+(?:VERCEL_AI_GATEWAY_TOKEN|VERCEL_AI_GATEWAY_KEY|AI_GATEWAY_API_KEY)=(.*)$/gm;
  let raw = null;
  for (const m of txt.matchAll(re)) raw = m[1];
  if (raw === null) return null;
  raw = raw.trim();
  let val;
  const q = raw[0];
  if (q === '"' || q === "'") {
    const end = raw.indexOf(q, 1);
    val = end === -1 ? "" : raw.slice(1, end);
  } else {
    val = raw.split(/[\s#]/)[0];
  }
  // Anything needing shell evaluation ($(...), $VAR, backticks) is not supported.
  if (!val || /[$`]/.test(val)) return null;
  return val;
}

function sdkEntry() {
  const hash = crypto.createHash("sha256").update(fs.readFileSync(path.join(HERE, "package-lock.json"))).digest("hex");
  const dir = process.env.JEV_DEPENDENCIES_DIR || path.join(codexHome(), ".codex-config-deps", "jev", hash);
  return createRequire(path.join(dir, "package.json")).resolve("ai");
}
const sdkInstalled = () => { try { sdkEntry(); return true; } catch { return false; } };

// ------------------------------------------------------------------- redaction

// Redact common credential formats before any provider call.
const SECRET_PATTERNS = [
  /AKIA[0-9A-Z]{16}/g,
  /sk-[a-zA-Z0-9]{20,}/g,
  /ghp_[a-zA-Z0-9]{36}/g,
  /gho_[a-zA-Z0-9]{36}/g,
  /xoxb-[0-9]{10,}[A-Za-z0-9-]*/g,
  /xoxp-[0-9]{10,}[A-Za-z0-9-]*/g,
  /glpat-[a-zA-Z0-9_-]{20}/g,
  /sk-ant-[A-Za-z0-9_-]{20,}/g,
  /github_pat_[A-Za-z0-9_]{20,}/g,
  /gh[usr]_[A-Za-z0-9]{36}/g,
  /xox[abprs]-[A-Za-z0-9-]{10,}/g,
  /vck_[A-Za-z0-9]{20,}/g,
  /npm_[A-Za-z0-9]{30,}/g,
  /AIza[0-9A-Za-z_-]{35}/g,
  /[sr]k_live_[A-Za-z0-9]{16,}/g,
  /whsec_[A-Za-z0-9]{16,}/g,
  /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g,
  /\bBearer[ \t]+[A-Za-z0-9._~+/=-]{16,}/gi,
];
// scheme://user:pass@host -> scheme://[REDACTED]@host
const URL_CREDS = /\b([a-z][a-z0-9+.-]*:\/\/)[^\s:@/]+:[^\s@/]+@/gi;
// The assignment redaction pattern is built from credential-name words (see CRED_WORDS) so no
// source line spells out a quoted NAME=value assignment.
const CRED_WORDS = [
  "token",
  "secret",
  "passw(?:or)?d",
  "passwd",
  "api[_-]?key",
  "private[_-]?key",
  "credentials?",
  "access[_-]?key",
].join("|");
const patternAssignment = new RegExp(
  `\\b([A-Za-z0-9_.-]*(?:${CRED_WORDS})[A-Za-z0-9_.-]*)([ \\t]*[=:][ \\t]*)("[^"\\n]*"|'[^'\\n]*'|[^\\s"',;]+)`,
  "gi",
);
const SENSITIVE_KEY =
  /^(?:.*[-_.])?(?:token|secret|password|passwd|pwd|api[-_]?key|apikey|authorization|auth|cookie|credentials?|private[-_]?key|access[-_]?key)s?$/i;
const TOKEN_CANDIDATE = /[A-Za-z0-9_\-+/=]{24,}/g;
const REDACTED = "[REDACTED]";

function entropy(s) {
  const f = new Map();
  for (const c of s) f.set(c, (f.get(c) || 0) + 1);
  let h = 0;
  for (const n of f.values()) {
    const p = n / s.length;
    h -= p * Math.log2(p);
  }
  return h;
}

function looksLikeSecret(t) {
  if (t.startsWith("/") || t.startsWith("./") || t.startsWith("../")) return false; // a path
  const hex = /^[0-9a-fA-F]+$/.test(t);
  if (hex) return t.length >= 32 && entropy(t) >= 3.0; // also catches 40-hex git SHAs: over-redaction is fine
  if (!(/[A-Z]/.test(t) && /[a-z]/.test(t) && /\d/.test(t))) return false;
  return entropy(t) >= (t.includes("/") ? 4.2 : 3.5);
}

function redactString(s, stats) {
  let out = s;
  const sub = (re, rep) => {
    out = out.replace(re, (...a) => {
      stats.count++;
      return typeof rep === "function" ? rep(...a) : rep;
    });
  };
  for (const re of SECRET_PATTERNS) sub(re, REDACTED);
  sub(URL_CREDS, (_m, scheme) => `${scheme}${REDACTED}@`);
  sub(patternAssignment, (m, name, sep, val) => (val === REDACTED || val.includes(REDACTED) ? m : `${name}${sep}${REDACTED}`));
  out = out.replace(TOKEN_CANDIDATE, (t) => {
    if (!looksLikeSecret(t)) return t;
    stats.count++;
    return REDACTED;
  });
  return out;
}

function redactValue(v, stats, depth = 0) {
  if (depth > 40) return REDACTED;
  if (typeof v === "string") return redactString(v, stats);
  if (Array.isArray(v)) return v.map((x) => redactValue(x, stats, depth + 1));
  if (v && typeof v === "object") {
    const o = {};
    for (const [k, x] of Object.entries(v)) {
      if (SENSITIVE_KEY.test(k) && (typeof x === "string" || typeof x === "number")) {
        stats.count++;
        o[k] = REDACTED;
      } else {
        o[k] = redactValue(x, stats, depth + 1);
      }
    }
    return o;
  }
  return v;
}

// ------------------------------------------------------------------ truncation

function collectStrings(v, out, parent = null, key = null) {
  if (typeof v === "string") out.push({ parent, key, len: v.length });
  else if (Array.isArray(v)) v.forEach((x, i) => collectStrings(x, out, v, i));
  else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) collectStrings(x, out, v, k);
}

// Shrink the longest string leaves (head 60% + tail 40%) until JSON size <= budget chars.
function truncateToBudget(obj, budgetChars) {
  let size = JSON.stringify(obj).length;
  if (size <= budgetChars) return { value: obj, truncated: false };
  for (let i = 0; i < 400 && size > budgetChars; i++) {
    const leaves = [];
    collectStrings(obj, leaves);
    leaves.sort((a, b) => b.len - a.len);
    const big = leaves[0];
    if (!big) break;
    const excess = size - budgetChars;
    const marker = (n) => `\n...[truncated ${n} chars]...\n`;
    const keep = Math.max(200, big.len - excess - 64);
    if (keep >= big.len) break;
    const s = big.parent[big.key];
    const head = Math.ceil(keep * 0.6);
    const tail = keep - head;
    big.parent[big.key] = s.slice(0, head) + marker(s.length - keep) + (tail > 0 ? s.slice(-tail) : "");
    size = JSON.stringify(obj).length;
  }
  if (size > budgetChars) {
    // Many small leaves: fall back to a cut of the serialised form.
    const cut = JSON.stringify(obj).slice(0, Math.max(0, budgetChars - 40));
    return { value: { _truncated_json: cut }, truncated: true };
  }
  return { value: obj, truncated: true };
}

// ---------------------------------------------------------------------- egress

// exclude_paths entries are directory prefixes,
// anchored at "/" or at $HOME ("~/work"; a bare "work" means "~/work"), matched case-insensitively on a
// path-segment boundary against the raw and the realpath form of the cwd. A trailing "/", "/*" or "/**" is
// ignored. A substring such as "/work/" no longer matches an unrelated checkout like /home/runner/work/x.
function excludedPrefixes() {
  const out = new Set();
  const homes = new Set([home()]);
  try {
    homes.add(fs.realpathSync(home()));
  } catch {
    /* home not on disk */
  }
  for (const raw of (config().exclude_paths || []).filter((p) => typeof p === "string" && p.trim())) {
    const e = raw.trim().replace(/(?:\/\*{0,2})+$/, "");
    if (!e) continue;
    const rel = e.startsWith("~") ? e.replace(/^~\/?/, "") : e.startsWith("/") ? null : e;
    const abs = rel === null ? [e] : [...homes].map((h) => (rel ? path.join(h, rel) : h));
    for (const a of abs) {
      out.add(a.toLowerCase());
      try {
        out.add(fs.realpathSync(a).toLowerCase()); // a prefix given through a symlink (e.g. /var -> /private/var)
      } catch {
        /* not on disk: raw only */
      }
    }
  }
  return out;
}

// External message text is not authorized for Jev by this integration.
export function egressReason(input) {
  // The caller may flag the source at top level or inside state; honor both.
  const srcs = [input.untrusted_source, input.state?.untrusted_source].flatMap((v) =>
    Array.isArray(v) ? v : typeof v === "string" ? [v] : [],
  );
  // Normalize to individual tags ("gmail,slack" -> gmail + slack) so each one needs its own authorization.
  const blocked = [...new Set(srcs.flatMap((s) => String(s).toLowerCase().match(/gmail|slack/g) || []))];
  if (blocked.length) return "egress_untrusted_source";
  if (configInvalid()) return "egress_config_unreadable"; // fail closed: the exclusion list is unknown
  const cwds = new Set();
  for (const c of [input.cwd, process.cwd()]) {
    if (typeof c !== "string" || !c) continue;
    cwds.add(c);
    try {
      cwds.add(fs.realpathSync(c));
    } catch {
      /* not on disk: raw only */
    }
  }
  // Paths the request is about (a Write/Edit target): relative ones resolve against the caller's cwd, and a
  // file that does not exist yet is canonicalized through its parent directory.
  const base = typeof input.cwd === "string" && input.cwd ? input.cwd : process.cwd();
  for (const p of Array.isArray(input.paths) ? input.paths : []) {
    if (typeof p !== "string" || !p) continue;
    const abs = path.resolve(base, p.startsWith("~/") ? path.join(home(), p.slice(2)) : p);
    cwds.add(abs);
    try { cwds.add(fs.realpathSync(abs)); } catch { /* new target */ }
    try {
      cwds.add(path.join(fs.realpathSync(path.dirname(abs)), path.basename(abs)));
    } catch {
      /* parent not on disk: raw only */
    }
  }
  for (const q of excludedPrefixes()) {
    for (const c of cwds) {
      const lc = c.toLowerCase();
      if (lc === q || lc.startsWith(q + "/")) return "egress_excluded_path";
    }
  }
  return null;
}

// -------------------------------------------------------------- validation/IO

function validate(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw badInput("stdin must be a JSON object");
  if (typeof input.rule !== "string" || !/^[\w.:/-]{1,80}$/.test(input.rule)) throw badInput("rule: required id string");
  const st = input.state;
  if (!st || typeof st !== "object" || Array.isArray(st)) throw badInput("state: required object");
  if ("untrusted" in st) throw badInput("state must not contain an 'untrusted' key; use the top-level untrusted field");
  const qs = input.questions;
  if (!qs || typeof qs !== "object" || Array.isArray(qs) || !Object.keys(qs).length) throw badInput("questions: required non-empty object");
  for (const [name, q] of Object.entries(qs)) {
    if (!q || typeof q !== "object") throw badInput(`questions.${name}: object required`);
    if (!["boolean", "choice", "score"].includes(q.type)) throw badInput(`questions.${name}.type: boolean|choice|score`);
    if (typeof q.instructions !== "string" || !q.instructions) throw badInput(`questions.${name}.instructions: string required`);
    if (q.type === "choice" && (!q.criteria || typeof q.criteria !== "object" || Array.isArray(q.criteria) || !Object.keys(q.criteria).length))
      throw badInput(`questions.${name}.criteria: object of options required for choice`);
    if (q.type === "score" && (!Array.isArray(q.criteria) || !q.criteria.length)) throw badInput(`questions.${name}.criteria: array required for score`);
  }
  if (input.timeout_ms !== undefined && !(Number.isFinite(input.timeout_ms) && input.timeout_ms >= 50 && input.timeout_ms <= 60000))
    throw badInput("timeout_ms: number 50..60000");
  if (input.paths !== undefined && !(Array.isArray(input.paths) && input.paths.length <= 50 && input.paths.every((p) => typeof p === "string")))
    throw badInput("paths: array of up to 50 strings");
  if (input.untrusted !== undefined && input.untrusted !== null && typeof input.untrusted !== "object" && typeof input.untrusted !== "string")
    throw badInput("untrusted: object or string");
}

function readStdin(cap = 16 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let n = 0;
    process.stdin.on("data", (c) => {
      n += c.length;
      if (n > cap) reject(badInput("stdin too large"));
      else chunks.push(c);
    });
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    process.stdin.on("error", reject);
  });
}

// Logs are optional metadata only. Refuse symlinked files/directories and stop
// at the size bound rather than mutating a questionable destination.
const LOG_MAX_BYTES = Number(process.env.JEV_LOG_MAX_BYTES) > 0 ? Number(process.env.JEV_LOG_MAX_BYTES) : 10 * 1024 * 1024;
function appendLog(dir, name, line) {
  const absolute = path.resolve(dir);
  let parent = path.parse(absolute).root;
  for (const part of absolute.slice(parent.length).split(path.sep).filter(Boolean)) {
    parent = path.join(parent, part);
    try { fs.mkdirSync(parent, { mode: 0o700 }); } catch (e) { if (e.code !== "EEXIST") throw e; }
    const entry = fs.lstatSync(parent);
    if (!entry.isDirectory() || entry.isSymbolicLink()) return;
  }
  let fd;
  try {
    fd = fs.openSync(path.join(absolute, `${name}.jsonl`), fs.constants.O_WRONLY | fs.constants.O_APPEND | fs.constants.O_CREAT | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK, 0o600);
    const entry = fs.fstatSync(fd);
    if (!entry.isFile() || entry.nlink !== 1 || (process.getuid && entry.uid !== process.getuid()) || entry.size > LOG_MAX_BYTES) return;
    fs.fchmodSync(fd, 0o600);
    fs.writeSync(fd, line + "\n");
  } finally { if (fd !== undefined) fs.closeSync(fd); }
}

// The probability the first question's answer carries (boolean: probability; choice: that of the chosen
// option); null for score answers or no answer. Shown as `confidence` in decisions.jsonl.
function confidenceOf(answers) {
  const first = answers && typeof answers === "object" ? Object.values(answers)[0] : null;
  if (!first || typeof first !== "object") return null;
  if (typeof first.probability === "number") return first.probability;
  if (first.probabilities && typeof first.probabilities === "object" && first.choice in first.probabilities) return first.probabilities[first.choice];
  return null;
}

// Store only counts and fixed status metadata, never answer values, raw provider
// errors, file paths, prompts, source text, or arbitrary provider model strings.
function shadowLog(entry) {
  const number = (value) => Number.isFinite(value) && value >= 0 ? value : null;
  try {
    appendLog(path.join(stateDir(), "jev"), "decisions", JSON.stringify({
      ts: new Date().toISOString(),
      gate: entry.rule,
      mode: ["shadow", "enforce", "off"].includes(entry.mode) ? entry.mode : null,
      outcome: entry.outcome === "ok" ? "ok" : "unavailable",
      source: entry.source === "mock" ? "mock" : "direct",
      answers_count: entry.answers && typeof entry.answers === "object" ? Object.keys(entry.answers).length : 0,
      confidence: number(confidenceOf(entry.answers)),
      latency_ms: number(entry.latency_ms),
      cost_usd: number(entry.cost_usd),
      wall_ms: number(entry.wall_ms),
      redactions: number(entry.redactions),
      truncated: entry.truncated === true,
    }));
  } catch { /* logging must never fail a request */ }
}

function normalizedResult(out, questions, model) {
  if (!out || typeof out !== "object" || !out.answers || typeof out.answers !== "object" || Array.isArray(out.answers)) throw unavailable("invalid_answer");
  const probability = (n) => typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 1;
  const answers = {};
  for (const [name, question] of Object.entries(questions)) {
    const answer = out.answers[name];
    if (!answer || typeof answer !== "object" || Array.isArray(answer)) throw unavailable("invalid_answer");
    if (question.type === "boolean") {
      if (!probability(answer.probability)) throw unavailable("invalid_answer");
      answers[name] = { type: "boolean", probability: answer.probability };
    } else if (question.type === "choice") {
      if (typeof answer.choice !== "string" || !Object.hasOwn(question.criteria, answer.choice)) throw unavailable("invalid_answer");
      const probabilities = {};
      for (const option of Object.keys(question.criteria)) {
        const n = answer.probabilities?.[option];
        if (n !== undefined) {
          if (!probability(n)) throw unavailable("invalid_answer");
          probabilities[option] = n;
        }
      }
      if (!probability(probabilities[answer.choice])) throw unavailable("invalid_answer");
      answers[name] = { type: "choice", choice: answer.choice, probabilities };
    } else {
      if (typeof answer.score !== "number" || !Number.isFinite(answer.score) || answer.score < 0 || answer.score > question.criteria.length - 1) throw unavailable("invalid_answer");
      answers[name] = { type: "score", score: answer.score };
    }
  }
  const number = (n) => Number.isFinite(n) && n >= 0 ? n : 0;
  return { answers, model, latency_ms: number(out.latency_ms), cost_usd: number(out.cost_usd) };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// -------------------------------------------------------------------- backend

// Provider boundary. Throws JevError(unavailable).
async function callGateway({ model, state, questions, timeout_ms }) {
  const t0 = Date.now();
  if (process.env.JEV_BACKEND_FIXTURE) {
    const delay = Number(process.env.JEV_BACKEND_DELAY_MS || 0);
    if (delay) await sleep(delay);
    const j = readJson(process.env.JEV_BACKEND_FIXTURE, null);
    if (!j || !j.answers) throw unavailable("backend_fixture_unreadable");
    return { answers: j.answers, model: j.model || model, latency_ms: j.latency_ms ?? Date.now() - t0, cost_usd: j.cost_usd ?? 0 };
  }
  const key = resolveKey();
  if (!key) throw unavailable("no_key");
  process.env.AI_GATEWAY_API_KEY = key;
  let mod;
  try {
    mod = await import(sdkEntry());
  } catch {
    throw unavailable("sdk_missing");
  }
  let res;
  try {
    res = await mod.experimental_evaluate({
      model,
      state,
      questions,
      providerOptions: { gateway: { zeroDataRetention: true } },
      abortSignal: AbortSignal.timeout(Math.max(50, timeout_ms)),
    });
  } catch (e) {
    throw unavailable("gateway_error");
  }
  const gw = res?.providerMetadata?.gateway || {};
  const cost = Number.parseFloat(gw.marketCost ?? gw.cost ?? "0");
  return { answers: res.answers, model, latency_ms: Date.now() - t0, cost_usd: Number.isFinite(cost) ? cost : 0 };
}

// ------------------------------------------------------------------------ CLI

function finish(code, stdout) {
  if (stdout) process.stdout.write(stdout, () => process.exit(code));
  else process.exit(code);
}

async function ask() {
  let input;
  try {
    const raw = await readStdin();
    try {
      input = JSON.parse(raw);
    } catch {
      throw badInput("stdin is not valid JSON");
    }
    validate(input);
  } catch (e) {
    if (e instanceof JevError) {
      process.stderr.write(`jev-ask: bad input: ${e.reason}\n`);
      return finish(e.exit);
    }
    throw e;
  }

  const cfg = config();
  const mock = process.env.JEV_MOCK || "";
  const model = cfg.model || "typesafe-ai/jev";
  const cwd = typeof input.cwd === "string" && input.cwd ? input.cwd : process.cwd();
  const thisRule = rulesRegistry().rules[input.rule];
  const meta = { rule: input.rule, cwd, model: mock ? "mock" : model, mode: thisRule?.mode };
  const t0 = T_START;
  const fail = (reason) => {
    shadowLog({ ...meta, outcome: "unavailable", reason, wall_ms: Date.now() - t0 });
    process.stderr.write(`jev-ask: unavailable: ${reason.split(":")[0]}\n`);
    return finish(EXIT_UNAVAILABLE);
  };

  if (mock === "unavailable") return fail("mock_unavailable");
  if (killSwitchOn()) return fail("kill_switch");
  if (!thisRule || !["shadow", "enforce"].includes(thisRule.mode)) return fail("rule_off_or_unknown");
  const why = egressReason(input);
  if (why) return fail(why);

  // Redact, then truncate. Untrusted text stays under its own key.
  const stats = { count: 0 };
  const questions = input.questions;
  let payload = redactValue(input.state, stats);
  if (input.untrusted !== undefined && input.untrusted !== null) payload = { ...payload, untrusted: redactValue(input.untrusted, stats) };
  const budget = Math.max(1000, Math.floor((cfg.max_state_tokens || 28000) * 4) - JSON.stringify(questions).length);
  const tr = truncateToBudget(payload, budget);
  payload = tr.value;
  Object.assign(meta, { redactions: stats.count, truncated: tr.truncated });

  if (process.env.JEV_RECORD) {
    try {
      fs.writeFileSync(
        process.env.JEV_RECORD,
        JSON.stringify({ rule: input.rule, model: meta.model, state: payload, questions, truncated: tr.truncated, redactions: stats.count }, null, 2),
        { mode: 0o600 },
      );
    } catch {
      /* debug aid only */
    }
  }

  if (mock) {
    try {
      const result = normalizedResult(readJson(mock, null), questions, "mock");
      shadowLog({ ...meta, ...result, outcome: "ok", source: "mock", wall_ms: Date.now() - t0 });
      return finish(EXIT_OK, JSON.stringify(result) + "\n");
    } catch { return fail("invalid_answer"); }
  }

  if (!process.env.JEV_BACKEND_FIXTURE && !resolveKey()) return fail("no_key");

  const timeout = input.timeout_ms ?? cfg.default_timeout_ms ?? 1000;
  const deadline = t0 + timeout;
  const req = { model, state: payload, questions };
  let out = null;
  const source = "direct";
  try {
    if (!out) {
      const left = deadline - Date.now();
      if (left <= 0) return fail("timeout");
      out = await Promise.race([
        callGateway({ ...req, timeout_ms: left }),
        sleep(left).then(() => {
          throw unavailable("timeout");
        }),
      ]);
    }
  } catch (e) {
    return fail(e instanceof JevError ? e.reason : `error:${e?.name}`);
  }
  let result;
  try { result = normalizedResult(out, questions, model); } catch { return fail("invalid_answer"); }
  shadowLog({ ...meta, outcome: "ok", source, answers: result.answers, latency_ms: result.latency_ms, cost_usd: result.cost_usd, wall_ms: Date.now() - t0 });
  return finish(EXIT_OK, JSON.stringify(result) + "\n");
}

async function main() {
  const flag = process.argv[2];
  if (flag === "--registry") return finish(EXIT_OK, JSON.stringify(flatRegistry()) + "\n"); // local registry, no provider call
  if (flag === "--check") {
    // Local prerequisites only; this is not a gateway health check.
    let reason = null;
    if (configInvalid()) reason = "egress_config_unreadable";
    else if (killSwitchOn()) reason = "kill_switch";
    else if (!process.env.JEV_MOCK && !process.env.JEV_BACKEND_FIXTURE && !resolveKey()) reason = "no_key";
    else if (!process.env.JEV_MOCK && !process.env.JEV_BACKEND_FIXTURE && !sdkInstalled()) reason = "no_sdk";
    return finish(reason ? EXIT_UNAVAILABLE : EXIT_OK, reason ? reason + "\n" : "");
  }
  if (flag) {
    process.stderr.write("jev-ask: usage: jev-ask [--check|--registry]\n");
    return finish(EXIT_BAD_INPUT);
  }
  return ask();
}

// Run only as the entry point, so tests can import the pure helpers without starting the CLI.
const isEntry = (() => {
  try {
    return !!process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();
if (isEntry) {
  main().catch((e) => {
    process.stderr.write(`jev-ask: unavailable: internal:${e?.name || "Error"}\n`);
    process.exit(EXIT_UNAVAILABLE);
  });
}
