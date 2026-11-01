"""Run the soundness cases through other Lean proof checkers, not just AXLE.

Each case in cases.py becomes a tiny Lake project: Challenge.lean holds the
statement (with `sorry`), Solution.lean holds the candidate file. Every checker
gets its own fresh copy, so no checker sees files another one built.

    python soundness/compare_checkers.py --checkers leanchecker
    python soundness/compare_checkers.py --checkers leanchecker,comparator,safeverify \
        --safeverify path/to/safe_verify

Checkers:
  leanchecker  `lake build`, then `lake env leanchecker Solution`. Kernel replay
               only: it does not compare the statement or check axioms, so it is
               shown to separate those two jobs, not as a full judge.
  comparator   `lake comparator` (built into Lean 4.35.0, formerly
               leanprover/comparator). Needs Linux with bubblewrap: it builds the
               solution inside a sandbox.
  safeverify   GasStationManager/SafeVerify on the two compiled .olean files.
  axle         AXLE verify_proof, read from soundness/results.json (written by
               run_soundness.py); not re-run here.

Writes soundness/checkers.json and soundness/CHECKERS.md. Exits 1 only if a
checker could not run; what each checker accepts is reported, not judged.
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cases import CASES  # noqa: E402

TOOLCHAIN = "leanprover/lean4:v4.35.0"
AXIOMS = ["propext", "Quot.sound", "Classical.choice"]
THEOREM = re.compile(r"^theorem\s+([^\s(:{\[]+)", re.M)
TIMEOUT = 600
HEADER = "import Lean\n"
LAKEFILE = 'name = "case"\n\n[[lean_lib]]\nname = "Challenge"\n\n[[lean_lib]]\nname = "Solution"\n'
MANIFEST = {"version": "1.1.0", "packagesDir": ".lake/packages", "packages": [],
            "name": "case", "lakeDir": ".lake"}


def make_project(root: pathlib.Path, case: dict) -> pathlib.Path:
    root.mkdir(parents=True)
    (root / "lean-toolchain").write_text(TOOLCHAIN + "\n", encoding="utf-8")
    (root / "lakefile.toml").write_text(LAKEFILE, encoding="utf-8")
    (root / "lake-manifest.json").write_text(json.dumps(MANIFEST, indent=1) + "\n", encoding="utf-8")
    # AXLE's environments import Mathlib, which brings in `Lean`; plain Lean does not.
    (root / "Challenge.lean").write_text(HEADER + case["statement"] + "\n", encoding="utf-8")
    (root / "Solution.lean").write_text(HEADER + case["content"] + "\n", encoding="utf-8")
    (root / "comparator.json").write_text(json.dumps({
        "challenge_module": "Challenge", "solution_module": "Solution",
        "theorem_names": THEOREM.findall(case["statement"]), "permitted_axioms": AXIOMS,
    }), encoding="utf-8")
    return root


def run(cmd: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {TIMEOUT} s"


def first_error(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if "error" in ln.lower() or "exception" in ln.lower() or "mismatch" in ln.lower():
            return ln.strip()[:200]
    return (lines[-1].strip() if lines else "")[:200]


def check_leanchecker(d: pathlib.Path, lake: str, _args) -> dict:
    code, out = run([lake, "build", "Solution"], d)
    if code != 0:
        return {"accepted": False, "reason": "build failed: " + first_error(out)}
    code, out = run([lake, "env", "leanchecker", "Solution"], d)
    return {"accepted": code == 0, "reason": "" if code == 0 else first_error(out)}


def check_comparator(d: pathlib.Path, lake: str, _args) -> dict:
    code, out = run([lake, "comparator"], d)
    if code == 2:
        return {"error": "could not start: " + first_error(out)}
    return {"accepted": code == 0, "reason": "" if code == 0 else first_error(out)}


def check_safeverify(d: pathlib.Path, lake: str, args) -> dict:
    code, out = run([lake, "build", "Challenge"], d)
    if code != 0:
        return {"error": "challenge did not build: " + first_error(out)}
    code, out = run([lake, "build", "Solution"], d)
    if code != 0:
        return {"accepted": False, "reason": "build failed: " + first_error(out)}
    lib = d / ".lake" / "build" / "lib" / "lean"
    code, out = run([lake, "env", args.safeverify, str(lib / "Challenge.olean"),
                     str(lib / "Solution.olean")], d)
    return {"accepted": code == 0, "reason": "" if code == 0 else first_error(out)}


CHECKERS = {"leanchecker": check_leanchecker, "comparator": check_comparator,
            "safeverify": check_safeverify}


def axle_results() -> tuple[dict, str]:
    path = HERE / "results.json"
    if not path.exists():
        return {}, ""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = {r["name"]: {"accepted": r["accepted"], "reason": (r["reason"] or [""])[0][:200]}
            for r in data["cases"]}
    return rows, data.get("environment", "")


def mark(case: dict, res: dict | None) -> str:
    if res is None:
        return "not run"
    if "error" in res:
        return "error"
    sound = res["accepted"] == (case["expect"] == "accept")
    word = "accepts" if res["accepted"] else "rejects"
    return word if sound else f"**{word}** (wrong)"


def write_markdown(results: dict, names: list[str], meta: dict) -> None:
    head = ["Case", "Expected"] + names
    lines = [
        "# Lean proof checkers on the soundness cases",
        "",
        "Generated by [`compare_checkers.py`](compare_checkers.py) from the cases in",
        "[`cases.py`](cases.py). A sound checker rejects every cheat and accepts both",
        "honest controls; **bold** marks a wrong answer.",
        "",
        f"Run: {meta['date']}, Lean 4.35.0, {meta['platform']}.",
        "",
        "- **AXLE**: `verify_proof`, environment `lean-4.35.0`, from `results.json`.",
        "- **leanchecker**: kernel replay of the compiled solution only. It does not",
        "  compare the statement or check axioms, so it is not a full judge on its own.",
        "- **comparator**: `lake comparator`, built into Lean 4.35.0, run in its sandbox.",
        "- **safeverify**: GasStationManager/SafeVerify at the commit in the workflow.",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "---|" * len(head),
    ]
    for case in CASES:
        cells = [f"`{case['name']}`", case["expect"]]
        cells += [mark(case, results[case["name"]].get(n)) for n in names]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    for n in names:
        wrong = [c["name"] for c in CASES
                 if (r := results[c["name"]].get(n)) and "error" not in r
                 and r["accepted"] != (c["expect"] == "accept")]
        ran = sum(1 for c in CASES if (r := results[c["name"]].get(n)) and "error" not in r)
        lines.append(f"- **{n}**: {ran - len(wrong)} of {ran} right"
                     + (f"; wrong on {', '.join(f'`{w}`' for w in wrong)}" if wrong else ""))
    (HERE / "CHECKERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkers", default="leanchecker")
    ap.add_argument("--safeverify", help="path to the safe_verify executable")
    ap.add_argument("--only", help="comma-separated case names")
    args = ap.parse_args()
    chosen = [c.strip() for c in args.checkers.split(",") if c.strip()]
    for c in chosen:
        if c not in CHECKERS:
            sys.exit(f"unknown checker {c}; choose from {', '.join(CHECKERS)}")
    if "safeverify" in chosen and not args.safeverify:
        sys.exit("--safeverify PATH is required for the safeverify checker")
    lake = shutil.which("lake") or sys.exit("lake not found on PATH (install Lean with elan)")
    cases = [c for c in CASES if not args.only or c["name"] in args.only.split(",")]

    axle, axle_env = axle_results()
    results = {c["name"]: {} for c in CASES}
    for c in CASES:
        if c["name"] in axle:
            results[c["name"]]["axle"] = axle[c["name"]]

    failed = False
    with tempfile.TemporaryDirectory(prefix="checkers-") as tmp:
        for case in cases:
            for name in chosen:
                d = make_project(pathlib.Path(tmp) / name / case["name"], case)
                res = CHECKERS[name](d, lake, args)
                results[case["name"]][name] = res
                failed |= "error" in res
                print(f"{name:<12} {case['name']:<30} {mark(case, res)}"
                      + (f"  [{res.get('reason') or res.get('error')}]" if res.get("reason") or res.get("error") else ""))

    names = (["axle"] if axle else []) + chosen
    meta = {"date": datetime.date.today().isoformat(), "axle_environment": axle_env,
            "platform": os.environ.get("RUNNER_OS", sys.platform)}
    (HERE / "checkers.json").write_text(json.dumps(
        {"meta": meta, "checkers": names, "cases": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    if not args.only:
        write_markdown(results, names, meta)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
