"""
Prompt Builder - Analyze a codebase and generate custom review prompts

This tool scans an existing codebase to extract coding conventions, patterns,
and standards, then generates a custom prompt file that can be used with the
code reviewer to enforce those same patterns in future code.

Usage:
    python prompt_builder.py <project_directory> [options]

See README.md for full documentation.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import Counter, defaultdict

# Reuse the extension map from reviewer
EXTENSION_MAP = {
    ".cs": "csharp",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
}


class CodebaseAnalyzer:
    """Analyzes a codebase to extract patterns and conventions."""

    def __init__(self, project_dir: Path, language: str):
        self.project_dir = project_dir
        self.language = language
        self.files: List[Path] = []
        self.analysis = {
            "naming_conventions": {
                "classes": [],
                "functions": [],
                "variables": [],
                "constants": [],
                "private_fields": []
            },
            "imports": Counter(),
            "frameworks": set(),
            "patterns": {
                "error_handling": [],
                "async_patterns": [],
                "testing_patterns": [],
                "documentation": []
            },
            "file_structure": defaultdict(int),
            "common_features": Counter(),
            "code_quality": {
                "avg_function_length": 0,
                "max_file_length": 0,
                "uses_type_hints": False,
                "uses_docstrings": False
            }
        }

    def scan_files(self, recursive: bool = True) -> List[Path]:
        """Scan directory for files matching the language."""
        extensions = [ext for ext, lang in EXTENSION_MAP.items() if lang == self.language]

        pattern = "**/*" if recursive else "*"

        for ext in extensions:
            for filepath in self.project_dir.glob(f"{pattern}{ext}"):
                if filepath.is_file() and not self._should_skip(filepath):
                    self.files.append(filepath)

        print(f"Found {len(self.files)} {self.language} files")
        return self.files

    def _should_skip(self, filepath: Path) -> bool:
        """Skip common non-source directories."""
        skip_dirs = {
            "node_modules", "venv", ".venv", "env", ".env",
            "build", "dist", "target", "bin", "obj",
            ".git", ".svn", "__pycache__", ".pytest_cache"
        }
        return any(part in skip_dirs for part in filepath.parts)

    def analyze(self) -> Dict:
        """Run full analysis on all files."""
        if not self.files:
            self.scan_files()

        print(f"Analyzing {len(self.files)} files...")

        for filepath in self.files:
            try:
                content = filepath.read_text(encoding="utf-8")
                self._analyze_file(filepath, content)
            except Exception as e:
                print(f"Warning: Could not analyze {filepath}: {e}")

        self._compute_statistics()
        return self.analysis

    def _analyze_file(self, filepath: Path, content: str):
        """Analyze a single file."""
        lines = content.split('\n')

        # Track file length
        self.analysis["code_quality"]["max_file_length"] = max(
            self.analysis["code_quality"]["max_file_length"],
            len(lines)
        )

        # Language-specific analysis
        if self.language == "python":
            self._analyze_python(content, lines)
        elif self.language == "typescript" or self.language == "javascript":
            self._analyze_typescript(content, lines)
        elif self.language == "csharp":
            self._analyze_csharp(content, lines)
        elif self.language == "go":
            self._analyze_go(content, lines)
        elif self.language == "rust":
            self._analyze_rust(content, lines)
        elif self.language == "java":
            self._analyze_java(content, lines)

    def _analyze_python(self, content: str, lines: List[str]):
        """Analyze Python-specific patterns."""
        # Find class names
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find function/method names
        for match in re.finditer(r'^(?:async\s+)?def\s+(\w+)', content, re.MULTILINE):
            func_name = match.group(1)
            if func_name.startswith('_') and not func_name.startswith('__'):
                self.analysis["naming_conventions"]["private_fields"].append(func_name)
            else:
                self.analysis["naming_conventions"]["functions"].append(func_name)

        # Find constants (UPPERCASE)
        for match in re.finditer(r'^([A-Z_]{2,})\s*=', content, re.MULTILINE):
            self.analysis["naming_conventions"]["constants"].append(match.group(1))

        # Find imports
        for match in re.finditer(r'^(?:from\s+(\S+)\s+import|import\s+(\S+))', content, re.MULTILINE):
            module = match.group(1) or match.group(2)
            base_module = module.split('.')[0]
            self.analysis["imports"][base_module] += 1

        # Detect frameworks
        if 'fastapi' in content.lower() or 'FastAPI' in content:
            self.analysis["frameworks"].add("FastAPI")
        if 'flask' in content.lower() or 'Flask' in content:
            self.analysis["frameworks"].add("Flask")
        if 'django' in content.lower():
            self.analysis["frameworks"].add("Django")
        if 'pytest' in content.lower():
            self.analysis["frameworks"].add("pytest")

        # Check for type hints
        if re.search(r':\s*\w+\s*(?:=|\)|->', content):
            self.analysis["code_quality"]["uses_type_hints"] = True

        # Check for docstrings
        if '"""' in content or "'''" in content:
            self.analysis["code_quality"]["uses_docstrings"] = True

        # Error handling patterns
        if 'try:' in content:
            self.analysis["patterns"]["error_handling"].append("try/except blocks")
        if 'raise ' in content:
            self.analysis["patterns"]["error_handling"].append("explicit exceptions")

        # Async patterns
        if 'async def' in content:
            self.analysis["patterns"]["async_patterns"].append("async/await")
        if 'asyncio' in content:
            self.analysis["patterns"]["async_patterns"].append("asyncio")

    def _analyze_typescript(self, content: str, lines: List[str]):
        """Analyze TypeScript/JavaScript patterns."""
        # Find class names
        for match in re.finditer(r'class\s+(\w+)', content):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find function names
        for match in re.finditer(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()', content):
            func_name = match.group(1) or match.group(2)
            if func_name:
                self.analysis["naming_conventions"]["functions"].append(func_name)

        # Find constants
        for match in re.finditer(r'const\s+([A-Z_]{2,})\s*=', content):
            self.analysis["naming_conventions"]["constants"].append(match.group(1))

        # Find private fields (TypeScript)
        for match in re.finditer(r'private\s+(\w+):', content):
            self.analysis["naming_conventions"]["private_fields"].append(match.group(1))

        # Find imports
        for match in re.finditer(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)', content):
            module = match.group(1)
            base_module = module.split('/')[0].replace('@', '')
            if not module.startswith('.'):
                self.analysis["imports"][base_module] += 1

        # Detect frameworks
        if 'react' in content.lower() or 'React' in content:
            self.analysis["frameworks"].add("React")
        if 'vue' in content.lower():
            self.analysis["frameworks"].add("Vue")
        if 'angular' in content.lower():
            self.analysis["frameworks"].add("Angular")
        if 'express' in content.lower():
            self.analysis["frameworks"].add("Express")
        if 'jest' in content.lower() or 'describe(' in content:
            self.analysis["frameworks"].add("Jest")

        # Type usage
        if ': any' in content:
            self.analysis["common_features"]["uses_any_type"] += 1
        if 'interface ' in content or 'type ' in content:
            self.analysis["code_quality"]["uses_type_hints"] = True

        # Async patterns
        if 'async ' in content or 'await ' in content:
            self.analysis["patterns"]["async_patterns"].append("async/await")
        if '.then(' in content:
            self.analysis["patterns"]["async_patterns"].append("Promise chains")

        # Error handling
        if 'try {' in content:
            self.analysis["patterns"]["error_handling"].append("try/catch blocks")

    def _analyze_csharp(self, content: str, lines: List[str]):
        """Analyze C# patterns."""
        # Find class names
        for match in re.finditer(r'class\s+(\w+)', content):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find method names
        for match in re.finditer(r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?(?:\w+\s+)?(\w+)\s*\(', content):
            self.analysis["naming_conventions"]["functions"].append(match.group(1))

        # Find private fields
        for match in re.finditer(r'private\s+(?:readonly\s+)?\w+\s+(_\w+)', content):
            self.analysis["naming_conventions"]["private_fields"].append(match.group(1))

        # Find using statements
        for match in re.finditer(r'using\s+([^;]+);', content):
            namespace = match.group(1).strip()
            base = namespace.split('.')[0]
            self.analysis["imports"][base] += 1

        # Detect frameworks
        if 'Entity' in content and 'Framework' in content:
            self.analysis["frameworks"].add("Entity Framework")
        if 'DbContext' in content:
            self.analysis["frameworks"].add("Entity Framework")
        if '[ApiController]' in content or 'Controller' in content:
            self.analysis["frameworks"].add("ASP.NET Core")
        if 'xUnit' in content or '[Fact]' in content:
            self.analysis["frameworks"].add("xUnit")
        if 'NUnit' in content or '[Test]' in content:
            self.analysis["frameworks"].add("NUnit")

        # Nullable reference types
        if '#nullable enable' in content or '?' in content:
            self.analysis["code_quality"]["uses_type_hints"] = True

        # Async patterns
        if 'async ' in content and 'await ' in content:
            self.analysis["patterns"]["async_patterns"].append("async/await")
        if '.ConfigureAwait(' in content:
            self.analysis["patterns"]["async_patterns"].append("ConfigureAwait")

        # Error handling
        if 'try' in content and 'catch' in content:
            self.analysis["patterns"]["error_handling"].append("try/catch blocks")

        # Documentation
        if '///' in content:
            self.analysis["patterns"]["documentation"].append("XML documentation")

    def _analyze_go(self, content: str, lines: List[str]):
        """Analyze Go patterns."""
        # Find type names (structs, interfaces)
        for match in re.finditer(r'type\s+(\w+)\s+(?:struct|interface)', content):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find function names
        for match in re.finditer(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(', content):
            self.analysis["naming_conventions"]["functions"].append(match.group(1))

        # Find imports
        for match in re.finditer(r'import\s+(?:\(\s*([^)]+)\)|"([^"]+)")', content, re.DOTALL):
            imports_block = match.group(1) or match.group(2)
            for imp in re.finditer(r'"([^"]+)"', imports_block):
                package = imp.group(1).split('/')[-1]
                self.analysis["imports"][package] += 1

        # Error handling
        if 'if err != nil' in content:
            self.analysis["patterns"]["error_handling"].append("explicit error checking")
        if 'defer ' in content:
            self.analysis["patterns"]["error_handling"].append("defer for cleanup")

        # Concurrency
        if 'go func' in content or 'go ' in content:
            self.analysis["patterns"]["async_patterns"].append("goroutines")
        if 'chan ' in content:
            self.analysis["patterns"]["async_patterns"].append("channels")
        if 'sync.' in content:
            self.analysis["patterns"]["async_patterns"].append("sync primitives")

        # Testing
        if 'func Test' in content:
            self.analysis["patterns"]["testing_patterns"].append("standard testing")
        if 't.Run(' in content:
            self.analysis["patterns"]["testing_patterns"].append("table-driven tests")

    def _analyze_rust(self, content: str, lines: List[str]):
        """Analyze Rust patterns."""
        # Find struct/enum names
        for match in re.finditer(r'(?:pub\s+)?(?:struct|enum)\s+(\w+)', content):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find function names
        for match in re.finditer(r'(?:pub\s+)?fn\s+(\w+)', content):
            self.analysis["naming_conventions"]["functions"].append(match.group(1))

        # Find constants
        for match in re.finditer(r'const\s+([A-Z_]+):', content):
            self.analysis["naming_conventions"]["constants"].append(match.group(1))

        # Find use statements
        for match in re.finditer(r'use\s+([^;]+);', content):
            module = match.group(1).split('::')[0]
            self.analysis["imports"][module] += 1

        # Error handling
        if 'Result<' in content:
            self.analysis["patterns"]["error_handling"].append("Result type")
        if '?' in content:
            self.analysis["patterns"]["error_handling"].append("? operator")
        if '.unwrap()' in content:
            self.analysis["common_features"]["uses_unwrap"] += 1

        # Async
        if 'async fn' in content or '.await' in content:
            self.analysis["patterns"]["async_patterns"].append("async/await")

        # Testing
        if '#[test]' in content:
            self.analysis["patterns"]["testing_patterns"].append("unit tests")
        if '#[cfg(test)]' in content:
            self.analysis["patterns"]["testing_patterns"].append("test modules")

    def _analyze_java(self, content: str, lines: List[str]):
        """Analyze Java patterns."""
        # Find class names
        for match in re.finditer(r'(?:public\s+)?class\s+(\w+)', content):
            self.analysis["naming_conventions"]["classes"].append(match.group(1))

        # Find method names
        for match in re.finditer(r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)?(\w+)\s*\(', content):
            self.analysis["naming_conventions"]["functions"].append(match.group(1))

        # Find imports
        for match in re.finditer(r'import\s+([^;]+);', content):
            package = match.group(1).split('.')[-1]
            self.analysis["imports"][package] += 1

        # Frameworks
        if 'Spring' in content or '@Autowired' in content:
            self.analysis["frameworks"].add("Spring")
        if 'JUnit' in content or '@Test' in content:
            self.analysis["frameworks"].add("JUnit")

        # Error handling
        if 'try {' in content:
            self.analysis["patterns"]["error_handling"].append("try/catch blocks")

        # Documentation
        if '/**' in content:
            self.analysis["patterns"]["documentation"].append("JavaDoc")

    def _compute_statistics(self):
        """Compute summary statistics."""
        # Determine dominant naming conventions
        for category in ["classes", "functions", "constants", "private_fields"]:
            items = self.analysis["naming_conventions"][category]
            if items:
                # Keep only most common examples
                self.analysis["naming_conventions"][category] = list(set(items))[:10]

        # Sort imports by frequency
        top_imports = self.analysis["imports"].most_common(15)
        self.analysis["imports"] = dict(top_imports)

        # Convert sets to lists for JSON serialization
        self.analysis["frameworks"] = list(self.analysis["frameworks"])

        # Deduplicate patterns
        for pattern_type in self.analysis["patterns"]:
            self.analysis["patterns"][pattern_type] = list(set(
                self.analysis["patterns"][pattern_type]
            ))


class PromptGenerator:
    """Generates a custom review prompt based on codebase analysis."""

    def __init__(self, analysis: Dict, language: str, project_name: str):
        self.analysis = analysis
        self.language = language
        self.project_name = project_name

    def generate(self) -> str:
        """Generate the full prompt text."""
        sections = [
            self._generate_header(),
            self._generate_naming_conventions(),
            self._generate_frameworks_section(),
            self._generate_best_practices(),
            self._generate_testing_section(),
            self._generate_code_quality(),
            self._generate_footer()
        ]

        return "\n\n".join(filter(None, sections))

    def _generate_header(self) -> str:
        """Generate prompt header."""
        return f"""You are an expert {self.language.title()} code reviewer for the {self.project_name} project.

This prompt was auto-generated by analyzing the existing codebase to extract
coding conventions, patterns, and standards. Review new code to ensure it
matches the established patterns in this project.

File: {{filename}}
Language: {{language}}"""

    def _generate_naming_conventions(self) -> str:
        """Generate naming conventions section."""
        nc = self.analysis["naming_conventions"]

        sections = ["## 1. Naming Conventions"]

        if nc["classes"]:
            convention = self._detect_case_convention(nc["classes"])
            examples = ", ".join(nc["classes"][:5])
            sections.append(f"- Classes: {convention} (e.g., {examples})")

        if nc["functions"]:
            convention = self._detect_case_convention(nc["functions"])
            examples = ", ".join(nc["functions"][:5])
            sections.append(f"- Functions/Methods: {convention} (e.g., {examples})")

        if nc["constants"]:
            convention = self._detect_case_convention(nc["constants"])
            examples = ", ".join(nc["constants"][:5])
            sections.append(f"- Constants: {convention} (e.g., {examples})")

        if nc["private_fields"]:
            convention = self._detect_case_convention(nc["private_fields"])
            examples = ", ".join(nc["private_fields"][:5])
            sections.append(f"- Private fields: {convention} (e.g., {examples})")

        return "\n".join(sections) if len(sections) > 1 else ""

    def _detect_case_convention(self, names: List[str]) -> str:
        """Detect the naming convention used."""
        if not names:
            return "unknown"

        sample = names[0]

        if sample.isupper() or (sample.upper() == sample.replace('_', '')):
            return "UPPER_SNAKE_CASE"
        elif '_' in sample and sample.islower():
            return "snake_case"
        elif sample[0].isupper() and '_' not in sample:
            return "PascalCase"
        elif sample[0].islower() and '_' not in sample:
            return "camelCase"
        else:
            return "mixed"

    def _generate_frameworks_section(self) -> str:
        """Generate frameworks and libraries section."""
        frameworks = self.analysis.get("frameworks", [])
        imports = self.analysis.get("imports", {})

        if not frameworks and not imports:
            return ""

        sections = ["## 2. Frameworks & Libraries"]

        if frameworks:
            sections.append("\nThis project uses:")
            for fw in frameworks:
                sections.append(f"- {fw}")

        if imports:
            sections.append("\nCommon imports/packages:")
            for module, count in list(imports.items())[:10]:
                sections.append(f"- {module} (used {count} times)")

        return "\n".join(sections)

    def _generate_best_practices(self) -> str:
        """Generate best practices section."""
        patterns = self.analysis["patterns"]

        sections = ["## 3. Code Patterns & Best Practices"]

        if patterns["error_handling"]:
            sections.append("\nError Handling:")
            for pattern in set(patterns["error_handling"]):
                sections.append(f"- Uses {pattern}")

        if patterns["async_patterns"]:
            sections.append("\nAsync/Concurrency Patterns:")
            for pattern in set(patterns["async_patterns"]):
                sections.append(f"- Uses {pattern}")

        if patterns["documentation"]:
            sections.append("\nDocumentation:")
            for pattern in set(patterns["documentation"]):
                sections.append(f"- Uses {pattern}")

        # Add language-specific patterns
        common = self.analysis.get("common_features", {})
        if common:
            sections.append("\nCommon Patterns:")
            for feature, count in common.items():
                if count > 3:
                    sections.append(f"- {feature.replace('_', ' ').title()}")

        return "\n".join(sections) if len(sections) > 1 else ""

    def _generate_testing_section(self) -> str:
        """Generate testing standards section."""
        patterns = self.analysis["patterns"].get("testing_patterns", [])

        if not patterns:
            return ""

        sections = ["## 4. Testing Standards"]
        sections.append("\nThis project follows these testing patterns:")

        for pattern in set(patterns):
            sections.append(f"- {pattern}")

        return "\n".join(sections)

    def _generate_code_quality(self) -> str:
        """Generate code quality section."""
        quality = self.analysis["code_quality"]

        sections = ["## 5. Code Quality & Style"]

        if quality.get("uses_type_hints"):
            sections.append("- Code uses type hints/annotations - ensure new code does too")

        if quality.get("uses_docstrings"):
            sections.append("- Functions have documentation - add docstrings to new functions")

        max_length = quality.get("max_file_length", 0)
        if max_length > 0:
            sections.append(f"- Maximum file length observed: ~{max_length} lines")

        return "\n".join(sections) if len(sections) > 1 else ""

    def _generate_footer(self) -> str:
        """Generate prompt footer."""
        return """## Review Guidelines

When reviewing code:
1. Check that it follows the naming conventions above
2. Ensure it uses the same frameworks/libraries as the rest of the codebase
3. Verify error handling matches established patterns
4. Confirm testing approach is consistent
5. Check code quality matches project standards

Prioritize issues by severity:
- CRITICAL: Bugs, security issues, inconsistent patterns that break compatibility
- HIGH: Major style violations, missing tests, poor error handling
- MEDIUM: Minor style issues, optimization opportunities
- LOW: Suggestions for improvement

```{language}
{code}
```

Review:"""


def main():
    parser = argparse.ArgumentParser(
        description="Prompt Builder - Generate custom code review prompts from existing codebases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project -l python          Analyze Python project
  %(prog)s ./src -l csharp -o prompts/custom.txt   Save to specific file
  %(prog)s ../myapp -l typescript --json       Output analysis as JSON

The tool will scan the codebase, extract patterns, and generate a custom
prompt file that can be used with reviewer_claude.py or reviewer.py.
        """
    )

    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to the project directory to analyze"
    )

    parser.add_argument(
        "-l", "--language",
        required=True,
        choices=list(set(EXTENSION_MAP.values())),
        help="Programming language to analyze"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: prompts/<language>-custom.txt)"
    )

    parser.add_argument(
        "-n", "--name",
        type=str,
        help="Project name (default: directory name)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output analysis as JSON instead of generating prompt"
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't scan subdirectories"
    )

    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: Directory not found: {args.project_dir}")
        sys.exit(1)

    if not args.project_dir.is_dir():
        print(f"Error: Not a directory: {args.project_dir}")
        sys.exit(1)

    # Determine project name
    project_name = args.name or args.project_dir.name

    # Analyze codebase
    print(f"\n{'='*60}")
    print(f"Analyzing {project_name} ({args.language})")
    print(f"{'='*60}\n")

    analyzer = CodebaseAnalyzer(args.project_dir, args.language)
    analyzer.scan_files(recursive=not args.no_recursive)

    if not analyzer.files:
        print(f"No {args.language} files found in {args.project_dir}")
        sys.exit(1)

    analysis = analyzer.analyze()

    # Output JSON if requested
    if args.json:
        print(json.dumps(analysis, indent=2))
        return

    # Generate prompt
    print("\nGenerating custom prompt...")
    generator = PromptGenerator(analysis, args.language, project_name)
    prompt = generator.generate()

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        prompts_dir = Path(__file__).parent / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        output_file = prompts_dir / f"{args.language}-custom.txt"

    # Write prompt
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(prompt, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ Prompt generated: {output_file}")
    print(f"{'='*60}\n")

    print("Summary:")
    print(f"  - Files analyzed: {len(analyzer.files)}")
    print(f"  - Classes found: {len(analysis['naming_conventions']['classes'])}")
    print(f"  - Functions found: {len(analysis['naming_conventions']['functions'])}")
    if analysis['frameworks']:
        print(f"  - Frameworks: {', '.join(analysis['frameworks'])}")

    print(f"\nUse this prompt with the reviewer:")
    print(f"  python reviewer_claude.py yourfile.{args.language} --prompt-file {output_file}")
    print()


if __name__ == "__main__":
    main()
