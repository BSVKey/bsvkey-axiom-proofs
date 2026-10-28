"""Offline tests for the plain-Lean guard."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lean_guard as g  # noqa: E402


class GuardTests(unittest.TestCase):
    def test_all_repo_proofs_are_plain(self):
        for p in sorted((ROOT / "proofs").glob("*.lean")) + sorted((ROOT / "negative").glob("*.lean")):
            self.assertEqual(g.check_source(p.read_text(encoding="utf-8-sig")), [], p.name)

    def test_refuses_metaprogramming(self):
        for snippet in [
            "run_cmd do pure ()",
            "#eval 1 + 1",
            "open Lean Elab in\ntheorem t : True := trivial",
            "def x := Lean.mkConst `y",
            "macro \"go\" : tactic => `(tactic| rfl)",
            "elab \"go\" : tactic => pure ()",
            "initialize pure ()",
            "#exit",
        ]:
            self.assertTrue(g.check_source(snippet), snippet)

    def test_refuses_trust_escapes(self):
        for snippet in [
            "axiom cheat : False",
            "theorem t : 1 = 1 := by native_decide",
            "unsafe def u : Nat := 0",
            "@[implemented_by u] def v : Nat := 1",
            "set_option debug.skipKernelTC true in\ntheorem t : True := trivial",
            "import Foo",
        ]:
            self.assertTrue(g.check_source(snippet), snippet)

    def test_allows_mathlib_import(self):
        self.assertEqual(g.check_source("import Mathlib\ntheorem t : 1 = 1 := rfl"), [])

    def test_comments_and_strings_do_not_trigger(self):
        src = (
            "/- run_cmd and Lean.foo in a doc comment, /- nested axiom -/ still comment -/\n"
            "-- #eval in a line comment\n"
            'def s : String := "macro unsafe axiom"\n'
            "theorem t : s.length = 18 := by decide\n"
        )
        self.assertEqual(g.check_source(src), [])

    def test_reports_line_numbers(self):
        problems = g.check_source("theorem a : True := trivial\naxiom b : False")
        self.assertTrue(problems[0].startswith("line 2:"), problems)


if __name__ == "__main__":
    unittest.main()
