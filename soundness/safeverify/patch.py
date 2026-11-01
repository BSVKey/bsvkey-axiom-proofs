"""Make SafeVerify (commit in COMMIT) build on Lean 4.35.0.

`CollectAxioms.collect` is private in Lean core since v4.30.0, so SafeVerify's
Main.lean no longer compiles. This swaps its two call sites for the public
`collectAxioms`, the change proposed in GasStationManager/SafeVerify#25.
No check is changed: the same axioms are collected for the same constants.

    python patch.py path/to/SafeVerify/Main.lean
"""

import pathlib
import re
import sys

HELPER = """
-- Added for Lean >= 4.30 (CollectAxioms.collect is private there), as in SafeVerify#25.
instance : MonadEnv (ReaderT Environment Id) where
  getEnv := read
  modifyEnv _ := pure ()

def axiomsIn (env : Environment) (n : Name) : Array Name :=
  (collectAxioms n : ReaderT Environment Id (Array Name)).run env
"""

CALL = re.compile(r"let \(_, s\) := \(CollectAxioms\.collect (\S+)\)\.run (\S+) \|>\.run \{\}")


def main(path: str) -> int:
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8")
    src, n = CALL.subn(r"let axs := axiomsIn \2 \1", src)
    if n != 2:
        sys.exit(f"expected 2 CollectAxioms.collect call sites, found {n}")
    src, m = re.subn(r"\bs\.axioms\b", "axs", src)
    if m != 2:
        sys.exit(f"expected 2 uses of s.axioms, found {m}")
    anchor = "open Std\n"
    if anchor not in src:
        sys.exit("could not find `open Std` to insert the helper after")
    src = src.replace(anchor, anchor + HELPER, 1)
    p.write_text(src, encoding="utf-8")
    print(f"patched {p}: 2 call sites now use collectAxioms")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
