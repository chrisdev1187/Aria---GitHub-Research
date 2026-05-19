"""
Quick test: run intake + decomposer only, print results.
Usage: python test_decomposer.py
"""
import asyncio
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.intake import IntakeAgent
from agents.decomposer import DecomposerAgent

IDEA = (
    "build an AI tool that analyzes system prompts, gives insights to the user, "
    "and connects to a database of leaked system prompts to guide the user to "
    "write a master system prompt"
)

async def main():
    print("=" * 60)
    print("IDEA:", IDEA)
    print("=" * 60)

    print("\n[1/2] Running Intake Agent...")
    intake = IntakeAgent()
    intake_result = await intake.run(IDEA)
    print("\nINTAKE OUTPUT:")
    print(json.dumps(intake_result, indent=2))

    print("\n[2/2] Running Decomposer Agent...")
    decomposer = DecomposerAgent()
    decomp_result = await decomposer.run(intake_result)

    # Normalise output
    if isinstance(decomp_result, dict):
        sub_problems = decomp_result.get("sub_problems", list(decomp_result.values()))
    else:
        sub_problems = decomp_result

    print("\nDECOMPOSER OUTPUT:")
    for sp in sub_problems:
        print(f"\n  {sp.get('id')} — {sp.get('title')}")
        print(f"  core_problem_ref: {sp.get('core_problem_ref', '')}")
        print(f"  github_search_queries:")
        for q in sp.get("github_search_queries", []):
            print(f"    - {q}")

    print("\n" + "=" * 60)
    print("VERDICT:")
    print(f"  sub-problems generated: {len(sub_problems)}")
    for sp in sub_problems:
        queries = sp.get("github_search_queries", [])
        generic = [q for q in queries if not any(
            kw in q.lower() for kw in ["leaked", "system prompt", "prompt builder", "rag", "prompt analysis", "prompt dataset", "prompt collection", "llm prompt"]
        )]
        status = "OK" if not generic else f"GENERIC QUERIES: {generic}"
        print(f"  {sp.get('id')}: {status}")

asyncio.run(main())
