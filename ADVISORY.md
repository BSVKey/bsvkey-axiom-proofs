# Advisory: AXLE verify_proof accepts a proof of False

**Published:** 2026-10-28 by BSVKey (Embryo Space Inc.)
**Affects:** Axiom's AXLE (Axiom Lean Engine), `verify_proof`, environment
`lean-4.35.0`, tested with the `axiom-axle` 1.9.0 client against
https://axle.axiommath.ai. Other environments not tested.
**Status:** reported to Axiom (axle@axiommath.ai) on 2026-10-28. Axiom replied
on 2026-10-31: this is a known limitation and a deliberate design decision, kept
for `verify_proof` throughput; it will not be fixed. See
[Axiom's response](#axioms-response). Re-run
[`soundness/run_soundness.py`](soundness/run_soundness.py) to see the current
state: a fixed case prints `FIXED`.

## Summary

`verify_proof` returns `okay: true` for a file that proves `False`. The file
uses a short `run_cmd` metaprogram that adds the target theorem to the Lean
environment with the kernel check turned off. AXLE then finds a declaration
with the right name and type that uses only standard axioms, and accepts it.
Nothing re-checks that declaration with Lean's kernel.

Because the statement can be anything, **an `okay: true` from AXLE can be forged
by whoever writes the proof file.**

## Reproduction

formal_statement:

```lean
theorem t : False := by sorry
```

content:

```lean
abbrev Claim : Prop := False
open Lean Elab Command in
run_cmd do
  let ty := ((← getEnv).find? ``Claim).get!.value!
  let decl := Declaration.thmDecl { name := `t, levelParams := [], type := ty, value := mkConst ``True.intro }
  match (← getEnv).addDeclCore 0 0 decl none (doCheck := false) with
  | .ok env' => setEnv env'
  | .error _ => throwError "rejected"
```

Result: `okay: true`, no errors. A second route
(`toKernelEnv.addDeclWithoutChecking`, then `Environment.ofKernelEnv`) is also
accepted. Both are cases in [`soundness/cases.py`](soundness/cases.py); we
reproduced them three times on 2026-10-28.

The `Claim` indirection only makes the type match the stated theorem exactly.
Without it the trick still runs but fails AXLE's signature comparison.

## Who should care

- **AI training.** If AXLE is a reward signal for a prover model, the model can
  learn to emit this pattern instead of proofs.
- **Benchmarks and competitions** that take `okay: true` as a solved problem.
- **Anyone recording "verified by AXLE"**, including us: our 15 receipts
  anchored on Bitcoin BSV are unaffected because none of those files use
  metaprogramming, and the [guard](tools/lean_guard.py) now refuses any file
  that does. All 15 also pass an independent kernel replay (`leanchecker`) and
  axiom audit with the official Lean 4.35.0 and Mathlib v4.35.0, outside AXLE
  ([CI run](https://github.com/BSVKey/bsvkey-axiom-proofs/actions/runs/40689665073)).

## What AXLE gets right

The other 19 cases in the suite are rejected as they should be: `sorry`
(direct, in a helper, hidden in a macro), custom axioms, `native_decide`,
weaker or renamed statements, extra hypotheses, namespace shadowing, redefined
definitions, instance, notation and `macro_rules` overrides that change what
`+` means, redefining `False`, `#exit`, and `opaque` and `unsafe` tricks.
The statement comparison is strong. The gap is only that elaborated
declarations are trusted without a fresh kernel check.

## Fix

1. **Replay through the kernel** before returning `okay`. Lean 4.35.0 ships
   `leanchecker`, which replays every declaration of a compiled module through
   the kernel. On this exploit it reports
   `(kernel) declaration type mismatch, 't' has type True but it is expected to have type False`,
   while honest proofs pass. Demo: [`soundness/kernel-replay/`](soundness/kernel-replay).
2. **Refuse environment-changing metaprogramming** in submitted content
   (`run_cmd`, `#eval`, `elab`, `macro`, `open Lean`, `unsafe`, ...), as
   [`tools/lean_guard.py`](tools/lean_guard.py) does. Defense in depth only;
   deny lists can miss things, the kernel replay cannot.

## Axiom's response

Axiom replied on 2026-10-31. They know about this limitation and chose it on
purpose: a kernel replay fixes it but cuts `verify_proof` throughput, which
they see as AXLE's main advantage over lean4checker, Comparator and SafeVerify.
They leave it as an explicit gap rather than patching individual cases.

Their technical report documents it
([arXiv:2606.26442](https://arxiv.org/abs/2606.26442), submitted 2026-06-24).
Section 5.2 says `verify_proof` trusts that declarations came through the
normal kernel-checked path and compares its speed with the stricter checkers.
Appendix C.3 shows an `addDeclCore` example with the kernel check off that
`verify_proof` accepts and lean4checker rejects, and recommends adding a strict
checker for adversarial or outside code.

So this advisory describes documented behavior, not an undisclosed bug. We keep
it up because many users may not read the appendix before treating `okay: true`
as a kernel-checked result.

## If you use AXLE today

`verify_proof` will not catch this. If the proof files come from anyone you do
not fully trust (a prover model being trained, a benchmark entry, an outside
submitter), run the guard before sending files and replay accepted proofs
through the kernel (`leanchecker`, Comparator or SafeVerify). Treat
`okay: true` alone as "the statement matches and the elaborator was happy", not
as "the kernel checked it".
