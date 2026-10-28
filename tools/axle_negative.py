"""Negative controls: AXLE must REJECT every file in negative/.

Passes only if each file fails verification. For the buggy price rule it also
asks AXLE's `disprove` to prove the claim false, which shows the checker
finding a real pricing bug rather than just failing to compile.

NO PRIVACY: the Lean source is sent to Axiom's cloud in plain text.
"""

import asyncio
import os
import pathlib
import sys

from axle import AxleClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEGATIVE = ROOT / "negative"
ENVIRONMENT = os.environ.get("AXLE_ENVIRONMENT", "lean-4.35.0")


async def main() -> int:
    bad = 0
    async with AxleClient(api_key=os.environ.get("AXLE_API_KEY")) as client:
        for path in sorted(NEGATIVE.glob("*.lean")):
            content = path.read_text(encoding="utf-8-sig")
            statement = await client.theorem2sorry(content=content, environment=ENVIRONMENT)
            result = await client.verify_proof(
                formal_statement=statement.content, content=content, environment=ENVIRONMENT,
            )
            if result.okay:
                bad += 1
                print(f"WRONG  {path.name}: AXLE accepted a file it should reject")
            else:
                print(f"OK     {path.name}: rejected as expected")
            if path.name.startswith("buggy_"):
                dis = await client.disprove(content=content, environment=ENVIRONMENT)
                found = bool(dis.disproved_theorems)
                print(f"       disprove: {'counterexample found for ' + ', '.join(dis.disproved_theorems) if found else 'no counterexample found'}")
                if not found:
                    bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
