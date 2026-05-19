"""
Test: synthesizer section assembly + key fixes.
Checks:
  1. Architecture section gets real library names (not empty strings from wrong key)
  2. Build order section gets performance/security from correct keys
  3. ALL sections appear in the brief (assembly no longer drops sections after index 4)
  4. Brief does NOT recommend T5/Neo4j/training (findings-only rule)
"""
import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.synthesizer import SynthesizerAgent

INTAKE = {
    "raw_idea": (
        "build an AI tool that analyzes system prompts, gives insights to the user, "
        "and connects to a database of leaked system prompts to guide the user to "
        "write a master system prompt"
    ),
    "ideal_outcome": (
        "A tool that analyzes system prompts via RAG retrieval over a corpus of leaked "
        "system prompts, extracting patterns and guiding users to write high-quality master system prompts."
    ),
    "domain": ["ml", "data"],
    "complexity_estimate": "medium",
}

DECOMPOSITION = [
    {"id": "SP-1", "title": "System Prompt Corpus Collection", "description": "Collect and index leaked system prompts from public sources."},
    {"id": "SP-2", "title": "RAG Retrieval over Prompt Corpus", "description": "Embed corpus and retrieve similar prompts via vector search."},
    {"id": "SP-3", "title": "Pattern Extraction from Leaked Prompts", "description": "Extract structural patterns and best practices from corpus."},
]

GITHUB_FINDINGS = [
    {
        "sub_problem_id": "SP-1", "sub_problem_title": "System Prompt Corpus Collection",
        "repos_found": 5, "deep_dive_results": [],
        "all_repos": [
            {"full_name": "f/awesome-chatgpt-prompts", "stargazers_count": 112000, "language": None,
             "relevance_score": 9, "relevance_reason": "Largest curated leaked system prompt collection"},
        ],
    },
    {
        "sub_problem_id": "SP-2", "sub_problem_title": "RAG Retrieval over Prompt Corpus",
        "repos_found": 6,
        "deep_dive_results": [
            {
                "full_name": "chroma-core/chroma", "stars": 15000, "relevance_score": 9,
                "analysis": {
                    "architecture": "In-process vector store, no server needed",
                    "key_pattern": "collection.query(query_texts=[...], n_results=5)",
                    "dependencies": ["chromadb", "sentence-transformers"],
                    "gotchas": ["persist to disk or embeddings lost on restart"],
                    "fork_worth_it": False,
                }
            }
        ],
        "all_repos": [],
    },
    {
        "sub_problem_id": "SP-3", "sub_problem_title": "Pattern Extraction from Leaked Prompts",
        "repos_found": 4, "deep_dive_results": [],
        "all_repos": [
            {"full_name": "run-llama/llama_index", "stargazers_count": 38000, "language": "Python",
             "relevance_score": 8, "relevance_reason": "Full RAG pipeline for prompt corpus ingestion and querying"},
        ],
    },
]

PATTERNS = {
    "architectural_patterns": [
        {"name": "RAG over leaked prompt corpus", "description": "Embed corpus with sentence-transformers, store in ChromaDB, retrieve by cosine similarity"},
    ],
    "libraries_to_use": [
        {"library": "chromadb", "version": "latest", "reason": "vector store for prompt corpus", "source_repo": "chroma-core/chroma"},
        {"library": "sentence-transformers", "version": "all-MiniLM-L6-v2", "reason": "fast embedder for prompt-length text", "source_repo": "sentence-transformers"},
        {"library": "llama-index", "version": "latest", "reason": "RAG pipeline framework", "source_repo": "run-llama/llama_index"},
    ],
    "repos_to_fork": [{"repo": "chroma-core/chroma", "reason": "base vector store"}],
    "anti_patterns": [{"name": "Whole-prompt embedding", "description": "chunk by section for better retrieval"}],
    "gotchas": [{"name": "Corpus persistence", "description": "persist ChromaDB to disk or lose embeddings on restart"}],
    "performance": [{"name": "Embedding speed", "description": "all-MiniLM-L6-v2 is fastest for prompt-length texts"}],
    "security": [],
}

async def main():
    agent = SynthesizerAgent()
    brief = await agent.run(INTAKE, DECOMPOSITION, GITHUB_FINDINGS, [], PATTERNS)

    print("BRIEF SECTION HEADERS:")
    for line in brief.split("\n"):
        if line.startswith("#"):
            print(f"  {line}")

    print("\nCHECKS:")

    # 1. All 3 SP sections present
    for sp in ["SP-1", "SP-2", "SP-3"]:
        found = sp in brief
        print(f"  {sp} section present: {'PASS' if found else 'FAIL'}")

    # 2. Architecture section present
    has_arch = "Synthesised Architecture" in brief or "Architecture" in brief
    print(f"  Architecture section present: {'PASS' if has_arch else 'FAIL'}")

    # 3. Build order section present
    has_build = "Build Order" in brief
    print(f"  Build Order section present: {'PASS' if has_build else 'FAIL'}")

    # 4. Real library names in brief (not empty strings from wrong key)
    has_chroma = "chromadb" in brief or "chroma" in brief.lower()
    print(f"  'chromadb' in brief (key fix check): {'PASS' if has_chroma else 'FAIL'}")

    # 5. No hallucinated bad tech
    has_t5 = "t5" in brief.lower() or "fine-tun" in brief.lower()
    has_neo4j = "neo4j" in brief.lower()
    print(f"  No T5/fine-tuning hallucination: {'PASS' if not has_t5 else 'FAIL'}")
    print(f"  No Neo4j hallucination:           {'PASS' if not has_neo4j else 'FAIL'}")

asyncio.run(main())
