# bsvkey-axiom-proofs

> **Axiom integration test.** This repo tests [AXLE](https://axle.axiommath.ai/), the
> Axiom Lean Engine from Axiom Math, against BSVKey. It is an experiment, not a
> product, and not an endorsement by or partnership with Axiom.

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

## The 15 BSVKey uses

All 15 files pass AXLE (57 theorems in total). Results are in [`results/`](results).

| # | BSVKey product | Proven property |
|---|---|---|
| 01 | Non-custodial payment channel | Balances are conserved through any sequence of payments and refunds; no side is overdrawn |
| 02 | Paywall Cloud pricing | Price never below the floor, always covers cost plus 3%, rounds up by under one satoshi, never falls when cost rises |
| 03 | Paywall charge-first refunds | Total refunded never exceeds the charge, whatever refund requests arrive |
| 04 | Governor AI spend firewall | Spend never passes the cap for any request stream; kill switch blocks everything |
| 05 | Inference Broker metering | Bill always covers token cost; monotone in tokens; zero tokens is free; splitting a job costs at most 1 sat more |
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

### Negative controls

[`negative/`](negative) holds files AXLE **must reject**, so a pass means something:

- `buggy_paywall_pricing.lean`: the price rule with the 3% margin rounded **down**.
  AXLE rejects it, and `disprove` finds the counterexample (a cost of 1 sat is underpriced).
- `sorry_governor.lean`: an unfinished proof. AXLE rejects it.

## Check a receipt in your browser

[`index.html`](index.html) checks any proof against its receipt and the
on-chain root with nothing installed: it hashes the file with Web Crypto,
rebuilds the receipt leaf, climbs the Merkle path and reads the transaction
from WhatsOnChain. "Check all 15" runs every file. You can also drop your own
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
and theorems, the same rule many proof competitions use. It is defense in
depth on top of AXLE, and it runs in the Action too.

## Soundness tests of AXLE

[`soundness/`](soundness) holds adversarial cases: files that try to make
`verify_proof` accept a false or unproven claim (hidden `sorry`, custom axioms,
`native_decide`, weaker or renamed statements, redefined definitions, instance,
notation and macro overrides of `+`, `#exit`, `opaque` and `unsafe` tricks),
plus honest controls that must pass. AXLE handled all of them correctly.

```powershell
python soundness\run_soundness.py
```

## What these proofs do and do not show

- Each file proves a property of a **model** of a BSVKey rule, written in Lean.
  It does **not** prove that the deployed code (JavaScript, TypeScript or Python)
  matches the model. That link is checked by each product's own tests, not here.
- Files 09 and 10 treat the hash function as ideal (collision resistant). They do
  not prove anything about SHA-256 itself.
- A pass means Lean's kernel accepted the proof on Axiom's servers. You can re-check
  any file yourself with a local Lean 4.35.0 and Mathlib install.

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

Current batch ([`receipts/batch.json`](receipts/batch.json)):

- Merkle root: `0c202fbb16fae97fbf0f3cc9d494e4fed2b597fb5a2e33cb3b87deb2e93ee2d0`
- OP_RETURN script: `OP_FALSE OP_RETURN "bsvkey.proof" <root>`
- Anchored on Bitcoin BSV mainnet in transaction
  [`7a3a0e4e77454d51fdb2091eac4899bcda3fbc09e84e8440fd1f88a759bbedae`](https://whatsonchain.com/tx/7a3a0e4e77454d51fdb2091eac4899bcda3fbc09e84e8440fd1f88a759bbedae)
  (broadcast 2026-10-28, one input, 25 sat fee).

Anyone can check any proof file against that transaction:

```powershell
python tools\proof_receipt.py verify proofs\04_governor_spend_cap.lean --txid 7a3a0e4e77454d51fdb2091eac4899bcda3fbc09e84e8440fd1f88a759bbedae
```

The tool never signs or broadcasts. To anchor a new batch, pay for one
transaction with an output of the batch's script from a wallet you control,
then set `anchor_txid` in `receipts/batch.json`.

That checks the file hash, the receipt, the Merkle path and the on-chain root
through WhatsOnChain.

## License

Apache-2.0. See [LICENSE](LICENSE).
