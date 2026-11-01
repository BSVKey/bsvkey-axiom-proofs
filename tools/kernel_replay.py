"""Kernel replay for the Action: the check AXLE's verify_proof leaves out.

AXLE trusts that every declaration was added through Lean's kernel-checked
path (Axiom's report, arXiv:2606.26442, Appendix C.3), so a file that adds a
theorem with the kernel check turned off passes. This step compiles the same
files with the official Lean toolchain, replays every compiled declaration
through the kernel with `leanchecker`, and audits the axioms of every theorem.

    python tools/kernel_replay.py prepare   # write the Lake project
    (lake update, lake exe cache get if Mathlib, lake build, all in that project)
    python tools/kernel_replay.py check     # leanchecker + axiom audit, per file

Each file becomes its own module and is checked on its own, as AXLE checks
each file on its own, so two files may both declare a theorem `t`.

Settings come from the environment, as for axle_verify.py:
    AXLE_PROOFS_DIR      folder of .lean files (default: proofs)
    AXLE_RESULTS_DIR     where kernel.json goes (default: axle-results)
    AXLE_ENVIRONMENT     AXLE environment, e.g. lean-4.35.0 (picks the toolchain)
    KERNEL_DIR           Lake project to write (default: .axle-kernel)
    KERNEL_MATHLIB       true, false or auto (default: auto, on if any file imports Mathlib)
    KERNEL_AXIOMS        comma-separated allowed axioms
                         (default: propext,Classical.choice,Quot.sound)
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

PROOFS = pathlib.Path(os.environ.get("AXLE_PROOFS_DIR") or "proofs")
RESULTS = pathlib.Path(os.environ.get("AXLE_RESULTS_DIR") or "axle-results")
ENVIRONMENT = os.environ.get("AXLE_ENVIRONMENT") or "lean-4.35.0"
KERNEL = pathlib.Path(os.environ.get("KERNEL_DIR") or ".axle-kernel")
MATHLIB = (os.environ.get("KERNEL_MATHLIB") or "auto").lower()
ALLOWED = {a.strip() for a in (os.environ.get("KERNEL_AXIOMS")
                               or "propext,Classical.choice,Quot.sound").split(",") if a.strip()}

# Prints one line per theorem declared in module MOD: AXIOMS<TAB>name<TAB>a,b
AUDIT = """import Lean
import MOD
open Lean Elab Command

