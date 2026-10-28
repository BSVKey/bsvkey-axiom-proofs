"""Offline tests for the proof receipt tool. No network, no AXLE."""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))

import proof_receipt as pr  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def fake_result(i: int, okay: bool = True) -> dict:
    return {
        "file": f"proofs/{i:02d}_example.lean",
        "source_sha256": f"{i:064x}",
        "statement_sha256": f"{i + 1000:064x}",
        "theorems": [f"t{i}"],
        "environment": "lean-4.35.0",
        "checker": "AXLE verify_proof",
        "okay": okay,
        "checked_at": "2026-10-28T00:00:00Z",
    }


class MerkleTests(unittest.TestCase):
    def test_every_leaf_climbs_to_root(self):
        for n in range(1, 18):
            leaves = [pr.sha256(bytes([i])) for i in range(n)]
            levels = pr.merkle_levels(leaves)
            root = levels[-1][0]
            for i, leaf in enumerate(leaves):
                self.assertEqual(pr.climb(leaf, pr.inclusion_path(levels, i)), root, (n, i))

    def test_wrong_leaf_does_not_climb(self):
        leaves = [pr.sha256(bytes([i])) for i in range(5)]
        levels = pr.merkle_levels(leaves)
        path = pr.inclusion_path(levels, 2)
        self.assertNotEqual(pr.climb(pr.sha256(b"forged"), path), levels[-1][0])

    def test_odd_level_not_duplicated(self):
        # [a, b, c] and [a, b, c, c] must have different roots.
        a, b, c = (pr.sha256(x) for x in (b"a", b"b", b"c"))
        self.assertNotEqual(pr.merkle_levels([a, b, c])[-1][0], pr.merkle_levels([a, b, c, c])[-1][0])

    def test_leaf_and_node_are_domain_separated(self):
        x, y = pr.sha256(b"x"), pr.sha256(b"y")
        self.assertNotEqual(pr.node_hash(x, y), pr.sha256(x + y))


class ScriptTests(unittest.TestCase):
    def test_op_return_roundtrip(self):
        root = pr.sha256(b"root")
        script = pr.op_return_script(root)
        self.assertEqual(script[:2], b"\x00\x6a")
        self.assertEqual(pr.parse_op_return(script), root)

    def test_other_scripts_ignored(self):
        self.assertIsNone(pr.parse_op_return(bytes.fromhex("76a914" + "00" * 20 + "88ac")))
        self.assertIsNone(pr.parse_op_return(b"\x00\x6a" + pr.push_data(b"other.tag") + pr.push_data(b"\x00" * 32)))


class BatchTests(unittest.TestCase):
    def test_failed_results_are_not_receipted(self):
        batch = pr.build_batch([fake_result(1), fake_result(2, okay=False), fake_result(3)])
        files = [e["receipt"]["file"] for e in batch["receipts"]]
        self.assertEqual(files, ["proofs/01_example.lean", "proofs/03_example.lean"])

    def test_receipt_change_changes_root(self):
        a = pr.build_batch([fake_result(1), fake_result(2)])
        changed = fake_result(2)
        changed["theorems"] = ["t2", "extra"]
        b = pr.build_batch([fake_result(1), changed])
        self.assertNotEqual(a["merkle_root"], b["merkle_root"])

    def test_canonical_json_is_order_independent(self):
        self.assertEqual(pr.canonical({"b": 1, "a": 2}), pr.canonical({"a": 2, "b": 1}))


class FileVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proof = pathlib.Path(self.tmp.name) / "99_demo.lean"
        self.proof.write_bytes(b"theorem demo : 1 + 1 = 2 := rfl\n")
        result = fake_result(99)
        result["file"] = "proofs/99_demo.lean"
        result["source_sha256"] = pr.source_sha256(self.proof)
        self.batch = pr.build_batch([fake_result(1), result, fake_result(2)])

    def tearDown(self):
        self.tmp.cleanup()

    def test_untouched_file_passes(self):
        self.assertEqual(pr.verify_file(self.batch, self.proof), [])

    def test_crlf_and_bom_do_not_matter(self):
        self.proof.write_bytes(b"\xef\xbb\xbftheorem demo : 1 + 1 = 2 := rfl\r\n")
        self.assertEqual(pr.verify_file(self.batch, self.proof), [])

    def test_edited_file_fails(self):
        self.proof.write_bytes(b"theorem demo : 1 + 1 = 3 := sorry\n")
        problems = pr.verify_file(self.batch, self.proof)
        self.assertTrue(any("hash mismatch" in p for p in problems))

    def test_tampered_path_fails(self):
        entry = next(e for e in self.batch["receipts"] if e["receipt"]["file"] == "proofs/99_demo.lean")
        entry["path"][0]["hash"] = "00" * 32
        self.assertTrue(any("Merkle root" in p for p in pr.verify_file(self.batch, self.proof)))


class CommittedBatchTests(unittest.TestCase):
    """The committed receipts/batch.json must match the committed proofs."""

    def test_committed_batch_matches_proofs(self):
        batch_path = ROOT / "receipts" / "batch.json"
        if not batch_path.exists():
            self.skipTest("no committed batch yet")
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        proofs = sorted((ROOT / "proofs").glob("*.lean"))
        self.assertEqual(len(batch["receipts"]), len(proofs))
        for proof in proofs:
            self.assertEqual(pr.verify_file(batch, proof), [], proof.name)


if __name__ == "__main__":
    unittest.main()
