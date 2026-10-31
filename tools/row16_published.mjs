// Row 16 against the broker's published charge formula.
//
//     node tools/row16_published.mjs          # offline: fixture vs the Lean model
//     node tools/row16_published.mjs --live   # also: the served verify.js still has it
//
// proofs/16_failed_calls.lean bills max(minSats, ceil(msat / 1000)) where
// msat = (input + hiddenIn) * inMsat + (delivered + hiddenOut) * outMsat.
// The broker's rates are sats per 1k tokens, which is millisats per token, so
// with no discount and no web-search fee the two must agree exactly. This runs
// the published JavaScript itself (not a port) on seeded random cases and on
// the theorems' own shapes. Discounts and web-search fees are not modelled in
// Lean and are held at zero here.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FIXTURE = path.join(ROOT, 'tests', 'fixtures', 'inference-verify-formula.js');
const LIVE_URL = 'https://inference.bsvkey.com/js/verify.js';

function extract(src) {
  const start = src.indexOf('function computeChargeSats(r) {');
  if (start < 0) throw new Error('computeChargeSats not found');
  const end = src.indexOf('\n}', start);
  if (end < 0) throw new Error('end of computeChargeSats not found');
  return src.slice(start, end + 2).replace(/\r\n/g, '\n');
}

const fn = extract(fs.readFileSync(FIXTURE, 'utf8'));
const computeChargeSats = new Function(`${fn}\nreturn computeChargeSats;`)();

// The Lean definition, in integers.
const lean = (u) => Math.max(u.minSats, Math.floor(((u.input + u.hiddenIn) * u.inMsat + (u.delivered + u.hiddenOut) * u.outMsat + 999) / 1000));
const code = (u) => computeChargeSats({
  inputTokens: u.input, outputTokens: u.delivered, hiddenInputTokens: u.hiddenIn, hiddenOutputTokens: u.hiddenOut,
  rateInPer1k: u.inMsat, rateOutPer1k: u.outMsat, webSearchSats: 0, discountPct: 0, minChargeSats: u.minSats,
});

let s = 16;
const pick = (n) => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s % n; };
const usage = () => ({
  input: pick(200_000), delivered: pick(50_000), hiddenIn: pick(5_000), hiddenOut: pick(20_000),
  inMsat: pick(30_000), outMsat: pick(150_000), minSats: pick(5),
});

const failures = [];
const check = (name, ok, detail) => { if (!ok) failures.push(`${name}: ${JSON.stringify(detail)}`); };
const N = 5000;
for (let i = 0; i < N; i++) {
  const u = usage();
  check('equals Lean tokenCharge', code(u) === lean(u), u);
  check('charged_at_least_min', code(u) >= u.minSats, u);
  const msat = (u.input + u.hiddenIn) * u.inMsat + (u.delivered + u.hiddenOut) * u.outMsat;
  check('charge_covers_cost', 1000 * code(u) >= msat, u);
  const cut = { ...u, delivered: pick(u.delivered + 1), hiddenIn: pick(u.hiddenIn + 1), hiddenOut: pick(u.hiddenOut + 1) };
  check('cut_short_le_finished', code(cut) <= code(u), { cut, u });
  check('charge_le_delivered_plus_allowance', code(u) <= code({ ...u, hiddenOut: u.hiddenOut + pick(10_000) }), u);
}
for (const minSats of [0, 1, 3]) {
  const z = { input: 0, delivered: 0, hiddenIn: 0, hiddenOut: 0, inMsat: 900, outMsat: 4500, minSats };
  check('zero_tokens_cost_min', code(z) === minSats, z);
}

if (process.argv.includes('--live')) {
  const res = await fetch(LIVE_URL);
  if (!res.ok) failures.push(`live: ${LIVE_URL} returned ${res.status}`);
  else check('live verify.js matches the fixture', extract(await res.text()) === fn, LIVE_URL);
}

if (failures.length) {
  console.log(failures.slice(0, 10).join('\n'));
  console.log(`FAIL: ${failures.length} checks failed`);
  process.exitCode = 1;
} else console.log(`PASS: published computeChargeSats matches row 16 on ${N} random cases and the zero-token cases` +
  (process.argv.includes('--live') ? `; ${LIVE_URL} still serves the same function` : ''));
