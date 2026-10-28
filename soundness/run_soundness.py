"""Run the adversarial soundness cases against AXLE verify_proof.

A case PASSES when AXLE does what a sound checker must: rejects every cheat
and accepts every honest control. Writes soundness/results.json.

NO PRIVACY: every case is sent to Axiom's cloud in plain text.
"""

import asyncio
import json
import os
import pathlib
import sys

from axle import AxleApiError, AxleClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cases import CASES  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ENVIRONMENT = os.environ.get("AXLE_ENVIRONMENT", "lean-4.35.0")


async def run_case(client, limit, case):
    async with limit:
        try:
            r = await client.verify_proof(
                formal_statement=case["statement"], content=case["content"], environment=ENVIRONMENT,
            )
            okay, why = r.okay, (r.lean_messages.errors + r.tool_messages.errors)[:3]
        except AxleApiError as e:
            okay, why = False, [f"{type(e).__name__}: {e}"]
    accepted = bool(okay)
    sound = accepted == (case["expect"] == "accept")
    return {"name": case["name"], "expect": case["expect"], "accepted": accepted, "sound": sound,
            "known_issue": case.get("known_issue", False), "reason": [w[:400] for w in why]}


async def main():
    limit = asyncio.Semaphore(2)
    async with AxleClient(api_key=os.environ.get("AXLE_API_KEY")) as client:
        rows = await asyncio.gather(*(run_case(client, limit, c) for c in CASES))
    (HERE / "results.json").write_text(json.dumps(
        {"environment": ENVIRONMENT, "cases": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in rows:
        if r["sound"]:
            mark = "FIXED" if r["known_issue"] else "OK   "
        else:
            mark = "KNOWN" if r["known_issue"] else "HOLE "
        print(f"{mark} {r['name']:<30} expect={r['expect']:<6} accepted={r['accepted']}")
        if r["expect"] == "reject" and not r["accepted"]:
            for w in r["reason"][:1]:
                print("       " + w.splitlines()[0][:150])
    holes = [r["name"] for r in rows if not r["sound"]]
    new_holes = [r["name"] for r in rows if not r["sound"] and not r["known_issue"]]
    print(f"\n{len(rows) - len(holes)}/{len(rows)} cases handled soundly")
    if holes:
        print(f"AXLE accepted {len(holes)} proof(s) of False: {holes}. See ADVISORY.md.")
    # Fail CI only on a hole that is not already documented in ADVISORY.md.
    return 1 if new_holes else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main()))
