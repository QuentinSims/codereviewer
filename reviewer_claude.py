"""
Claude Code Reviewer CLI

A command-line tool that uses Anthropic's Claude API to perform
automated code reviews. Supports multiple languages with customizable
prompts for language-specific best practices.

Usage:
    python reviewer_claude.py <file_or_directory> [options]

See README.md for full documentation.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Base review prompt - comprehensive code review template
BASE_PROMPT = """You are an expert code reviewer. Analyze the following {language} code thoroughly.

## 1. Critical Issues (Priority: High)
- Bugs, logic errors, and potential runtime exceptions
- Null/undefined reference risks
- Resource leaks (memory, file handles, connections)
- Race conditions and thread safety issues
- Unhandled edge cases

## 2. Security Vulnerabilities
- Injection risks (SQL, command, XSS)
- Hardcoded secrets, credentials, or API keys
- Insecure data handling or exposure
- Input validation gaps
- Authentication/authorization weaknesses

## 3. Code Quality & Best Practices
- Naming conventions (consistency with language standards)
- Function/method length and cyclomatic complexity
- Single Responsibility Principle adherence
- DRY violations (duplicated code)
- Magic numbers/strings that should be constants
- Dead code or unreachable branches
- Error handling patterns

## 4. Performance Considerations
- Inefficient algorithms or data structures
- Unnecessary allocations or copies
- N+1 query patterns (if data access present)
- Blocking calls that should be async
- Missed caching opportunities

## 5. Testing & Testability
- Is the code testable? (dependency injection, pure functions)
- Missing test scenarios that should be covered
- Untested edge cases or error paths
- Suggestions for unit test cases
- Mocking considerations for dependencies

## 6. Documentation & Readability
- Missing or outdated comments on complex logic
- Public API documentation gaps
- Unclear variable/function names
- Code structure and organization

## Output Format
- Prioritize by severity (Critical > High > Medium > Low)
- Reference specific line numbers where applicable
- Provide brief, actionable suggestions
- Include code snippets for fixes when helpful

File: {filename}
Language: {language}

```{language}
{code}
```

Review:"""

# File extension to language mapping
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


def get_prompts_dir() -> Path:
    """Get the prompts directory path."""
    return Path(__file__).parent / "prompts"


def detect_language(filepath: Path) -> str:
    """Detect programming language from file extension."""
    return EXTENSION_MAP.get(filepath.suffix.lower(), "unknown")


def load_language_prompt(language: str) -> Optional[str]:
    """Load language-specific prompt from prompts directory if available."""
    prompt_file = get_prompts_dir() / f"{language}.txt"
    
    if prompt_file.exists():
        try:
            return prompt_file.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def review_code(
    code: str,
    filename: str,
    language: str,
    model: str = DEFAULT_MODEL,
    custom_prompt: Optional[str] = None,
    max_tokens: int = 4096,
    api_key: Optional[str] = None
) -> str:
    """Send code to Claude for review."""
    
    # Priority: custom_prompt > language-specific prompt > BASE_PROMPT
    if custom_prompt:
        prompt = custom_prompt
    else:
        prompt = load_language_prompt(language) or BASE_PROMPT
    
    full_prompt = prompt.format(
        filename=filename,
        language=language,
        code=code
    )
    
    # Get API key from parameter, environment, or raise error
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return "ERROR: ANTHROPIC_API_KEY not set. Set it via environment variable or --api-key flag."
    
    try:
        client = anthropic.Anthropic(api_key=key)
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,  # Lower for more focused responses
        )
        
        # Extract text from response
        if message.content and len(message.content) > 0:
            return message.content[0].text
        return "No response received"
        
    except anthropic.AuthenticationError:
        return "ERROR: Invalid API key. Check your ANTHROPIC_API_KEY."
    except anthropic.RateLimitError:
        return "ERROR: Rate limit exceeded. Please wait and try again."
    except anthropic.APIConnectionError:
        return "ERROR: Cannot connect to Anthropic API. Check your internet connection."
    except Exception as e:
        return f"ERROR: {str(e)}"


def review_file(
    filepath: Path,
    model: str,
    custom_prompt: Optional[str] = None,
    max_tokens: int = 4096,
    api_key: Optional[str] = None
) -> dict:
    """Review a single file."""
    if not filepath.exists():
        return {"file": str(filepath), "error": "File not found"}
    
    if not filepath.is_file():
        return {"file": str(filepath), "error": "Not a file"}
    
    try:
        code = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"file": str(filepath), "error": f"Cannot read file: {e}"}
    
    language = detect_language(filepath)
    
    print(f"📝 Reviewing: {filepath.name} ({language})...")
    
    review = review_code(
        code=code,
        filename=filepath.name,
        language=language,
        model=model,
        custom_prompt=custom_prompt,
        max_tokens=max_tokens,
        api_key=api_key
    )
    
    return {
        "file": str(filepath),
        "language": language,
        "review": review
    }


def review_directory(
    dirpath: Path,
    extensions: list[str],
    model: str,
    recursive: bool = False,
    custom_prompt: Optional[str] = None,
    max_tokens: int = 4096,
    api_key: Optional[str] = None
) -> list[dict]:
    """Review all matching files in a directory."""
    results = []
    
    pattern = "**/*" if recursive else "*"
    
    for ext in extensions:
        for filepath in dirpath.glob(f"{pattern}{ext}"):
            if filepath.is_file():
                result = review_file(filepath, model, custom_prompt, max_tokens, api_key)
                results.append(result)
    
    return results


def print_review(result: dict, output_format: str = "text"):
    """Print review result."""
    if output_format == "json":
        print(json.dumps(result, indent=2))
        return
    
    print("\n" + "=" * 60)
    print(f"📄 File: {result['file']}")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"🔤 Language: {result.get('language', 'unknown')}")
        print("-" * 60)
        print(result.get("review", "No review generated"))
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Reviewer - Analyze code using Anthropic Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.cs                          Review a single file
  %(prog)s src/ -e .cs .py                  Review all .cs and .py files in src/
  %(prog)s src/ -e .cs -r                   Review recursively
  %(prog)s file.cs --json                   Output as JSON
  %(prog)s file.cs -m claude-3-opus-20240229  Use different model

Environment:
  ANTHROPIC_API_KEY    Your Anthropic API key (or use --api-key)
        """
    )
    
    parser.add_argument(
        "path",
        type=Path,
        help="File or directory to review"
    )
    
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        default=[".cs", ".py", ".ts", ".js"],
        help="File extensions to review (default: .cs .py .ts .js)"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Review files recursively in directories"
    )
    
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL})"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Custom prompt template file"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum tokens to generate (default: 4096)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Load custom prompt if provided
    custom_prompt = None
    if args.prompt_file:
        if args.prompt_file.exists():
            custom_prompt = args.prompt_file.read_text()
        else:
            print(f"Warning: Prompt file not found: {args.prompt_file}")
    
    output_format = "json" if args.json else "text"
    
    if args.path.is_file():
        result = review_file(args.path, args.model, custom_prompt, args.max_tokens, args.api_key)
        print_review(result, output_format)
    elif args.path.is_dir():
        results = review_directory(
            args.path,
            args.extensions,
            args.model,
            args.recursive,
            custom_prompt,
            args.max_tokens,
            args.api_key
        )
        for result in results:
            print_review(result, output_format)
        
        if not args.json:
            print(f"\n✅ Reviewed {len(results)} file(s)")
    else:
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
