"""Plain-Lean guard: proof files may contain definitions and theorems only.

AXLE checks that a file proves the stated theorems with standard axioms.
As defense in depth we also refuse, before anything is sent, any file that
reaches for metaprogramming, unsafe code, extra axioms or checker options.
Competition-style rules: if a proof needs any of these, it does not belong
in a receipt.

    python tools/lean_guard.py proofs/*.lean
"""

import pathlib
import re
import sys

# (pattern, reason). Patterns run on source with comments and strings removed.
DENY = [
    (r"\brun_(cmd|elab|meta|tac)\b", "runs code at elaboration time"),
    (r"#eval\b", "runs code at elaboration time"),
    (r"#exit\b", "stops checking early"),
    (r"\b(elab|elab_rules|macro|macro_rules|syntax|declare_syntax_cat|notation|infix|infixl|infixr|prefix|postfix)\b",
     "changes syntax or elaboration"),
    (r"\b(builtin_)?initialize\b", "runs code at load time"),
    (r"\bunsafe\b", "unsafe code"),
    (r"@\[\s*(implemented_by|extern|csimp)\b", "swaps in unchecked code"),
    (r"\baxiom\b", "adds an axiom"),
    (r"\bnative_decide\b", "trusts compiled code"),
    (r"\bset_option\s+(debug|trace\.Kernel|maxRecDepth\s+0)", "changes checker behaviour"),
    (r"\bopen\s+(\w+\s+)*Lean\b|\bLean\.", "uses Lean's own internals"),
    (r"^\s*import\s+(?!Mathlib\b)", "imports something other than Mathlib"),
]


def strip_comments_and_strings(src: str) -> str:
    out, i, depth, n = [], 0, 0, len(src)
    while i < n:
        if src.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and src.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            out.append("\n" if src[i] == "\n" else " ")
            i += 1
        elif src.startswith("--", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src[i] == '"':
            i += 1
            while i < n and src[i] != '"':
                i += 2 if src[i] == "\\" else 1
            i += 1
            out.append('""')
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def check_source(src: str) -> list[str]:
    code = strip_comments_and_strings(src.removeprefix("﻿"))
    problems = []
    for lineno, line in enumerate(code.splitlines(), 1):
        for pattern, reason in DENY:
            m = re.search(pattern, line)
            if m:
                problems.append(f"line {lineno}: `{m.group(0).strip()}` ({reason})")
    return problems


def main(paths: list[str]) -> int:
    bad = 0
    for p in paths:
        problems = check_source(pathlib.Path(p).read_text(encoding="utf-8-sig"))
        if problems:
            bad += 1
            print(f"REFUSED  {p}")
            for x in problems:
                print("         " + x)
        else:
            print(f"plain    {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
