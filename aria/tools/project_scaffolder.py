"""
ARIA v2 — Project Scaffolder
Generates starter project files from research findings.

Build mode only. Takes the knowledge package artifacts and produces:
- Project directory structure (src/, tests/, config/, docs/)
- Package manager config (package.json, requirements.txt, Cargo.toml)
- Core source files based on patterns and build plan
- Test scaffold
- README with project overview

Inputs:
    - intake_result: primary_language, domain, core_problems
    - patterns: libraries_to_use, architectural_patterns, project_structure
    - brief: full research brief with build plan
    - extracted_code_dir: path to extracted source files from top repos
"""

import os
import shutil
from typing import Any, Optional

# ─── Language Templates ────────────────────────────────────────────────────────

def _get_dir_structure(language: str) -> dict[str, str]:
    """Return the directory structure template for a given language."""
    templates = {
        "python": {
            "src/": "Main source code package",
            "src/core/": "Core business logic",
            "src/api/": "API interface layer",
            "src/models/": "Data models and schemas",
            "src/utils/": "Utility functions",
            "tests/": "Test suite",
            "tests/unit/": "Unit tests",
            "tests/integration/": "Integration tests",
            "config/": "Configuration files",
            "docs/": "Documentation",
            "scripts/": "Helper scripts",
        },
        "js": {
            "src/": "Main source code",
            "src/components/": "UI components",
            "src/services/": "Service layer",
            "src/utils/": "Utility functions",
            "tests/": "Test suite",
            "tests/unit/": "Unit tests",
            "config/": "Configuration files",
            "docs/": "Documentation",
            "public/": "Static assets",
        },
        "typescript": {
            "src/": "Main source code",
            "src/core/": "Core business logic",
            "src/services/": "Service layer",
            "src/types/": "TypeScript type definitions",
            "src/utils/": "Utility functions",
            "tests/": "Test suite",
            "tests/unit/": "Unit tests",
            "config/": "Configuration files",
            "docs/": "Documentation",
        },
        "rust": {
            "src/": "Main source code",
            "src/bin/": "Binary entry points",
            "src/lib/": "Library modules",
            "tests/": "Integration tests",
            "benches/": "Benchmarks",
            "examples/": "Example programs",
            "docs/": "Documentation",
            "config/": "Configuration files",
        },
        "go": {
            "cmd/": "Main application entry points",
            "internal/": "Private application code",
            "pkg/": "Public library code",
            "api/": "API definitions",
            "tests/": "Test suite",
            "config/": "Configuration files",
            "docs/": "Documentation",
        },
        "java": {
            "src/main/java/com/app/": "Main application source",
            "src/main/resources/": "Application resources",
            "src/test/java/com/app/": "Test source",
            "config/": "Configuration files",
            "docs/": "Documentation",
            "scripts/": "Build scripts",
        },
        "cpp": {
            "src/": "Main source code",
            "include/": "Header files",
            "tests/": "Test suite",
            "config/": "Configuration files",
            "docs/": "Documentation",
            "scripts/": "Build scripts",
        },
    }
    # Normalize language name
    lang = language.lower().strip() if language else "unknown"
    for key in ["python", "javascript", "typescript", "rust", "go", "golang", "java", "cpp", "c++"]:
        if key in lang:
            mapped = {"javascript": "js", "golang": "go", "c++": "cpp"}.get(key, key)
            if mapped in templates:
                return templates[mapped]
    # Default to Python structure
    return templates["python"]