#eval show CommandElabM Unit from do
  let env ← getEnv
  let mods := env.header.moduleNames
  let mut rows : Array (String × String) := #[]
  for (n, ci) in env.constants.map₁.toList do
    let .thmInfo _ := ci | continue
    if n.isInternalDetail then continue
    let some idx := env.getModuleIdxFor? n | continue
    unless mods[idx.toNat]! == `MOD do continue
    let axs ← collectAxioms n
    rows := rows.push (n.toString, ",".intercalate (axs.toList.map toString))
  for (n, a) in rows.qsort (fun x y => x.1 < y.1) do
    IO.println s!"AXIOMS\\t{n}\\t{a}"
"""


def toolchain(environment: str) -> str:
    m = re.fullmatch(r"lean-(\d+\.\d+\.\d+(?:-rc\d+)?)", environment)
    if not m:
        sys.exit(f"cannot map AXLE environment {environment!r} to a Lean toolchain; "
                 "kernel replay supports lean-X.Y.Z environments")
    return m.group(1)


def module_part(part: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", part)
    return s if s[:1].isalpha() else "P" + s


def lean_files() -> list[pathlib.Path]:
    return sorted(p for p in PROOFS.rglob("*.lean") if ".lake" not in p.parts)


def prepare() -> int:
    files = lean_files()
    if not files:
        sys.exit(f"no .lean files under {PROOFS}")
    version = toolchain(ENVIRONMENT)
    mathlib = MATHLIB == "true" or (MATHLIB == "auto" and any(
        re.search(r"^import\s+Mathlib", f.read_text(encoding="utf-8"), re.M) for f in files))

    shutil.rmtree(KERNEL / "Proofs", ignore_errors=True)
    (KERNEL / "Proofs").mkdir(parents=True)
    modules = {}
    for f in files:
        rel = f.relative_to(PROOFS).with_suffix("")
        name = "Proofs." + ".".join(module_part(p) for p in rel.parts)
        if name in modules.values():
            sys.exit(f"{f}: module name {name} clashes with another file")
        dest = KERNEL / pathlib.Path(*name.split(".")).with_suffix(".lean")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(f.read_bytes())  # byte for byte: hashes still match the originals
        modules[f.relative_to(PROOFS).as_posix()] = name

    (KERNEL / "lean-toolchain").write_text(f"leanprover/lean4:v{version}\n", encoding="utf-8")
    lakefile = 'name = "kernel"\ndefaultTargets = ["Proofs"]\n\n'
    if mathlib:
        lakefile += ('[[require]]\nname = "mathlib"\nscope = "leanprover-community"\n'
                     f'rev = "v{version}"\n\n')
    # No root module: each file is built as its own module, never imported together.
    lakefile += '[[lean_lib]]\nname = "Proofs"\nglobs = ["Proofs.+"]\n'
    (KERNEL / "lakefile.toml").write_text(lakefile, encoding="utf-8")
    (KERNEL / "modules.json").write_text(json.dumps(modules, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"mathlib={'true' if mathlib else 'false'}\n")
    print(f"{len(files)} files -> {KERNEL / 'Proofs'} (Lean {version}, Mathlib {'yes' if mathlib else 'no'})")
    return 0


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=KERNEL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def check_file(lake: str, file: str, mod: str) -> dict:
    row = {"file": file, "module": mod, "replay": "ok", "theorems": [], "ok": False}
    code, out, err = run([lake, "env", "leanchecker", mod])
    if code != 0:
        lines = [ln.strip() for ln in (out + err).splitlines() if ln.strip()]
        row["replay"] = "REJECTED: " + " ".join(lines[-4:])[:300]
        return row
    audit = KERNEL / ".audit.lean"
    audit.write_text(AUDIT.replace("MOD", mod), encoding="utf-8")
    code, out, err = run([lake, "env", "lean", audit.name])
    if code != 0:
        row["replay"] = "ok"
        row["audit_error"] = (out + err).strip()[:300]
        return row
    for line in out.splitlines():
        if line.startswith("AXIOMS\t"):
            _, name, axs = line.split("\t", 2)
            used = [a for a in axs.split(",") if a]
            row["theorems"].append({"theorem": name, "axioms": used,
                                    "bad_axioms": sorted(set(used) - ALLOWED)})
    row["ok"] = bool(row["theorems"]) and not any(t["bad_axioms"] for t in row["theorems"])
    return row


def check() -> int:
    modules = json.loads((KERNEL / "modules.json").read_text(encoding="utf-8"))
    lake = shutil.which("lake") or "lake"
    rows = [check_file(lake, f, m) for f, m in modules.items()]
    (KERNEL / ".audit.lean").unlink(missing_ok=True)

    def why(r: dict) -> str:
        if r["replay"] != "ok":
            return r["replay"]
        if "audit_error" in r:
            return "axiom audit failed: " + r["audit_error"]
        if not r["theorems"]:
            return "no theorems found"
        bad = sorted({a for t in r["theorems"] for a in t["bad_axioms"]})
        return "other axioms: " + ", ".join(bad) if bad else "ok"

    passed = sum(r["ok"] for r in rows)
    theorems = sum(len(r["theorems"]) for r in rows)
    verdict = (f"PASS: all {len(rows)} files replay through the kernel; their {theorems} theorems "
               f"use only {', '.join(sorted(ALLOWED))}" if passed == len(rows)
               else f"FAIL: {len(rows) - passed} of {len(rows)} files failed kernel replay or the axiom audit")
    for r in rows:
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['file']}  ({len(r['theorems'])} theorems)  {why(r)}")
    print(verdict)

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "kernel.json").write_text(json.dumps({
        "check": "kernel replay (leanchecker) + axiom audit",
        "lean": toolchain(ENVIRONMENT), "allowed_axioms": sorted(ALLOWED),
        "passed": passed == len(rows), "files": rows}, indent=2) + "\n", encoding="utf-8")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Kernel replay and axiom audit\n\n**{verdict}**\n\n"
                     "| File | Theorems | Result |\n|---|---|---|\n")
            fh.writelines(f"| {r['file']} | {len(r['theorems'])} | {why(r)} |\n" for r in rows)
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        sys.exit(prepare())
    if cmd == "check":
        sys.exit(check())
    sys.exit("usage: kernel_replay.py prepare|check")
