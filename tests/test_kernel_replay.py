"""Offline tests for the Action's kernel-replay project generator and the checker comparison."""

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "soundness"))

import compare_checkers as cc  # noqa: E402
import kernel_replay as kr  # noqa: E402


class KernelReplayPrepareTests(unittest.TestCase):
    def prepare(self, files: dict[str, str], mathlib: str = "auto") -> pathlib.Path:
        tmp = pathlib.Path(tempfile.mkdtemp())
        src = tmp / "src"
        for name, text in files.items():
            (src / name).parent.mkdir(parents=True, exist_ok=True)
            (src / name).write_bytes(text.encode("utf-8"))
        kr.PROOFS, kr.KERNEL, kr.MATHLIB, kr.ENVIRONMENT = src, tmp / "k", mathlib, "lean-4.35.0"
        self.assertEqual(kr.prepare(), 0)
        return tmp / "k"

    def test_each_file_is_its_own_module(self):
        k = self.prepare({"01_a.lean": "theorem t : True := trivial\n",
                          "sub/b-c.lean": "theorem t : True := trivial\n"})
        modules = json.loads((k / "modules.json").read_text(encoding="utf-8"))
        self.assertEqual(modules, {"01_a.lean": "Proofs.P01_a", "sub/b-c.lean": "Proofs.sub.b_c"})
        self.assertTrue((k / "Proofs" / "P01_a.lean").exists())
        self.assertTrue((k / "Proofs" / "sub" / "b_c.lean").exists())
        # no root module importing everything, so two files may both declare `t`
        self.assertFalse((k / "Proofs.lean").exists())
        self.assertIn('globs = ["Proofs.+"]', (k / "lakefile.toml").read_text(encoding="utf-8"))

    def test_copies_are_byte_for_byte(self):
        text = "-- é\r\ntheorem t : True := trivial\r\n"
        k = self.prepare({"a.lean": text})
        self.assertEqual((k / "Proofs" / "a.lean").read_bytes(), text.encode("utf-8"))

    def test_mathlib_auto_detects_import(self):
        k = self.prepare({"a.lean": "theorem t : True := trivial\n"})
        self.assertNotIn("mathlib", (k / "lakefile.toml").read_text(encoding="utf-8"))
        k = self.prepare({"a.lean": "import Mathlib\ntheorem t : True := trivial\n"})
        lake = (k / "lakefile.toml").read_text(encoding="utf-8")
        self.assertIn('name = "mathlib"', lake)
        self.assertIn('rev = "v4.35.0"', lake)
        self.assertEqual((k / "lean-toolchain").read_text(encoding="utf-8").strip(),
                         "leanprover/lean4:v4.35.0")

    def test_environment_maps_to_toolchain(self):
        self.assertEqual(kr.toolchain("lean-4.35.0"), "4.35.0")
        self.assertEqual(kr.toolchain("lean-4.36.0-rc1"), "4.36.0-rc1")
        with self.assertRaises(SystemExit):
            kr.toolchain("cslib-1.0")

    def test_audit_template_names_the_module(self):
        src = kr.AUDIT.replace("MOD", "Proofs.P01_a")
        self.assertIn("import Proofs.P01_a\n", src)
        self.assertIn("== `Proofs.P01_a", src)


class CompareCheckersTests(unittest.TestCase):
    def test_every_case_gets_a_project(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        for case in cc.CASES:
            d = cc.make_project(tmp / case["name"], case)
            config = json.loads((d / "comparator.json").read_text(encoding="utf-8"))
            self.assertTrue(config["theorem_names"], case["name"])
            self.assertEqual(config["permitted_axioms"], cc.AXIOMS)
            self.assertTrue((d / "lake-manifest.json").exists())
            self.assertTrue((d / "Solution.lean").read_text(encoding="utf-8").startswith("import Lean\n"))

    def test_marks(self):
        reject = {"expect": "reject"}
        self.assertEqual(cc.mark(reject, {"accepted": False}), "rejects")
        self.assertEqual(cc.mark(reject, {"accepted": True}), "**accepts** (wrong)")
        self.assertEqual(cc.mark(reject, {"error": "x"}), "error")
        self.assertEqual(cc.mark(reject, None), "not run")


if __name__ == "__main__":
    unittest.main()
