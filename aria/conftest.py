# These are standalone integration scripts (run with `python test_*.py`), not pytest suites.
collect_ignore = [
    "test_all_apis.py",
    "test_decomposer.py",
    "test_decomposer_aria.py",
    "test_github_scorer.py",
    "test_knowledge_packager.py",
    "test_pattern_extractor.py",
    "test_quality_judge.py",
    "test_synthesizer.py",
    "test_web_researcher.py",
]
