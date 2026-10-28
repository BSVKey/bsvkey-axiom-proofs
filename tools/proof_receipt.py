"""BSVKey proof receipts: batch AXLE results under one Merkle root for Bitcoin BSV.

    python tools/proof_receipt.py build
        Reads results/*.json (from axle_verify.py). Every passing file becomes a
        receipt leaf. Writes receipts/batch.json with the Merkle root, each
        receipt's inclusion path, and the OP_RETURN output script to anchor.

    python tools/proof_receipt.py verify proofs/01_payment_channel.lean [--txid TXID]
        Re-hashes the proof file, finds its receipt, climbs the inclusion path
        to the root, and (with --txid) checks the root is in that transaction's
        OP_RETURN on Bitcoin BSV mainnet via WhatsOnChain.

This tool never signs or broadcasts. Anchoring means paying for one
transaction with the script printed by `build`, from a wallet you control.

NO PRIVACY: receipts, roots and OP_RETURN data are public. They hold hashes
of the proof files, and the proof files themselves are public in this repo.
"""

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
BATCH = ROOT / "receipts" / "batch.json"

SCHEMA = "bsvkey.proof-receipt/1"
TAG = b"bsvkey.proof"
RECEIPT_FIELDS = (
    "file", "source_sha256", "statement_sha256", "theorems",
    "environment", "checker", "okay", "checked_at",
)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# Domain separated hashes, as in proofs/10_merkle_batch.lean: a leaf can never
# be mistaken for an inner node.
def leaf_hash(receipt: dict) -> bytes:
    return sha256(b"\x00" + canonical(receipt))


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha256(b"\x01" + left + right)


def merkle_levels(leaves: list[bytes]) -> list[list[bytes]]:
    """All tree levels, leaves first. An odd last node is carried up unpaired
    (never duplicated), so no two different leaf lists share a root."""
    if not leaves:
        raise ValueError("no leaves")
    levels = [leaves]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt = [node_hash(cur[i], cur[i + 1]) for i in range(0, len(cur) - 1, 2)]
        if len(cur) % 2:
            nxt.append(cur[-1])
        levels.append(nxt)
    return levels


def inclusion_path(levels: list[list[bytes]], index: int) -> list[dict]:
    """Sibling hashes from leaf to root; side says where the sibling sits."""
    path = []
    for level in levels[:-1]:
        sib = index ^ 1
        if sib < len(level):
            path.append({"side": "left" if sib < index else "right", "hash": level[sib].hex()})
        index //= 2
    return path


def climb(h: bytes, path: list[dict]) -> bytes:
    for step in path:
        sib = bytes.fromhex(step["hash"])
        h = node_hash(sib, h) if step["side"] == "left" else node_hash(h, sib)
    return h


def push_data(data: bytes) -> bytes:
    if len(data) < 0x4C:
        return bytes([len(data)]) + data
    if len(data) <= 0xFF:
        return b"\x4c" + bytes([len(data)]) + data
    raise ValueError("push too large for this tool")


def op_return_script(root: bytes) -> bytes:
    """OP_FALSE OP_RETURN <"bsvkey.proof"> <32-byte Merkle root>"""
    return b"\x00\x6a" + push_data(TAG) + push_data(root)


def parse_op_return(script: bytes) -> bytes | None:
    """Return the root if `script` is a bsvkey.proof OP_RETURN, else None."""
    prefix = b"\x00\x6a" + push_data(TAG)
    if script.startswith(prefix) and len(script) == len(prefix) + 33 and script[len(prefix)] == 32:
        return script[len(prefix) + 1:]
    return None


def receipt_from_result(result: dict) -> dict:
    receipt = {k: result[k] for k in RECEIPT_FIELDS}
    receipt["schema"] = SCHEMA
    return receipt


def build_batch(results: list[dict]) -> dict:
    receipts = sorted(
        (receipt_from_result(r) for r in results if r.get("okay")),
        key=lambda r: r["file"],
    )
    leaves = [leaf_hash(r) for r in receipts]
    levels = merkle_levels(leaves)
    root = levels[-1][0]
    return {
        "schema": "bsvkey.proof-batch/1",
        "merkle_root": root.hex(),
        "op_return_script_hex": op_return_script(root).hex(),
        "anchor_txid": None,
        "receipts": [
            {"receipt": r, "leaf": leaves[i].hex(), "path": inclusion_path(levels, i)}
            for i, r in enumerate(receipts)
        ],
    }


def source_sha256(path: pathlib.Path) -> str:
    raw = path.read_bytes().removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def verify_file(batch: dict, proof: pathlib.Path) -> list[str]:
    """Return a list of problems; empty means the file matches the batch."""
    name = f"proofs/{proof.name}"
    entry = next((e for e in batch["receipts"] if e["receipt"]["file"] == name), None)
    if entry is None:
        return [f"{name}: no receipt in this batch"]
    problems = []
    if source_sha256(proof) != entry["receipt"]["source_sha256"]:
        problems.append(f"{name}: file changed since it was checked (hash mismatch)")
    leaf = leaf_hash(entry["receipt"])
    if leaf.hex() != entry["leaf"]:
        problems.append(f"{name}: receipt does not match its leaf hash")
    if climb(leaf, entry["path"]).hex() != batch["merkle_root"]:
        problems.append(f"{name}: inclusion path does not reach the Merkle root")
    return problems


def fetch_tx_scripts(txid: str) -> list[bytes]:
    url = f"https://api.whatsonchain.com/v1/bsv/main/tx/hash/{txid}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        tx = json.load(resp)
    return [bytes.fromhex(v["scriptPubKey"]["hex"]) for v in tx["vout"]]


def cmd_build(_args) -> int:
    results = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS.glob("*.json"))]
    failed = [r["file"] for r in results if not r.get("okay")]
    if failed:
        print("Not building: these files did not pass AXLE: " + ", ".join(failed))
        return 1
    batch = build_batch(results)
    BATCH.parent.mkdir(exist_ok=True)
    BATCH.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
    print(f"{len(batch['receipts'])} receipts -> {BATCH.relative_to(ROOT)}")
    print(f"Merkle root:      {batch['merkle_root']}")
    print(f"OP_RETURN script: {batch['op_return_script_hex']}")
    return 0


def cmd_verify(args) -> int:
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    problems = verify_file(batch, pathlib.Path(args.proof))
    if args.txid:
        roots = [parse_op_return(s) for s in fetch_tx_scripts(args.txid)]
        if bytes.fromhex(batch["merkle_root"]) not in roots:
            problems.append(f"transaction {args.txid} does not carry this batch's Merkle root")
    for p in problems:
        print("FAIL  " + p)
    if not problems:
        where = f" and anchored in {args.txid}" if args.txid else " (not checked on-chain: no --txid)"
        print(f"PASS  {args.proof} matches its AXLE receipt{where}")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    v = sub.add_parser("verify")
    v.add_argument("proof")
    v.add_argument("--txid")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
