# bsvkey-axiom-proofs

> **Axiom integration test.** This repo tests [AXLE](https://axle.axiommath.ai/), the
> Axiom Lean Engine from Axiom Math, against BSVKey. It is an experiment, not a
> product, and not an endorsement by or partnership with Axiom.

> **Advisory (2026-10-28):** AXLE's `verify_proof` can be made to accept a
> proof of `False`. Details, reproduction and the fix: [ADVISORY.md](ADVISORY.md).
> Our 16 proofs are unaffected: none use metaprogramming, the guard refuses any file that does,
> and all 16 pass an [independent kernel replay](#independent-kernel-replay) with the official
> Lean 4.35.0 and Mathlib v4.35.0 ([CI run](https://github.com/BSVKey/bsvkey-axiom-proofs/actions/runs/40689665073)).

> **Check the receipts in your browser:** https://bsvkey.github.io/bsvkey-axiom-proofs/

> **No privacy.** Nothing in this repo is private, and AXLE gives no privacy:
> - Every proof file is sent **in plain text** to Axiom's cloud servers to be checked.
> - The receipts, Merkle root and OP_RETURN data are **public**, and so are the proof files.
> - There is no encryption, no zero-knowledge and no selective disclosure here.
>
> Do not put anything confidential, proprietary or export-controlled through this
> pipeline. If you need to prove something without revealing it, this is the wrong tool.

## What it does

Machine-checked proofs of the rules behind BSVKey products, plus a public
receipt for each check that can be anchored on Bitcoin BSV:

1. **Prove.** Each file in [`proofs/`](proofs) models one BSVKey rule in Lean 4
   (with Mathlib) and proves the property that matters, such as "the Governor can
   never overspend its cap".
2. **Check with AXLE.** [`tools/axle_verify.py`](tools/axle_verify.py) sends each file
   to AXLE. AXLE strips the proofs to get the bare statements, then checks the full
   file against them. A file passes only if every proof is complete: no `sorry`,
   no errors, no extra axioms.
3. **Receipt.** [`tools/proof_receipt.py`](tools/proof_receipt.py) turns each pass into
   a receipt (file hash, statement hash, theorem names, Lean version, time), puts
   all receipts under one Merkle root, and prints the OP_RETURN script for anchoring
   that root on Bitcoin BSV.
4. **Verify.** Anyone can re-hash a proof file, check its receipt reaches the
   root, and (with a txid) confirm the root is on-chain.

AXLE proves that **the logic holds**. The Bitcoin BSV anchor proves that
**this exact proof existed, unchanged, at that time**. Neither does the other's job.

## AXLE features (what Axiom provides)

From the `axiom-axle` client (v1.9.0) and Axiom's public docs:

| Feature | What it does | Used here |
|---|---|---|
| `verify_proof` | Checks a proof against a stated theorem; fails on `sorry`, errors or extra axioms | Yes, every file |
| `theorem2sorry` | Strips proofs to leave bare statements | Yes, to get each file's claims |
| `disprove` | Tries to prove a theorem's negation (finds counterexamples) | Yes, negative control |
| `check` | Compiles Lean code and returns all messages | No |
| `repair_proofs`, `simplify_theorems` | Fixes or shortens broken or long proofs | No |
| `extract_decls`, `extract_proof_states` | Splits files into declarations; shows proof state per line | No |
| `normalize`, `merge`, `rename`, `have2lemma`, `sorry2lemma` and others | Lean file tooling | No |
| Environments | Lean 4.21 to 4.35 with Mathlib, plus CSLib, Physlib, PrimeGapsLib | `lean-4.35.0` |
| Access | Python SDK, CLI, web UI, MCP server, HTTP API; no local Lean install needed | Python SDK |
| Cost | Free; anonymous use is rate-limited, a free API key raises limits | Anonymous |
| Privacy | **None.** Source code is sent to and processed on Axiom's servers | n/a |

AxiomProver, the AI that writes proofs (used for Axiom's Classification of Finite
Simple Groups formalization), is **not** publicly available and is not used here.
Every proof in this repo was written by hand and only *checked* by AXLE.

## The 16 BSVKey uses

All 16 files pass AXLE (64 theorems in total). Results are in [`results/`](results).

| # | BSVKey product | Proven property |
|---|---|---|
| 01 | Non-custodial payment channel | Balances are conserved through any sequence of payments and refunds; no side is overdrawn |
| 02 | Paywall Cloud pricing | Price never below the floor, always covers cost plus 3%, rounds up by under one satoshi, never falls when cost rises |
| 03 | Paywall charge-first refunds | Total refunded never exceeds the charge, whatever refund requests arrive |
| 04 | Governor AI spend firewall | Spend never passes the cap for any request stream; kill switch blocks everything |
| 05 | Inference Broker metering | Bill always covers token cost; monotone in tokens; zero tokens is free; splitting a job costs at most 1 sat more (token counts only: the live broker adds a minimum charge and handles failures, see row 16) |
| 06 | Fee rake (as in BSV Scribe) | Seller share plus fee equals the payment exactly; fee never exceeds the payment |
| 07 | Name Market trades | A trade is all or nothing; no name without payment, no payment without the name; money conserved |
| 08 | .key name registry | No name ever has two owners; a stranger cannot transfer someone else's name |
| 09 | Receipt hash chain | Same head means same history: any edited, removed or reordered receipt changes the anchored head |
| 10 | Merkle batch anchoring | One root fixes every leaf; every leaf has an inclusion path to the root |
| 11 | Wallet session idle lock | Idle for 900 s means locked; once locked, no amount of waiting or activity reopens it |
| 12 | DTN custody receipts | Valid custody chains have no gaps; the holder is the last receiver; chains splice cleanly |
| 13 | Paid DMs and Contact Gauge | Every delivered message was paid in full to the right address; revenue is at least price times count |
| 14 | Reserve receipts | Reserves still cover all balances after any deposits and withdrawals |
| 15 | x402 settlement | Nothing is served unless a node accepted the payment; a rejected request is never served |
| 16 | Inference Broker failed and partial calls | A provider error is never charged, even after tokens streamed; a timeout costs the same as a finished call with the same delivered tokens; cutting a call short never costs more than finishing it; the charge never exceeds delivered tokens plus the buyer's hidden-output allowance; every charged call costs at least the minimum (so zero tokens costs the minimum, not zero) |

Row 16 was added on 2026-10-30 after a reader asked whether a call that fails
partway is inside row 05's model. It was not: row 05 bills token counts and
says nothing about how a call ends, and it has no minimum charge. Row 16 models
both, matching the broker's code.

### Negative controls

[`negative/`](negative) holds files AXLE **must reject**, so a pass means something:

- `buggy_paywall_pricing.lean`: the price rule with the 3% margin rounded **down**.
  AXLE rejects it, and `disprove` finds the counterexample (a cost of 1 sat is underpriced).
- `sorry_governor.lean`: an unfinished proof. AXLE rejects it.

## Check a receipt in your browser

Live at https://bsvkey.github.io/bsvkey-axiom-proofs/ .
[`index.html`](index.html) checks any proof against its receipt and the
on-chain root with nothing installed: it hashes the file with Web Crypto,
rebuilds the receipt leaf, climbs the Merkle path and reads the transaction
from WhatsOnChain. "Check all 16" runs every file. You can also drop your own
copy of a `.lean` file on it to see whether it is the exact file AXLE checked.
Open it from a local copy of the repo with any static server, for example
`python -m http.server --directory .`

## Use AXLE in your own CI

This repo is also a GitHub Action. Add to any workflow:

```yaml
- uses: actions/checkout@v4
- uses: BSVKey/bsvkey-axiom-proofs@main
  with:
    path: proofs            # folder of .lean files, searched recursively
    # api-key: ${{ secrets.AXLE_API_KEY }}   # optional, raises rate limits
```

It checks every file with AXLE and writes a pass/fail table to the job page.
No Lean install, no Mathlib build. **No privacy:** the files are sent in plain
text to Axiom's servers, so only use it on code you would publish anyway.

## Plain-Lean guard

Before anything is sent, [`tools/lean_guard.py`](tools/lean_guard.py) refuses
files that use metaprogramming (`run_cmd`, `#eval`, `elab`, `macro`, `open Lean`),
`unsafe` code, `implemented_by`, extra axioms, `native_decide`, checker
options or imports other than Mathlib. Receipts are only for plain definitions
and theorems, the same rule many proof competitions use. It blocks the trick
in [ADVISORY.md](ADVISORY.md), and it runs in the Action too.

## Independent kernel replay

The `kernel` job in [CI](.github/workflows/test.yml) checks the 16 proofs
without AXLE, on every push, on GitHub's own runner:

1. [`tools/kernel_project.py`](tools/kernel_project.py) copies each file byte for
   byte into a Lake library ([`kernel/`](kernel)), for example
   `proofs/01_payment_channel.lean` to `kernel/Proofs/P01_payment_channel.lean`
   (Lean module names cannot start with a digit). The files in `proofs/` are not
   changed, so the anchored hashes still match.
2. [`leanprover/lean-action`](https://github.com/leanprover/lean-action) builds them
   with the official Lean 4.35.0 and Mathlib v4.35.0 (Mathlib's prebuilt cache).
3. `leanchecker` replays every compiled declaration in the 16 modules through
   Lean's kernel. Mathlib's own declarations are loaded as imports, not replayed.
4. `axiom-audit` and `#print axioms` confirm that each of the 64 theorems uses only
   `propext`, `Classical.choice` and `Quot.sound`. The job page shows a table.
5. The same replay is run on the exploit from [ADVISORY.md](ADVISORY.md) and must
   reject it, so the check is known to catch that trick.

**Result:** [all 15 files and 57 theorems pass](https://github.com/BSVKey/bsvkey-axiom-proofs/actions/runs/40689665073)
(run of 2026-10-28, commit `bf5251b`). Row 16 is replayed on every push since
2026-10-30: see the latest [`test` run](https://github.com/BSVKey/bsvkey-axiom-proofs/actions/workflows/test.yml).

To repeat it locally (PowerShell, Lean installed with elan):

```powershell
python tools\kernel_project.py
cd kernel
lake exe cache get
lake build
lake env leanchecker Proofs
cd ..
python tools\kernel_project.py --audit
```

## Soundness tests of AXLE

[`soundness/`](soundness) holds adversarial cases: files that try to make
`verify_proof` accept a false or unproven claim (hidden `sorry`, custom axioms,
`native_decide`, weaker or renamed statements, redefined definitions, instance,
notation and macro overrides of `+`, `#exit`, `opaque` and `unsafe` tricks,
and two metaprograms that add a theorem with the kernel check turned off),
plus honest controls that must pass.

**Result: 19 of 21 handled correctly. AXLE accepted both kernel-skipping
proofs of `False`.** See [ADVISORY.md](ADVISORY.md). Known cases print `KNOWN`
and turn into `FIXED` once AXLE rejects them; any new hole fails the run.
[`soundness/kernel-replay/`](soundness/kernel-replay) shows Lean's own
`leanchecker` rejecting the same file.

```powershell
python soundness\run_soundness.py
```

## What these proofs do and do not show

- Each file proves a property of a **model** of a BSVKey rule, written in Lean.
  It does **not** prove that the deployed code (JavaScript, TypeScript or Python)
  matches the model. That link is checked by each product's own tests, not here.
  For row 16, the Inference Broker's test suite runs its real charge formula and
  stream path through the same cases as the Lean model (provider error, timeout,
  cut short, allowance cap, minimum). That repo is private, so this is our
  statement, not something you can check here. What you can check: the broker
  publishes its charge formula in its receipt verifier
  (https://inference.bsvkey.com/js/verify.js), and
  [`tools/row16_published.mjs`](tools/row16_published.mjs) runs that published
  JavaScript against row 16's Lean definition on 5000 random cases (offline, on
  every push). With `--live` it also checks the served file still has the same
  function (weekly in CI). Discounts and web-search fees are held at zero.
- Files 09 and 10 treat the hash function as ideal (collision resistant). They do
  not prove anything about SHA-256 itself.
- An AXLE pass means AXLE reported the proof as checked on Axiom's servers. The
  [independent kernel replay](#independent-kernel-replay) re-checks every file with
  Lean's own kernel on GitHub's runner, and you can repeat it on your own machine.

## Run it

PowerShell, from the repo folder (Python 3.11 or later):

```powershell
python -m pip install -r requirements.txt
python tools\lean_guard.py proofs\01_payment_channel.lean
python tools\axle_verify.py
python tools\axle_negative.py
python tools\proof_receipt.py build
python tools\proof_receipt.py verify proofs\04_governor_spend_cap.lean
python -m unittest discover -s tests
```

`axle_verify.py` and `axle_negative.py` call Axiom's servers. The receipt tool and
the unit tests run offline. Set `AXLE_API_KEY` for higher rate limits.

## Anchoring on Bitcoin BSV

Current batch ([`receipts/batch.json`](receipts/batch.json), 16 receipts):

- Merkle root: `e4b67dc1db0a6c1a250380e68e29f8d0a0d5079f7e57a99db431d58636a3ed21`
- OP_RETURN script: `OP_FALSE OP_RETURN "bsvkey.proof" <root>`
- Anchored on Bitcoin BSV mainnet in transaction
  [`116140e0ed3c1d2b0a46825128d88a032003bed08ad3fc3d8147c340c825b2cf`](https://whatsonchain.com/tx/116140e0ed3c1d2b0a46825128d88a032003bed08ad3fc3d8147c340c825b2cf)
  (broadcast 2026-10-30, one input, 25 sat fee). Its input is the change output
  of the first anchor, so the two anchors are linked on chain.

First batch ([`receipts/batch-2026-10-28.json`](receipts/batch-2026-10-28.json), files 01 to 15):
root `0c202fbb16fae97fbf0f3cc9d494e4fed2b597fb5a2e33cb3b87deb2e93ee2d0`, anchored in
[`7a3a0e4e77454d51fdb2091eac4899bcda3fbc09e84e8440fd1f88a759bbedae`](https://whatsonchain.com/tx/7a3a0e4e77454d51fdb2091eac4899bcda3fbc09e84e8440fd1f88a759bbedae)
(2026-10-28). Those 15 receipts are byte for byte the same in the new batch;
only the root changed because a 16th leaf was added.

Anyone can check any proof file against the current transaction:

```powershell
python tools\proof_receipt.py verify proofs\04_governor_spend_cap.lean --txid 116140e0ed3c1d2b0a46825128d88a032003bed08ad3fc3d8147c340c825b2cf
```

The tool never signs or broadcasts. To anchor a new batch, pay for one
transaction with an output of the batch's script from a wallet you control,
then set `anchor_txid` in `receipts/batch.json`.

That checks the file hash, the receipt, the Merkle path and the on-chain root
through WhatsOnChain.

## License

Apache-2.0. See [LICENSE](LICENSE).
