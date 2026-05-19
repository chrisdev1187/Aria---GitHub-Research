"""
Test decomposer on the ARIA self-research idea.
Verifies queries target implementation tech, not circular tool descriptions.
"""
import asyncio, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from agents.intake import IntakeAgent
from agents.decomposer import DecomposerAgent

IDEA = (
    "build a multi-agent AI research pipeline called ARIA that takes a software idea, "
    "decomposes it into sub-problems, searches GitHub and the web in parallel for relevant "
    "repos and articles, deep-dives into real source code, extracts architectural patterns "
    "and copy-paste-ready libraries, synthesizes a structured research brief, judges its "
    "quality and re-researches gaps automatically, then packages everything into a knowledge "
    "folder ready to feed to any coding AI"
)

# Known circular/bad query fragments that must NOT appear
BAD_FRAGMENTS = [
    "software idea decomposition library",
    "decomposing software ideas",
    "research pipeline tool",
    "research brief generator",
    "automated github research tool",
    "automated research",
    "knowledge folder",
    "coding ai integration",
]

# At least these implementation-tech anchors must appear across all queries
GOOD_ANCHORS = [
    "asyncio", "async", "github api", "pygithub", "openai", "rate limit",
    "provider", "fallback", "circuit", "markdown", "pydantic", "orchestrat",
    "llm", "agent workflow", "parallel", "semaphore", "key rotation",
]

async def main():
    print("Running intake...")
    intake = IntakeAgent()
    intake_result = await intake.run(IDEA)
    print(f"  ideal_outcome: {intake_result.get('ideal_outcome','')[:100]}")
    print(f"  core_problems: {len(intake_result.get('core_problems', []))}")

    print("\nRunning decomposer...")
    decomp = DecomposerAgent()
    sps = await decomp.run(intake_result)
    print(f"  sub-problems generated: {len(sps)}")

    print("\nSUB-PROBLEM QUERIES:")
    all_queries = []
    for sp in sps:
        queries = sp.get("github_search_queries", [])
        all_queries.extend(queries)
        print(f"\n  {sp['id']}: {sp['title']}")
        for q in queries:
            print(f"    - {q}")

    print("\nCHECKS:")

    # 1. No circular queries
    circular_found = []
    for q in all_queries:
        for bad in BAD_FRAGMENTS:
            if bad.lower() in q.lower():
                circular_found.append(f"'{q}' contains '{bad}'")
    print(f"  No circular queries: {'PASS' if not circular_found else 'FAIL'}")
    for c in circular_found[:5]:
        print(f"    BAD: {c}")

    # 2. Implementation anchors present across the query set
    all_queries_lower = " ".join(all_queries).lower()
    found_anchors = [a for a in GOOD_ANCHORS if a.lower() in all_queries_lower]
    missing_anchors = [a for a in GOOD_ANCHORS if a.lower() not in all_queries_lower]
    anchor_pass = len(found_anchors) >= 5
    print(f"  Implementation anchors present ({len(found_anchors)}/{len(GOOD_ANCHORS)}): {'PASS' if anchor_pass else 'FAIL'}")
    if found_anchors:
        print(f"    Found: {found_anchors}")
    if missing_anchors:
        print(f"    Missing: {missing_anchors}")

    # 3. Reasonable count
    count_pass = 4 <= len(sps) <= 12
    print(f"  SP count {len(sps)} in range 4-12: {'PASS' if count_pass else 'FAIL'}")

asyncio.run(main())
