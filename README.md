# Claude Code Reviewer

A command-line tool that uses Anthropic's Claude API to perform automated code reviews with language-specific best practices.

## Features

- 🔍 **Automated code review** using Claude AI
- 🌐 **Multi-language support** with language-specific prompts
- 📁 **Single file or directory** review modes
- 🎯 **Customizable prompts** for your specific needs
- 📊 **JSON output** for integration with other tools

## Installation

```bash
# Install the required dependency
pip install anthropic
```

## Quick Start

```bash
# Set your API key (or use --api-key flag)
export ANTHROPIC_API_KEY=your-key-here  # Linux/Mac
set ANTHROPIC_API_KEY=your-key-here     # Windows

# Review a single file
python reviewer_claude.py path/to/file.cs

# Review a directory
python reviewer_claude.py src/ -e .cs .py

# Review recursively
python reviewer_claude.py src/ -e .cs -r
```

## Usage

```
python reviewer_claude.py <path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `path` | File or directory to review |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-e, --extensions` | `.cs .py .ts .js` | File extensions to review (for directories) |
| `-r, --recursive` | `false` | Review files recursively in directories |
| `-m, --model` | `claude-sonnet-4-20250514` | Claude model to use |
| `--json` | `false` | Output results as JSON |
| `--prompt-file` | - | Custom prompt template file |
| `--max-tokens` | `4096` | Maximum tokens to generate |
| `--api-key` | - | Anthropic API key (or set env var) |

### Examples

```bash
# Review a C# file
python reviewer_claude.py MyService.cs

# Review all Python and TypeScript files in src/
python reviewer_claude.py src/ -e .py .ts

# Review recursively with JSON output
python reviewer_claude.py src/ -e .cs -r --json

# Use a different Claude model
python reviewer_claude.py file.py -m claude-3-opus-20240229

# Use a custom prompt
python reviewer_claude.py file.go --prompt-file prompts/go.txt

# Increase token limit for longer reviews
python reviewer_claude.py large_file.cs --max-tokens 8192
```

## Supported Languages

The reviewer automatically detects languages by file extension:

| Extension | Language |
|-----------|----------|
| `.cs` | C# |
| `.py` | Python |
| `.js`, `.jsx` | JavaScript |
| `.ts`, `.tsx` | TypeScript |
| `.java` | Java |
| `.go` | Go |
| `.rs` | Rust |
| `.cpp`, `.c` | C/C++ |
| `.rb` | Ruby |
| `.php` | PHP |
| `.swift` | Swift |
| `.kt` | Kotlin |

## Language-Specific Prompts

The reviewer includes specialized prompts for common languages in the `prompts/` directory:

- `csharp.txt` - C# and .NET best practices
- `python.txt` - PEP 8, type hints, pytest patterns
- `typescript.txt` - TypeScript/JavaScript idioms, React patterns
- `go.txt` - Go idioms, concurrency patterns
- `java.txt` - Java best practices, Spring Framework
- `rust.txt` - Ownership, lifetimes, error handling

When reviewing a file, the tool automatically loads the matching prompt if available.

## Extending the Reviewer

### Adding a New Language

1. **Add the extension mapping** in `reviewer_claude.py`:
   ```python
   EXTENSION_MAP = {
       # ... existing mappings ...
       ".scala": "scala",
   }
   ```

2. **Create a prompt file** at `prompts/scala.txt`:
   ```text
   You are an expert Scala code reviewer...
   
   ## 1. Critical Issues
   - ...
   
   File: {filename}
   
   ```{language}
   {code}
   ```
   
   Review:
   ```

### Prompt Template Variables

Your prompt files can use these placeholders:

| Variable | Description |
|----------|-------------|
| `{filename}` | Name of the file being reviewed |
| `{language}` | Detected programming language |
| `{code}` | The source code content |

### Creating Custom Prompts

You can create prompts for specific purposes:

```bash
# Security-focused review
python reviewer_claude.py file.py --prompt-file prompts/security-audit.txt

# Performance review
python reviewer_claude.py file.cs --prompt-file prompts/performance.txt
```

Example custom prompt (`prompts/security-audit.txt`):
```text
You are a security expert. Analyze the following code for vulnerabilities:

- SQL injection
- XSS attacks
- Authentication bypasses
- Sensitive data exposure
- Insecure cryptography

File: {filename}

```{language}
{code}
```

Security Report:
```

## Integration Ideas

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Code Review
  run: |
    pip install anthropic
    python reviewer_claude.py src/ -e .py -r --json > review.json
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python reviewer_claude.py $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$') --json
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

## Available Models

| Model | Description |
|-------|-------------|
| `claude-sonnet-4-20250514` | Fast, balanced (default) |
| `claude-3-opus-20240229` | Most capable, slower |
| `claude-3-haiku-20240307` | Fastest, basic reviews |

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
Set the environment variable or use `--api-key`:
```bash
python reviewer_claude.py file.py --api-key sk-ant-...
```

### "Rate limit exceeded"
Wait a moment and try again, or reduce the number of files being reviewed.

### "Cannot connect to Anthropic API"
Check your internet connection and firewall settings.

## License

MIT License - feel free to use and modify as needed.
