# Kernel replay catches what AXLE accepts

A tiny Lake project (Lean 4.35.0, no Mathlib) with two modules:

- `Honest.lean`: a normal proof.
- `Exploit.lean`: the "proof" of `False` from [ADVISORY.md](../../ADVISORY.md).

Lean **compiles both without errors**. Replaying the compiled modules through
Lean's kernel with `leanchecker` (shipped with the Lean 4.35.0 toolchain)
tells them apart.

```powershell
lake build
lake env leanchecker Honest
lake env leanchecker Exploit
```

Output on 2026-10-28 (Windows, Lean 4.35.0):

```
Build completed successfully (5 jobs).
Honest:  exit 0
Exploit: leanchecker found a problem in Exploit
         uncaught exception: while replaying declaration 't':
         (kernel) declaration type mismatch, 't' has type
           True
         but it is expected to have type
           False
```

Any service or pipeline that reports a proof as verified should replay the
compiled declarations like this (or with an independent checker such as
`lean4lean` or `nanoda`, which also ship with the toolchain) before saying yes.
