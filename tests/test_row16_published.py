"""Offline: the broker's published charge formula agrees with row 16's Lean model."""

import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Row16PublishedFormulaTests(unittest.TestCase):
    def test_published_formula_matches_lean_model(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        run = subprocess.run([node, str(ROOT / "tools" / "row16_published.mjs")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
