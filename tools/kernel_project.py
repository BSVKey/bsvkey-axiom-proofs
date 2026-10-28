"""Independent kernel check: put the proof files in a Lake project, audit axioms.

Lean module names cannot start with a digit, so proofs/01_payment_channel.lean
is copied byte for byte to kernel/Proofs/P01_payment_channel.lean. The copies
are generated (git ignores them); proofs/ itself is never touched, so the
hashes anchored on Bitcoin BSV still match.

    python tools/kernel_project.py           # write kernel/Proofs/, Proofs.lean, Audit.lean
    python tools/kernel_project.py --audit   # after the build: #print axioms on every theorem

After `lake build` and `lake env leanchecker` have replayed every compiled
declaration through Lean's kernel, --audit confirms that each theorem named
in proofs/ exists in the compiled environment and uses only the allowed
axioms. Writes a table to $GITHUB_STEP_SUMMARY when run in GitHub Actions.
"""

import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOFS = ROOT / "proofs"
KERNEL = ROOT / "kernel"
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}

THEOREM = re.compile(r"^(?:private\s+|protected\s+)?(?:theorem|lemma)\s+([^\s(:{\[]+)", re.M)
NAMESPACE = re.compile(r"^namespace\s+(\S+)", re.M)
PRINTED = re.compile(
    r"'([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)")


def module_name(path: pathlib.Path) -> str:
    return "P" + path.stem


def theorems(path: pathlib.Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    spaces = NAMESPACE.findall(src)
    if len(spaces) != 1:
        sys.exit(f"{path.name}: expected exactly one namespace, found {spaces}")
    return [f"{spaces[0]}.{name}" for name in THEOREM.findall(src)]


def generate() -> dict[str, list[str]]:
    files = sorted(PROOFS.glob("*.lean"))
    out = KERNEL / "Proofs"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    found = {}
    for f in files:
        dest = out / (module_name(f) + ".lean")
        dest.write_bytes(f.read_bytes())
        found[f.name] = theorems(f)
    (KERNEL / "Proofs.lean").write_text(
        "".join(f"import Proofs.{module_name(f)}\n" for f in files), encoding="utf-8")
    names = [n for ns in found.values() for n in ns]
    (KERNEL / "Audit.lean").write_text(
        "import Proofs\n\n" + "".join(f"#print axioms {n}\n" for n in names), encoding="utf-8")
    print(f"{len(files)} proof files, {len(names)} theorems -> {out}")
    return found


def audit(found: dict[str, list[str]]) -> int:
    lake = shutil.which("lake") or "lake"
    run = subprocess.run([lake, "env", "lean", "Audit.lean"], cwd=KERNEL,
                         capture_output=True, text=True, encoding="utf-8")
    text = run.stdout + run.stderr
    axioms = {name: [a.strip() for a in (lst or "").split(",") if a.strip()]
              for name, lst in PRINTED.findall(" ".join(text.split()))}

    rows, bad = [], 0
    for file, names in found.items():
        for name in names:
            used = axioms.get(name)
            if used is None:
                status, bad = "MISSING from compiled environment", bad + 1
            elif set(used) - ALLOWED:
                status, bad = "FAIL: " + ", ".join(sorted(set(used) - ALLOWED)), bad + 1
            else:
                status = "ok"
            rows.append((file, name, ", ".join(used or []) or "none", status))

    for row in rows:
        print("  ".join(row))
    total = len(rows)
    if run.returncode != 0:
        print(text)
        bad = bad or 1
    verdict = (f"PASS: all {total} theorems in {len(found)} files use only "
               f"{', '.join(sorted(ALLOWED))}" if not bad
               else f"FAIL: {bad} of {total} theorems failed the axiom check")
    print(verdict)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Kernel replay and axiom audit\n\n**{verdict}**\n\n"
                     "| File | Theorem | Axioms | Result |\n|---|---|---|---|\n")
            fh.writelines(f"| {f} | `{n}` | {a} | {s} |\n" for f, n, a, s in rows)
    return 1 if bad else 0


if __name__ == "__main__":
    if "--audit" in sys.argv[1:]:
        sys.exit(audit({f.name: theorems(f) for f in sorted(PROOFS.glob("*.lean"))}))
    generate()