def _get_package_config(language: str, libraries: list[dict[str, Any]]) -> str:
    """Generate package manager configuration content."""
    lang = language.lower().strip() if language else ""

    lib_names = []
    for lib in libraries:
        name = lib.get("name", lib.get("library", lib.get("package", "")))
        version = lib.get("version", lib.get("recommended_version", ""))
        if name:
            lib_names.append((name, version))

    if "python" in lang:
        lines = ["# ARIA-generated requirements.txt", f"# Generated from research on: {', '.join(lib_names[:5])}", ""]
        for name, version in lib_names:
            if version:
                lines.append(f"{name}=={version}")
            else:
                lines.append(name)
        # Add common development dependencies
        lines.extend(["", "# Development", "pytest>=7.0", "pytest-cov>=4.0"])
        return "\n".join(lines)

    elif "js" in lang or "typescript" in lang or "javascript" in lang:
        pkg = {
            "name": "aria-generated-project",
            "version": "0.1.0",
            "description": "ARIA-generated project from deep code research",
            "main": "src/index.js" if "javascript" in lang else "src/index.ts",
            "scripts": {
                "start": "node src/index.js",
                "test": "jest",
                "dev": "nodemon src/index.js",
            },
            "dependencies": {},
            "devDependencies": {
                "jest": "^29.0.0",
                "nodemon": "^3.0.0",
            },
        }
        for name, version in lib_names:
            pkg["dependencies"][name] = version if version else "^1.0.0"
        import json
        return json.dumps(pkg, indent=2)

    elif "rust" in lang:
        lines = ['[package]', 'name = "aria-generated-project"', 'version = "0.1.0"', 'edition = "2021"', '']
        lines.append('[dependencies]')
        for name, version in lib_names:
            if version:
                lines.append(f'{name} = "{version}"')
            else:
                lines.append(f'{name} = "1.0"')
        return "\n".join(lines)

    elif "go" in lang:
        lines = ["module github.com/user/aria-generated-project", "", "go 1.22", ""]
        lines.append("require (")
        for name, version in lib_names:
            if version:
                lines.append(f"\t{name} v{version}")
            else:
                lines.append(f"\t{name} v1.0.0")
        lines.append(")")
        return "\n".join(lines)

    else:
        return "# Package configuration\n# Language: {}\n# Libraries: {}\n".format(
            language, ", ".join(n for n, _ in lib_names)
        )


def _get_entry_point(language: str, domain: list[str], patterns: dict[str, Any]) -> str:
    """Generate a starter entry point / main file."""
    lang = language.lower().strip() if language else ""
    architecture = patterns.get("architectural_patterns", [])
    arch_names = [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in (architecture[:3])]
    arch_context = ", ".join(arch_names) if arch_names else "modular"
    domain_str = ", ".join(domain) if domain else "general"

    if "python" in lang:
        return f'''"""
ARIA-Generated Project — Starter Entry Point

Domain: {domain_str}
Architecture: {arch_context}

Generated from deep code research. Expand this scaffold based on
the build plan in the knowledge package.
"""

import logging
import sys


def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting {domain_str} application...")

    # TODO: Implement based on the build plan in knowledge_package/06_BUILD_PLAN.md
    # See knowledge_package/extracted_code/ for implementation patterns
    pass


if __name__ == "__main__":
    main()
'''

    elif "js" in lang or "javascript" in lang:
        return '''/**
 * ARIA-Generated Project — Starter Entry Point
 *
 * Domain: %s
 * Architecture: %s
 *
 * Generated from deep code research. Expand this scaffold based on
 * the build plan in the knowledge package.
 */

const main = () => {
    console.log("Starting %s application...");
    // TODO: Implement based on the build plan in knowledge_package/06_BUILD_PLAN.md
};

main();
''' % (domain_str, arch_context, domain_str)

    elif "typescript" in lang:
        return '''/**
 * ARIA-Generated Project — Starter Entry Point
 *
 * Domain: %s
 * Architecture: %s
 *
 * Generated from deep code research. Expand this scaffold based on
 * the build plan in the knowledge package.
 */

const main = (): void => {
    console.log("Starting %s application...");
    // TODO: Implement based on the build plan in knowledge_package/06_BUILD_PLAN.md
};

main();
''' % (domain_str, arch_context, domain_str)

    elif "rust" in lang:
        return '''/// ARIA-Generated Project — Starter Entry Point
///
/// Domain: %s
/// Architecture: %s
///
/// Generated from deep code research. Expand this scaffold based on
/// the build plan in the knowledge package.

fn main() {
    println!("Starting %s application...");
    // TODO: Implement based on the build plan in knowledge_package/06_BUILD_PLAN.md
}
''' % (domain_str, arch_context, domain_str)

    else:
        return f"""// ARIA-Generated Project — Starter Entry Point
// Domain: {domain_str}
// Architecture: {arch_context}
//
// Generated from deep code research. Expand this scaffold based on
// the build plan in the knowledge package.

fn main() {{
    println!("Starting {domain_str} application...");
}}
"""


def _get_test_file(language: str) -> str:
    """Generate a starter test file."""
    lang = language.lower().strip() if language else ""

    if "python" in lang:
        return '''"""Starter test file — expand with real tests as you build."""

import pytest


def test_placeholder() -> None:
    """Placeholder test — will be replaced during development."""
    assert True
'''
    elif "js" in lang or "javascript" in lang or "typescript" in lang:
        return '''/**
 * Starter test file — expand with real tests as you build.
 */

describe("Placeholder", () => {
    it("should pass — will be replaced during development", () => {
        expect(true).toBe(true);
    });
});
'''
    elif "rust" in lang:
        return '''/// Starter test file — expand with real tests as you build.

#[cfg(test)]
mod tests {
    #[test]
    fn placeholder() {
        assert!(true);
    }
}
'''
    else:
        return '// Starter test — expand with real tests as you build.\nassert!(true);'


