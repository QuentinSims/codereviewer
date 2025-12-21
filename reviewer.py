"""
Local Code Reviewer CLI
Connects to Ollama running locally to review code files.
"""

import argparse
import json
import sys
from pathlib import Path
import requests
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "deepseek-coder-v2:16b"

# Base review prompt - we'll make this configurable per language later
BASE_PROMPT = """You are an expert code reviewer. Analyze the following code and provide:

1. **Issues**: Any bugs, potential errors, or problematic patterns
2. **Improvements**: Suggestions for better code quality, readability, or performance
3. **Security**: Any security concerns if applicable
4. **Summary**: Brief overall assessment

Be concise and actionable. Focus on the most important items.

File: {filename}
Language: {language}

```{language}
{code}
```

Review:"""


def detect_language(filepath: Path) -> str:
    """Detect programming language from file extension."""
    extension_map = {
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
    return extension_map.get(filepath.suffix.lower(), "unknown")


def review_code(
    code: str,
    filename: str,
    language: str,
    model: str = DEFAULT_MODEL,
    custom_prompt: Optional[str] = None,
    ctx_size: int = 8192
) -> str:
    """Send code to Ollama for review."""
    
    prompt = custom_prompt or BASE_PROMPT
    full_prompt = prompt.format(
        filename=filename,
        language=language,
        code=code
    )
    
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,  # Lower for more focused responses
            "num_predict": 2048,  # Max tokens to generate
            "num_ctx": ctx_size,  # Context window - increase if model supports it
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response received")
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Is it running? (docker ps)"
    except requests.exceptions.Timeout:
        return "ERROR: Request timed out. The model might be overloaded."
    except Exception as e:
        return f"ERROR: {str(e)}"


def review_file(filepath: Path, model: str, custom_prompt: Optional[str] = None, ctx_size: int = 8192) -> dict:
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
        ctx_size=ctx_size
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
    ctx_size: int = 8192
) -> list[dict]:
    """Review all matching files in a directory."""
    results = []
    
    pattern = "**/*" if recursive else "*"
    
    for ext in extensions:
        for filepath in dirpath.glob(f"{pattern}{ext}"):
            if filepath.is_file():
                result = review_file(filepath, model, custom_prompt, ctx_size)
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
        description="Local Code Reviewer - Analyze code using local LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.cs                    Review a single file
  %(prog)s src/ -e .cs .py            Review all .cs and .py files in src/
  %(prog)s src/ -e .cs -r             Review recursively
  %(prog)s file.cs --json             Output as JSON
  %(prog)s file.cs -m codellama:13b   Use different model
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
        help=f"Ollama model to use (default: {DEFAULT_MODEL})"
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
        "--ctx-size",
        type=int,
        default=8192,
        help="Context window size (default: 8192, use 16384+ for larger files)"
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
        result = review_file(args.path, args.model, custom_prompt, args.ctx_size)
        print_review(result, output_format)
    elif args.path.is_dir():
        results = review_directory(
            args.path,
            args.extensions,
            args.model,
            args.recursive,
            custom_prompt,
            args.ctx_size
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
