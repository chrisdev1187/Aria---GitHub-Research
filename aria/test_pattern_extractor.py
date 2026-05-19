"""
Test: pattern extractor with idea context + realistic good repos.
Simulates what SP-2 (leaked prompt retrieval) findings look like after the scorer fix.
"""
import asyncio
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.pattern_extractor import PatternExtractorAgent

INTAKE = {
    "raw_idea": (
        "build an AI tool that analyzes system prompts, gives insights to the user, "
        "and connects to a database of leaked system prompts to guide the user to "
        "write a master system prompt"
    ),
    "ideal_outcome": (
        "A tool that analyzes system prompts, extracts insights from a corpus of leaked "
        "system prompts via RAG retrieval, and guides users in writing high-quality "
        "master system prompts."
    ),
}

# Simulate realistic findings post scorer-fix — domain-relevant repos
GITHUB_FINDINGS = [
    {
        "sub_problem_id": "SP-1",
        "sub_problem_title": "System Prompt Analysis Engine",
        "repos_found": 8,
        "deep_dive_results": [
            {
                "full_name": "brainlid/langchain",
                "stars": 1200,
                "relevance_score": 8,
                "analysis": {
                    "architecture": "Elixir LangChain port — chains prompts together with structured output parsing. Prompt template system is standalone.",
                    "key_pattern": "Prompt template + variable injection with schema validation before LLM call",
                    "code_snippet": "chain = LLMChain.new(llm: model, prompt: prompt_template)\nresult = LLMChain.run(chain, input_vars)",
                    "dependencies": ["langchain", "openai", "anthropic"],
                    "gotchas": ["Prompt injection possible if user input not sanitised before template fill"],
                }
            }
        ],
        "all_repos": [
            {"full_name": "brainlid/langchain", "stargazers_count": 1200, "language": "Elixir", "relevance_score": 8, "relevance_reason": "Prompt chaining library directly useful for system prompt analysis pipeline"},
            {"full_name": "f/awesome-chatgpt-prompts", "stargazers_count": 112000, "language": None, "relevance_score": 9, "relevance_reason": "Largest curated collection of system prompts — ideal corpus for the leaked prompts database"},
        ],
    },
    {
        "sub_problem_id": "SP-2",
        "sub_problem_title": "Leaked Prompt Database Retrieval",
        "repos_found": 7,
        "deep_dive_results": [
            {
                "full_name": "chroma-core/chroma",
                "stars": 15000,
                "relevance_score": 9,
                "analysis": {
                    "architecture": "Embedded vector store — runs in-process, no server needed. Stores embeddings + metadata, retrieves by cosine similarity.",
                    "key_pattern": "collection.add(documents=[...], embeddings=[...], ids=[...]) then collection.query(query_embeddings=..., n_results=5)",
                    "code_snippet": "import chromadb\nclient = chromadb.Client()\ncollection = client.create_collection('system_prompts')\ncollection.add(documents=leaked_prompts, ids=ids)\nresults = collection.query(query_texts=['write a helpful assistant prompt'], n_results=5)",
                    "dependencies": ["chromadb", "sentence-transformers", "openai"],
                    "gotchas": ["Re-embedding full corpus on restart unless persisted to disk", "Cosine similarity doesn't capture prompt structure — chunk by section not whole prompt"],
                }
            }
        ],
        "all_repos": [
            {"full_name": "chroma-core/chroma", "stargazers_count": 15000, "language": "Python", "relevance_score": 9, "relevance_reason": "Vector store for RAG — ideal for semantic retrieval over leaked prompt corpus"},
            {"full_name": "run-llama/llama_index", "stargazers_count": 38000, "language": "Python", "relevance_score": 8, "relevance_reason": "Full RAG framework — document ingestion, chunking, and retrieval pipeline ready-made"},
        ],
    },
]

WEB_FINDINGS = [
    {
        "sub_problem_title": "RAG over system prompt corpus",
        "analysis": {
            "key_insights": [
                "Chunking system prompts by section (role, rules, format) yields better retrieval than whole-prompt embedding",
                "sentence-transformers all-MiniLM-L6-v2 is fastest embedder for prompt-length texts",
                "Most leaked prompt collections available on HuggingFace datasets hub",
            ],
            "recommended_libraries": ["chromadb", "sentence-transformers", "llama-index"],
        }
    }
]

async def main():
    agent = PatternExtractorAgent()
    result = await agent.run(GITHUB_FINDINGS, WEB_FINDINGS, INTAKE)

    print("PATTERN EXTRACTOR OUTPUT:")
    print(json.dumps(result, indent=2))

    print("\nVERDICT:")
    for key, items in result.items():
        if isinstance(items, list):
            generic = [i for i in items if not any(
                kw in json.dumps(i).lower()
                for kw in ["prompt", "rag", "embed", "retriev", "chroma", "llama", "vector", "corpus", "leaked"]
            )]
            status = f"{len(items)} items, {len(generic)} generic"
            print(f"  {key}: {status}")

asyncio.run(main())
