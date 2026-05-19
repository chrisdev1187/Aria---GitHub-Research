"""
Test: KnowledgePackagerAgent — verify all tabs produce non-empty content.
Uses the same fixtures as test_synthesizer.py.
"""
import os
import sys
import tempfile
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.knowledge_packager import KnowledgePackagerAgent

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
    "primary_language": "Python",
    "core_problems": [
        "Collect and index leaked system prompts from public sources",
        "Embed corpus and retrieve similar prompts via vector search",
        "Extract structural patterns and best practices from corpus",
    ],
}

DECOMPOSITION = [
    {"id": "SP-1", "title": "System Prompt Corpus Collection", "description": "Collect and index leaked system prompts.",
     "why_critical": "Corpus is the foundation of the RAG system.", "github_search_queries": ["leaked system prompts dataset python"]},
    {"id": "SP-2", "title": "RAG Retrieval over Prompt Corpus", "description": "Embed and retrieve similar prompts.",
     "why_critical": "Core retrieval mechanism.", "github_search_queries": ["rag system prompt retrieval chroma python"]},
    {"id": "SP-3", "title": "Pattern Extraction", "description": "Extract structural patterns from corpus.",
     "why_critical": "Drives the insight generation.", "github_search_queries": ["system prompt pattern extraction llm"]},
]

WEB_RESULTS = [
    {
        "sub_problem_id": "SP-1", "sub_problem_title": "System Prompt Corpus Collection",
        "results_count": 3,
        "results": [
            {"title": "awesome-chatgpt-prompts", "url": "https://github.com/f/awesome-chatgpt-prompts",
             "snippet": "112k stars, largest curated leaked system prompt collection"},
        ],
    },
]

PATTERNS = {
    "architectural_patterns": [
        {"name": "RAG over leaked prompt corpus", "description": "Embed corpus with sentence-transformers, store in ChromaDB, retrieve by cosine similarity"},
    ],
    "libraries_to_use": [
        {"library": "chromadb", "version": "latest", "reason": "vector store for prompt corpus", "source_repo": "chroma-core/chroma"},
        {"library": "sentence-transformers", "version": "all-MiniLM-L6-v2", "reason": "fast embedder", "source_repo": "sentence-transformers/sentence-transformers"},
        {"library": "llama-index", "version": "latest", "reason": "RAG pipeline framework", "source_repo": "run-llama/llama_index"},
    ],
    "repos_to_fork": [{"repo": "chroma-core/chroma", "reason": "base vector store"}],
    "anti_patterns": [{"name": "Whole-prompt embedding", "description": "chunk by section for better retrieval"}],
    "gotchas": [{"name": "Corpus persistence", "description": "persist ChromaDB to disk or lose embeddings on restart"}],
    "performance": [{"name": "Embedding speed", "description": "all-MiniLM-L6-v2 is fastest for prompt-length texts"}],
    "security": [],
}

BRIEF = """# ARIA Research Brief

**Idea:** Build a RAG-powered system prompt analyzer.
**Ideal Outcome:** RAG retrieval over leaked system prompts corpus.

## Executive Summary
Build using ChromaDB + sentence-transformers for RAG retrieval.

## Build Order & Risks
Phase 1: Ingest corpus into ChromaDB
Phase 2: Build retrieval layer
Phase 3: Wire to prompt builder
"""


def main():
    agent = KnowledgePackagerAgent()

    with tempfile.TemporaryDirectory() as tmpdir:
        result = agent.run(
            intake_result=INTAKE,
            decomposer_result=DECOMPOSITION,
            web_results=WEB_RESULTS,
            pattern_result=PATTERNS,
            brief=BRIEF,
            output_dir=tmpdir,
            run_id="test-run-001",
        )

        print(f"Status: {result['status']}")
        if result.get("error"):
            print(f"ERROR: {result['error']}")

        pkg = result["package_dir"]
        print(f"\nPackage dir: {pkg}")
        print(f"Sections created: {result['sections_created']}")

        expected_files = [
            ("README.md",            ["ARIA Knowledge Package", "RAG retrieval"]),
            ("00_PROBLEM.md",        ["Problem Statement", "RAG retrieval", "Collect and index leaked"]),
            ("01_DECOMPOSITION.md",  ["SP-1", "SP-2", "SP-3", "leaked system prompts dataset python"]),
            ("02_TOP_REPOS.md",      ["chroma-core/chroma"]),
            ("04_PATTERNS.md",       ["RAG over leaked prompt corpus"]),
            ("05_LIBRARIES.md",      ["chromadb", "sentence-transformers", "chroma-core/chroma"]),
            ("06_BUILD_PLAN.md",     ["ChromaDB", "Phase"]),
            ("07_WEB_RESEARCH.md",   ["SP-1", "awesome-chatgpt-prompts"]),
            ("08_RISKS.md",          ["Whole-prompt embedding", "Corpus persistence", "all-MiniLM-L6-v2 is fastest"]),
            ("ARIA_research_brief.md", ["ARIA Research Brief"]),
        ]

        print("\nCHECKS:")
        all_pass = True
        for filename, expected_strings in expected_files:
            filepath = os.path.join(pkg, filename)
            if not os.path.exists(filepath):
                print(f"  FAIL — {filename}: file missing")
                all_pass = False
                continue

            content = open(filepath, encoding="utf-8").read()
            if len(content.strip()) < 50:
                print(f"  FAIL — {filename}: too short ({len(content)} chars)")
                all_pass = False
                continue

            missing = [s for s in expected_strings if s.lower() not in content.lower()]
            if missing:
                print(f"  FAIL — {filename}: missing {missing}")
                all_pass = False
            else:
                print(f"  PASS — {filename}")

        print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")


if __name__ == "__main__":
    main()
