"""
Test: quality judge against two briefs.
Brief A = the broken one (T5 fine-tuning + Neo4j) — should score low on architecture_matches_problem.
Brief B = a correct brief (RAG + chroma) — should score high.
"""
import asyncio
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.quality_judge import QualityJudgeAgent

INTAKE = {
    "raw_idea": (
        "build an AI tool that analyzes system prompts, gives insights to the user, "
        "and connects to a database of leaked system prompts to guide the user to "
        "write a master system prompt"
    ),
    "ideal_outcome": (
        "A tool that analyzes system prompts, extracts insights from a corpus of leaked "
        "system prompts via RAG retrieval, and guides users in writing high-quality master system prompts."
    ),
}

BRIEF_BAD = """
# Research Brief

## Executive Summary
We will build an AI tool using T5-base fine-tuned on leaked system prompts.
Store prompts in Neo4j graph database. Use microservices architecture with Docker.

## Phase 1: Database Design
Design Neo4j schema with Prompt, Category, Tag nodes.
Use py2neo driver for Python integration.

## Phase 2: AI Model Development
Fine-tune T5ForConditionalGeneration on leaked prompt dataset.
Train with HuggingFace Trainer API. Recommended model: t5-base.

## Phase 3: Integration
Integrate fine-tuned model with Neo4j using Flask microservice.
Deploy on Docker + Kubernetes.

## Privacy and Compliance
Implement encryption with pycryptodome. Follow GDPR.

## Tech Stack
| Component | Recommendation |
| Database | Neo4j |
| ML Model | T5-base (fine-tuned) |
| Framework | Flask + Docker |
"""

BRIEF_GOOD = """
# Research Brief

## Executive Summary
Build a RAG-powered system prompt analyzer. Embed a corpus of leaked system prompts
using sentence-transformers, store in ChromaDB, and retrieve semantically similar
prompts to guide users writing new system prompts.

## SP-1: System Prompt Corpus
Use f/awesome-chatgpt-prompts (112k stars) + HuggingFace datasets as the leaked corpus.
Load with `datasets.load_dataset("fka/awesome-chatgpt-prompts")`.

## SP-2: Embedding + Retrieval
ChromaDB (chroma-core/chroma, 15k stars) for vector store.
sentence-transformers all-MiniLM-L6-v2 for embeddings — fastest for prompt-length text.
```python
collection.add(documents=leaked_prompts, ids=ids)
results = collection.query(query_texts=[user_prompt], n_results=5)
```

## SP-3: Insight Extraction + Prompt Builder
LlamaIndex (run-llama/llama_index, 38k stars) for RAG pipeline.
On query: retrieve top-5 similar leaked prompts → extract structural patterns → suggest improvements.

## Build Order
1. Ingest corpus into ChromaDB
2. Build retrieval + pattern extraction layer
3. Wire to prompt builder UI (Streamlit)
"""

async def main():
    judge = QualityJudgeAgent()

    print("=" * 60)
    print("BRIEF A (broken — T5 fine-tuning + Neo4j):")
    result_a = await judge.run(BRIEF_BAD, INTAKE)
    print(f"  overall_score:               {result_a['overall_score']}")
    print(f"  architecture_matches_problem: {result_a['dimensions']['architecture_matches_problem']}")
    print(f"  verdict:                     {result_a['verdict']}")
    print(f"  gaps: {result_a['gaps'][:2]}")

    judge2 = QualityJudgeAgent()
    print("\nBRIEF B (correct — RAG + ChromaDB):")
    result_b = await judge2.run(BRIEF_GOOD, INTAKE)
    print(f"  overall_score:               {result_b['overall_score']}")
    print(f"  architecture_matches_problem: {result_b['dimensions']['architecture_matches_problem']}")
    print(f"  verdict:                     {result_b['verdict']}")

    print("\nVERDICT:")
    a_arch = result_a['dimensions']['architecture_matches_problem']
    b_arch = result_b['dimensions']['architecture_matches_problem']
    a_pass = result_a['verdict'] == "RE_RESEARCH" and a_arch < 6
    b_pass = result_b['verdict'] in ("SHIP", "NEEDS_GAPS_FILLED") and b_arch >= 6
    print(f"  Brief A (bad) correctly flagged RE_RESEARCH: {'PASS' if a_pass else 'FAIL'}")
    print(f"  Brief B (good) not flagged RE_RESEARCH:      {'PASS' if b_pass else 'FAIL'}")

asyncio.run(main())
