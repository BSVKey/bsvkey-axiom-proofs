"""Send every proof in proofs/ to AXLE (Axiom Lean Engine) and record the result.

For each file AXLE first turns every proof into `sorry` (theorem2sorry), which
gives the bare statements. It then checks the original file against those
statements (verify_proof), which fails on any `sorry`, any error, or any
non-standard axiom. One JSON result per file lands in results/.

NO PRIVACY: the full Lean source is sent to Axiom's cloud in plain text.

Usage:
    python tools/axle_verify.py               # all proofs
    python tools/axle_verify.py 01 04         # only files whose name starts with these
Set AXLE_API_KEY for higher rate limits (optional).
"""

import asyncio
import datetime
import hashlib
import importlib.metadata
import json
import os
import pathlib
import sys

from axle import AxleApiError, AxleClient

import lean_guard

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOFS = pathlib.Path(os.environ.get("AXLE_PROOFS_DIR", ROOT / "proofs")).resolve()
RESULTS = pathlib.Path(os.environ.get("AXLE_RESULTS_DIR", ROOT / "results")).resolve()
ENVIRONMENT = os.environ.get("AXLE_ENVIRONMENT", "lean-4.35.0")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_source(path: pathlib.Path) -> bytes:
    """File bytes as hashed and sent: no BOM, LF line endings."""
    return path.read_bytes().removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")


async def verify_one(client: AxleClient, limit: asyncio.Semaphore, path: pathlib.Path) -> dict:
    raw = canonical_source(path)
    content = raw.decode("utf-8")
    theorems = sorted({
        line.split()[1]
        for line in content.splitlines()
        if line.startswith("theorem ")
    })
    report = {
        "file": path.relative_to(PROOFS.parent).as_posix(),
        "source_sha256": sha256_hex(raw),
        "statement_sha256": None,
        "theorems": theorems,
        "environment": ENVIRONMENT,
        "checker": "AXLE verify_proof",
        "axle_client": importlib.metadata.version("axiom-axle"),
        "okay": False,
        "failed_declarations": [],
        "errors": [],
    }
    refused = lean_guard.check_source(content)
    if refused:
        report["errors"] = ["lean_guard refused the file (not sent to AXLE): " + "; ".join(refused)]
        report["checked_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return report
    async with limit:
        try:
            statement = await client.theorem2sorry(content=content, environment=ENVIRONMENT)
            result = await client.verify_proof(
                formal_statement=statement.content,
                content=content,
                environment=ENVIRONMENT,
            )
        except AxleApiError as e:
            report["errors"] = [f"{type(e).__name__}: {e}"]
        else:
            report["statement_sha256"] = sha256_hex(statement.content.encode("utf-8"))
            report["okay"] = result.okay
            report["failed_declarations"] = result.failed_declarations
            report["errors"] = result.lean_messages.errors + result.tool_messages.errors
    report["checked_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return report


async def main(prefixes: list[str]) -> int:
    files = sorted(p for p in PROOFS.rglob("*.lean") if ".lake" not in p.parts)
    if prefixes:
        files = [f for f in files if any(f.name.startswith(p) for p in prefixes)]
    RESULTS.mkdir(exist_ok=True)
    failed = 0
    # Anonymous AXLE use allows only a few requests at once; stay well under it.
    limit = asyncio.Semaphore(int(os.environ.get("AXLE_PARALLEL", "2")))
    async with AxleClient(api_key=os.environ.get("AXLE_API_KEY")) as client:
        reports = await asyncio.gather(*(verify_one(client, limit, f) for f in files))
    for path, report in zip(files, reports):
        out = RESULTS / (path.relative_to(PROOFS).with_suffix("").as_posix().replace("/", "__") + ".json")
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        mark = "PASS" if report["okay"] else "FAIL"
        print(f"{mark}  {path.name}  ({len(report['theorems'])} theorems)")
        if not report["okay"]:
            failed += 1
            for err in report["errors"]:
                print("      " + err.replace("\n", "\n      "))
    print(f"\n{len(files) - failed}/{len(files)} proof files verified by AXLE ({ENVIRONMENT})")
    write_step_summary(reports, failed)
    return 1 if failed else 0


def write_step_summary(reports: list[dict], failed: int) -> None:
    """Markdown table for the GitHub Actions job page, when running in Actions."""
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    rows = [
        f"| {'✅' if r['okay'] else '❌'} | `{r['file']}` | {len(r['theorems'])} | `{r['source_sha256'][:12]}` |"
        for r in reports
    ]
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(f"### AXLE proof check: {len(reports) - failed}/{len(reports)} files verified ({ENVIRONMENT})\n\n")
        fh.write("| | File | Theorems | SHA-256 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n")
        fh.write("Files are checked by plain-Lean guard first, then sent in plain text to Axiom's AXLE.\n")


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
