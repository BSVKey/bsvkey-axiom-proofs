"""Offline tests for the kernel-check project generator."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import kernel_project as k  # noqa: E402


class KernelProjectTests(unittest.TestCase):
    def test_finds_all_64_theorems(self):
        files = sorted((ROOT / "proofs").glob("*.lean"))
        names = [n for f in files for n in k.theorems(f)]
        self.assertEqual(len(files), 16)
        self.assertEqual(len(names), 64)
        self.assertEqual(len(set(names)), 64)
        self.assertIn("BSVKey.Channel.pay_conserves", names)

    def test_module_names_are_valid(self):
        for f in (ROOT / "proofs").glob("*.lean"):
            self.assertRegex(k.module_name(f), r"^[A-Za-z_][A-Za-z0-9_]*$")

    def test_parses_print_axioms(self):
        out = ("'A.b' depends on axioms: [propext,\n Classical.choice, Quot.sound]\n"
               "'A.c' does not depend on any axioms\n")
        got = dict(k.PRINTED.findall(" ".join(out.split())))
        self.assertEqual(got["A.b"], "propext, Classical.choice, Quot.sound")
        self.assertEqual(got["A.c"], "")


if __name__ == "__main__":
    unittest.main()