def _get_gitignore(language: str) -> str:
    """Generate .gitignore content."""
    lang = language.lower().strip() if language else ""
    lines = ["# ARIA-generated project", "", "__pycache__/", "*.pyc", "*.pyo", ".env", "venv/", ".venv/",
             "node_modules/", "dist/", "build/", "target/", ".idea/", ".vscode/",
             "*.log", ".DS_Store", "*.swp", "*.swo"]
    if "rust" in lang:
        lines.append("")
        lines.append("# Rust")
        lines.append("Cargo.lock")
    if "python" in lang:
        lines.append("")
        lines.append("# Python")
        lines.append("*.egg-info/")
        lines.append(".pytest_cache/")
        lines.append("htmlcov/")
    if "go" in lang:
        lines.append("")
        lines.append("# Go")
        lines.append("bin/")
        lines.append("*.exe")
    return "\n".join(lines)


# ─── Scaffolder ─────────────────────────────────────────────────────────────────

class ProjectScaffolder:
    """
    Generates a starter project from ARIA research findings.

    Takes the knowledge package artifacts and creates a ready-to-extend
    project structure with config files, source files, tests, and docs.
    """

    def __init__(self):
        self.created_files: list[str] = []

    async def scaffold(
        self,
        output_dir: str,
        intake_result: dict[str, Any],
        patterns: dict[str, Any],
        brief: str,
        extracted_code_dir: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate the starter project scaffold.

        Args:
            output_dir: Directory to create the project in
            intake_result: From IntakeAgent (has primary_language, domain, etc.)
            patterns: From PatternExtractor (has libraries, architecture, etc.)
            brief: Full research brief markdown
            extracted_code_dir: Path to extracted code (for reference)

        Returns:
            Dict with status, project_dir, and created_files list
        """
        self.created_files = []

        language = intake_result.get("primary_language", "python")
        domain = intake_result.get("domain", [])
        libraries = patterns.get("libraries_to_use", [])

        # Create project directory
        project_dir = os.path.join(output_dir, "project")
        os.makedirs(project_dir, exist_ok=True)

        # 1. Create directory structure
        dirs = _get_dir_structure(language)
        created_dirs = []
        for dir_path, description in dirs.items():
            full_path = os.path.join(project_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
            created_dirs.append(dir_path)

        # 2. Generate README
        readme = self._generate_readme(language, domain, intake_result, patterns)
        self._write_file(project_dir, "README.md", readme)

        # 3. Generate package config
        pkg_config = _get_package_config(language, libraries)
        config_filename = {
            "python": "requirements.txt",
            "js": "package.json",
            "javascript": "package.json",
            "typescript": "package.json",
            "rust": "Cargo.toml",
            "go": "go.mod",
            "golang": "go.mod",
        }.get(language, "requirements.txt")
        self._write_file(project_dir, config_filename, pkg_config)

        # 4. Generate .gitignore
        self._write_file(project_dir, ".gitignore", _get_gitignore(language))

        # 5. Generate entry point
        entry_point = _get_entry_point(language, domain, patterns)
        entry_filename = {
            "python": "src/main.py",
            "js": "src/index.js",
            "javascript": "src/index.js",
            "typescript": "src/index.ts",
            "rust": "src/main.rs",
            "go": "cmd/main.go",
            "golang": "cmd/main.go",
        }.get(language, "src/main.py")
        self._write_file(project_dir, entry_filename, entry_point)

        # 6. Generate test file
        test_content = _get_test_file(language)
        test_filename = {
            "python": "tests/test_main.py",
            "js": "tests/test_main.test.js",
            "javascript": "tests/test_main.test.js",
            "typescript": "tests/test_main.test.ts",
            "rust": "tests/integration_test.rs",
            "go": "tests/main_test.go",
            "golang": "tests/main_test.go",
        }.get(language, "tests/test_main.py")
        self._write_file(project_dir, test_filename, test_content)

        # 7. Copy extracted code as reference
        if extracted_code_dir and os.path.isdir(extracted_code_dir):
            ref_dir = os.path.join(project_dir, "reference_code")
            try:
                shutil.copytree(extracted_code_dir, ref_dir, dirs_exist_ok=True)
                self.created_files.append("reference_code/ (copied from extracted repos)")
            except OSError:
                pass

        # 8. Write a BUILD_NOTES.md with the build plan summary
        self._write_file(project_dir, "BUILD_NOTES.md", self._generate_build_notes(brief, patterns))

        return {
            "status": "done",
            "project_dir": project_dir,
            "created_files": self.created_files,
            "created_dirs": created_dirs,
            "language": language,
            "domain": domain,
        }

    def _write_file(self, base_dir: str, rel_path: str, content: str) -> None:
        """Write a file and track it."""
        full_path = os.path.join(base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.created_files.append(rel_path)

    def _generate_readme(
        self,
        language: str,
        domain: list[str],
        intake: dict[str, Any],
        patterns: dict[str, Any],
    ) -> str:
        """Generate a project README from the research findings."""
        idea = intake.get("raw_idea", "ARIA-generated project")
        outcome = intake.get("ideal_outcome", "Build the solution")
        core_problems = intake.get("core_problems", [])
        libraries = patterns.get("libraries_to_use", [])
        arch = patterns.get("architectural_patterns", [])
        repos = patterns.get("repos_to_fork", [])

        lib_lines = "\n".join(
            f"- **{lib.get('name', lib.get('library', ''))}** — {lib.get('justification', lib.get('reason', ''))[:120]}"
            for lib in libraries[:8]
        )
        arch_lines = "\n".join(
            f"- **{a.get('name', str(a))}**" if isinstance(a, dict) else f"- {a}"
            for a in arch[:5]
        )
        problem_lines = "\n".join(f"- {p}" for p in core_problems[:5])
        repo_lines = "\n".join(
            f"- [{r.get('name', r.get('repo', ''))}]({r.get('url', '#')}) — {r.get('description', r.get('reason', ''))[:100]}"
            for r in repos[:5]
        )

        return (
            f"# ARIA-Generated Project\n\n"
            f"## Overview\n{idea}\n\n"
            f"**Language:** {language}  \n"
            f"**Domain:** {', '.join(domain) if domain else 'General'}  \n\n"
            f"## Ideal Outcome\n{outcome}\n\n"
            f"## Core Problems\n{problem_lines}\n\n"
            f"## Architecture\n{arch_lines}\n\n"
            f"## Recommended Libraries\n{lib_lines}\n\n"
            f"## Reference Repositories\n{repo_lines}\n\n"
            f"## Getting Started\n"
            f"1. Review `BUILD_NOTES.md` for the full build plan\n"
            f"2. Check `reference_code/` for implementation patterns from top repos\n"
            f"3. Start with `src/` and follow the build plan phases\n"
            f"4. See `knowledge_package/` in the ARIA output for full research context\n"
        )

    @staticmethod
    def _generate_build_notes(brief: str, patterns: dict[str, Any]) -> str:
        """Extract build plan summary from the research brief."""
        # Try to extract the build plan section from the brief
        build_plan = ""
        if "## Build Order" in brief:
            parts = brief.split("## Build Order", 1)
            if len(parts) > 1:
                build_plan = "## Build Order" + parts[1].split("##", 1)[0] if "##" in parts[1] else "## Build Order" + parts[1]
        elif "## Implementation" in brief:
            parts = brief.split("## Implementation", 1)
            if len(parts) > 1:
                build_plan = "## Implementation" + parts[1].split("##", 1)[0] if "##" in parts[1] else "## Implementation" + parts[1]

        anti_patterns = patterns.get("anti_patterns", [])
        gotchas = patterns.get("gotchas", patterns.get("key_gotchas", []))
        risks = patterns.get("risks", [])

        anti_lines = "\n".join(f"- {a}" for a in (anti_patterns if isinstance(anti_patterns, list) else [str(anti_patterns)])[:5])
        gotcha_lines = "\n".join(f"- {g}" for g in (gotchas if isinstance(gotchas, list) else [str(gotchas)])[:5])
        risk_lines = "\n".join(f"- {r}" for r in (risks if isinstance(risks, list) else [str(risks)])[:5])

        return (
            f"# ARIA Build Notes\n\n"
            f"## Build Plan\n{build_plan[:3000] if build_plan else 'See the full ARIA research brief for the build plan.'}\n\n"
            f"## Anti-Patterns to Avoid\n{anti_lines if anti_lines else '- See knowledge_package/08_RISKS.md'}\n\n"
            f"## Gotchas & Pitfalls\n{gotcha_lines if gotcha_lines else '- See knowledge_package/08_RISKS.md'}\n\n"
            f"## Risks\n{risk_lines if risk_lines else '- See knowledge_package/08_RISKS.md'}\n\n"
            f"---\n*Generated by ARIA v2 — Feed this project to Codebuff / Claude Code to start building.*\n"
        )


__all__ = ["ProjectScaffolder"]
