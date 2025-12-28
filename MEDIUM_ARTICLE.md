# Building Your Personal AI Code Reviewer: Language-Specific Feedback That Actually Understands Your Code

## The Problem: Generic Reviews Miss What Really Matters

You've probably tried asking ChatGPT or Claude to review your code. The feedback you get is... fine. It's generic. "Consider adding error handling." "This could be refactored for clarity." "Add documentation."

But here's what it misses:

**In Python**, it doesn't catch that you're using a mutable default argument that will cause subtle bugs:
```python
def add_item(item, items=[]):  # BUG: Shared mutable default!
    items.append(item)
    return items
```

**In Go**, it doesn't notice your goroutine is leaking because you're not closing a channel:
```go
func processData() {
    ch := make(chan int)
    go func() {
        for i := range ch {  // Will never exit!
            process(i)
        }
    }()
    // Channel never closed - goroutine leaks
}
```

**In TypeScript**, it doesn't warn you that using `any` defeats the entire purpose of TypeScript:
```typescript
function updateUser(data: any) {  // Lost all type safety!
    // What fields does data have? Who knows!
}
```

**In Rust**, it doesn't question why you're calling `unwrap()` in production code where it could panic:
```rust
let file = File::open("config.txt").unwrap();  // Will panic if file missing!
```

What you need isn't a generic code reviewer. You need a **constant companion** that understands the idioms, pitfalls, and best practices of **your language**. A reviewer that knows Python's GIL implications, Go's race detector patterns, TypeScript's strict null checks, or Rust's borrow checker nuances.

I built exactly that. And you can run it locally for free with Ollama, or use Claude API for state-of-the-art reviews. Let me show you how it works.

---

## Two Paths: Privacy-First (Ollama) or Power-First (Claude)

The tool offers two implementations that share the same interface but serve different needs:

### Path 1: `reviewer.py` - Local, Private, Free

**Perfect for:**
- Enterprise codebases that can't leave your network
- Working offline (flights, coffee shops, remote areas)
- Unlimited reviews without API costs
- Experimentation and learning

**What you need:**
- Docker or Ollama installed locally
- A decent GPU (or patience with CPU inference)
- `pip install requests`

**Example usage:**
```bash
# Pull a code-focused model
ollama pull deepseek-coder-v2:16b

# Review a file
python reviewer.py src/UserService.cs

# Review an entire directory
python reviewer.py src/ -e .cs -r
```

### Path 2: `reviewer_claude.py` - Cloud, Powerful, Polished

**Perfect for:**
- Best-in-class code review quality
- No local setup required
- Fast reviews without GPU dependencies
- CI/CD pipeline integration

**What you need:**
- Anthropic API key (from console.anthropic.com)
- `pip install anthropic`

**Example usage:**
```bash
# Set your API key
export ANTHROPIC_API_KEY='sk-ant-...'

# Review a file
python reviewer_claude.py src/UserService.cs

# Review directory with JSON output for CI/CD
python reviewer_claude.py src/ -e .cs -r --json > review.json
```

**Side-by-side comparison:**

| Feature | Ollama (reviewer.py) | Claude (reviewer_claude.py) |
|---------|---------------------|----------------------------|
| **Cost** | Free (local compute) | ~$3-15 per 1M tokens |
| **Privacy** | Code never leaves machine | Code sent to Anthropic |
| **Quality** | Good (open-source models) | Excellent (SOTA) |
| **Setup** | Docker + model download | API key only |
| **Offline** | ✅ Yes | ❌ No |
| **Speed** | Depends on hardware | ~2-5 sec per file |
| **Context** | 8K-16K+ tokens | Model-dependent |

Choose Ollama for privacy and cost, Claude for quality and convenience. The rest of this article applies to both—they share 90% of the same codebase.

---

## Under the Hood: A Systematic Code Walkthrough

Let's walk through how the system works, from CLI input to final review.

### Part 1: Language Detection - Knowing What You're Looking At

The first step is automatic language detection based on file extension:

```python
# From reviewer_claude.py, lines 91-107
EXTENSION_MAP = {
    ".cs": "C#",
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C/C++",
    # ... 12 languages total
}

def detect_language(filepath: Path) -> str:
    """Detect programming language from file extension"""
    ext = filepath.suffix.lower()
    return EXTENSION_MAP.get(ext, "unknown")
```

**Why this matters:** Once we know the language, we can load language-specific prompts instead of generic ones.

When you run:
```bash
python reviewer_claude.py UserService.cs
```

The system detects: `"C#"` → loads `prompts/csharp.txt`

### Part 2: The Prompt System - Your Expert Reviewer's Checklist

This is the secret sauce. Instead of generic prompts, each language gets a comprehensive checklist of what to look for.

**How prompts are selected (reviewer_claude.py, lines 143-147):**

```python
def review_code(code, filename, language, model, ...):
    # Priority: Custom > Language-specific > Base
    if custom_prompt:
        prompt = custom_prompt
    else:
        prompt = load_language_prompt(language) or BASE_PROMPT

    # Replace template variables
    full_prompt = prompt.replace("{filename}", filename)
    full_prompt = full_prompt.replace("{language}", language)
    full_prompt = full_prompt.replace("{code}", code)
```

**Loading language prompts (lines 120-129):**

```python
def load_language_prompt(language: str) -> Optional[str]:
    """Load language-specific prompt from prompts directory"""
    prompts_dir = get_prompts_dir()
    prompt_file = prompts_dir / f"{language.lower()}.txt"

    if prompt_file.exists():
        return prompt_file.read_text(encoding='utf-8')
    return None
```

Let me show you what these prompts actually check for...

### Part 3: Language-Specific Intelligence

Here's what makes each language prompt special:

#### **Python Prompt** (67 lines of expertise)

Checks for:
```
CRITICAL:
- Mutable default arguments (def func(x=[]):)
- Missing type hints in function signatures
- Bare except clauses that swallow all errors
- Using += on lists in loops (use list comprehension)
- Not using 'with' statement for file/resource handling

PERFORMANCE:
- List comprehension vs generator expressions for large data
- Using 'in' on lists instead of sets for membership tests
- Multiple string concatenations (use join())

TESTING:
- pytest fixtures instead of setUp/tearDown
- Mock/patch usage for external dependencies
- Parametrize decorators for test variants
```

**Real example it catches:**

```python
# ❌ BAD - Mutable default argument
def add_to_cart(item, cart=[]):
    cart.append(item)
    return cart

# First call: add_to_cart("apple") → ["apple"]
# Second call: add_to_cart("banana") → ["apple", "banana"]  # OOPS!

# ✅ GOOD - None default with initialization
def add_to_cart(item, cart=None):
    if cart is None:
        cart = []
    cart.append(item)
    return cart
```

#### **Go Prompt** (80 lines of expertise)

Checks for:
```
CRITICAL:
- Goroutine leaks (channels not closed, contexts not cancelled)
- Race conditions in concurrent code
- Errors returned but not checked
- Defer in loops (deferred calls pile up until function exit)

IDIOMS:
- "Accept interfaces, return structs" principle
- Context propagation through function chains
- Error wrapping with fmt.Errorf("%w", err) for error chains
- Table-driven tests for comprehensive coverage

PERFORMANCE:
- Unnecessary pointer usage (Go is call-by-value but cheap copies)
- String concatenation in loops (use strings.Builder)
- Repeated map lookups (cache the value)
```

**Real example it catches:**

```go
// ❌ BAD - Goroutine leak
func fetchData() {
    ch := make(chan Data)
    go func() {
        for item := range ch {  // Never exits!
            process(item)
        }
    }()
    // Forgot to close ch - goroutine runs forever
}

// ✅ GOOD - Proper cleanup
func fetchData() {
    ch := make(chan Data)
    var wg sync.WaitGroup
    wg.Add(1)

    go func() {
        defer wg.Done()
        for item := range ch {
            process(item)
        }
    }()

    // Send data...
    close(ch)  // Signal goroutine to exit
    wg.Wait()  // Wait for cleanup
}
```

#### **TypeScript Prompt** (78 lines of expertise)

Checks for:
```
CRITICAL:
- 'any' usage defeating type safety (use 'unknown' and narrow)
- Missing null checks with strict null checking enabled
- Unhandled promise rejections
- Type assertions (as) hiding potential runtime errors

REACT-SPECIFIC:
- Missing dependencies in useEffect hooks
- Key prop issues in lists
- Unnecessary re-renders (memo, useCallback, useMemo)
- Event handler inline functions recreated every render

SECURITY:
- XSS risks in dangerouslySetInnerHTML
- User input not validated before API calls
- Sensitive data in client-side code
```

**Real example it catches:**

```typescript
// ❌ BAD - Using 'any' loses all type safety
function updateUser(data: any) {
    return api.post('/users', data);
    // What fields should data have? Compiler doesn't know!
}

// ✅ GOOD - Proper types with validation
interface UpdateUserRequest {
    id: string;
    email?: string;
    name?: string;
}

function updateUser(data: UpdateUserRequest) {
    return api.post('/users', data);
    // Compiler ensures correct shape, autocomplete works!
}
```

#### **Rust Prompt** (90 lines of expertise)

Checks for:
```
CRITICAL:
- .unwrap() or .expect() in production code (use proper error handling)
- Unnecessary .clone() calls (understand borrowing instead)
- Unsafe blocks without thorough justification
- Mutex<T> instead of RwLock<T> for read-heavy workloads

IDIOMS:
- Iterator chains vs explicit loops (prefer iterators)
- ? operator for error propagation
- From/Into traits for conversions
- Builder pattern for complex initialization

TESTING:
- Property-based testing with proptest
- #[should_panic] for expected failures
- Benchmark tests with criterion
```

**Real example it catches:**

```rust
// ❌ BAD - unwrap() will panic on error
fn load_config() -> Config {
    let contents = fs::read_to_string("config.toml").unwrap();
    toml::from_str(&contents).unwrap()
}

// ✅ GOOD - Proper error handling
fn load_config() -> Result<Config, Box<dyn std::error::Error>> {
    let contents = fs::read_to_string("config.toml")?;
    let config = toml::from_str(&contents)?;
    Ok(config)
}
```

#### **C# Prompt** (42 lines of expertise)

Checks for:
```
CRITICAL:
- Async methods not awaited properly
- IDisposable objects not disposed (missing using statement)
- LINQ queries enumerated multiple times
- Entity Framework N+1 query problems

MODERN C#:
- Nullable reference types usage
- Pattern matching opportunities
- Record types for immutable data
- Init-only properties
```

**Real example it catches:**

```csharp
// ❌ BAD - Multiple enumeration of IEnumerable
var users = database.Users.Where(u => u.IsActive);
var count = users.Count();  // Query 1
var first = users.First();  // Query 2 - enumerated again!

// ✅ GOOD - Materialize once
var users = database.Users.Where(u => u.IsActive).ToList();
var count = users.Count;   // In-memory
var first = users.First(); // In-memory
```

### Part 4: Making the LLM Call

Once we have the language-specific prompt and code, we send it to the LLM.

**Ollama Version (reviewer.py, lines 75-100):**

```python
def review_code(code, filename, language, model="deepseek-coder-v2:16b", ctx_size=8192):
    # Format prompt with code
    full_prompt = prompt.replace("{filename}", filename)
    full_prompt = full_prompt.replace("{language}", language)
    full_prompt = full_prompt.replace("{code}", code)

    # Prepare Ollama request
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,  # Get complete response
        "options": {
            "temperature": 0.3,    # Low temp = focused, consistent
            "num_predict": 2048,   # Max tokens to generate
            "num_ctx": ctx_size,   # Context window size
        }
    }

    # Call local Ollama instance
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120  # 2 minutes max
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.ConnectionError:
        return "ERROR: Could not connect to Ollama. Is it running?"
    except requests.exceptions.Timeout:
        return "ERROR: Request timed out after 120 seconds"
```

**Claude Version (reviewer_claude.py, lines 161-178):**

```python
def review_code(code, filename, language, api_key, model="claude-sonnet-4-20250514", max_tokens=4096):
    # Format prompt (same as Ollama)
    full_prompt = prompt.replace("{filename}", filename)
    full_prompt = full_prompt.replace("{language}", language)
    full_prompt = full_prompt.replace("{code}", code)

    # Call Claude API
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3,  # Same low temp for consistency
        )
        return message.content[0].text

    except anthropic.AuthenticationError:
        return "ERROR: Invalid API key"
    except anthropic.RateLimitError:
        return "ERROR: Rate limit exceeded"
    except Exception as e:
        return f"ERROR: {e}"
```

**Key design choices:**
- **Temperature 0.3**: Low temperature makes reviews consistent and focused. The same code should get similar feedback each time.
- **Streaming disabled**: We want the complete review, not partial chunks.
- **Generous timeouts**: Code review can take time, especially for complex files.
- **Graceful error handling**: Network issues, auth problems, and timeouts all have clear error messages.

### Part 5: Output Formatting

The system supports two output modes:

**Human-readable (default):**
```
================================================================================
FILE: src/UserService.cs
LANGUAGE: C#
================================================================================

REVIEW:
1. Missing null checks for userId parameter
2. Database connection not disposed properly (missing using statement)
3. Async method GetUserAsync not awaited in calling code
...
```

**JSON mode (for CI/CD):**
```json
[
  {
    "file": "src/UserService.cs",
    "language": "C#",
    "review": "1. Missing null checks...",
    "error": null
  },
  {
    "file": "src/OrderService.cs",
    "language": "C#",
    "review": "1. N+1 query detected...",
    "error": null
  }
]
```

**Implementation (lines 277-295 in reviewer_claude.py):**

```python
def print_review(result: dict, output_format: str = "text"):
    """Print review results in specified format"""
    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=" * 80)
        print(f"FILE: {result['file']}")
        print(f"LANGUAGE: {result['language']}")
        print("=" * 80)

        if result.get("error"):
            print(f"\nERROR: {result['error']}")
        else:
            print(f"\n{result['review']}")
        print()
```

### Part 6: Directory Scanning

Both tools support reviewing entire directories recursively:

```python
def review_directory(dirpath, extensions, model, recursive=False, ...):
    """Review all files in a directory matching extensions"""
    results = []
    path = Path(dirpath)

    # Build glob pattern
    if recursive:
        patterns = [f"**/*{ext}" for ext in extensions]
    else:
        patterns = [f"*{ext}" for ext in extensions]

    # Find all matching files
    files = []
    for pattern in patterns:
        files.extend(path.glob(pattern))

    # Review each file
    for file_path in files:
        if file_path.is_file():
            result = review_file(file_path, model, ...)
            results.append(result)

            # Print immediately (streaming feedback)
            print_review(result, output_format)

    return results
```

**Example usage:**

```bash
# Review all Python files in src/ recursively
python reviewer_claude.py src/ -e .py -r

# Review TypeScript and JavaScript files
python reviewer_claude.py frontend/ -e .ts .tsx .js .jsx -r

# Output to JSON for processing
python reviewer_claude.py src/ -e .cs -r --json > reviews.json
```

---

## Making It Your Own: Customizing Prompts

The power of this system is that you can customize prompts to match **exactly** how you want to code.

### Example 1: Security-Focused Reviews

Create `prompts/security-audit.txt`:

```text
You are a security-focused code reviewer. Review {filename} ({language}) for:

CRITICAL SECURITY ISSUES:
- SQL injection vulnerabilities
- XSS attack vectors
- CSRF token usage
- Authentication/authorization bypasses
- Sensitive data in logs or error messages
- Cryptographic weaknesses (weak algorithms, hardcoded keys)
- Path traversal vulnerabilities
- Command injection risks
- Insecure deserialization
- Missing input validation

SECURE CODING PRACTICES:
- Principle of least privilege applied
- Defense in depth (multiple layers of security)
- Fail securely (errors don't expose internals)
- Cryptographic randomness for security-sensitive operations
- Proper secret management (no hardcoded credentials)

CODE:
{code}

Format your review as:
1. CRITICAL: [High-severity security issues]
2. HIGH: [Medium-severity security concerns]
3. MEDIUM: [Security best practices violations]
4. LOW: [Security hygiene improvements]
```

**Usage:**
```bash
python reviewer_claude.py auth/LoginService.cs --prompt-file prompts/security-audit.txt
```

### Example 2: Performance-Focused Reviews

Create `prompts/performance.txt`:

```text
You are a performance optimization expert. Review {filename} ({language}) for:

ALGORITHMIC EFFICIENCY:
- Time complexity issues (O(n²) that could be O(n))
- Unnecessary nested loops
- Inefficient data structures (list when set is better)
- Redundant computations that could be cached

MEMORY OPTIMIZATION:
- Memory leaks or unbounded growth
- Large object allocations that could be pooled
- Unnecessary copies of large data structures
- Missing streaming for large datasets

DATABASE/IO:
- N+1 query problems
- Missing database indexes
- Synchronous I/O blocking threads
- Unbatched operations that could be batched

LANGUAGE-SPECIFIC:
- Python: GIL contention, list vs generator
- Go: Goroutine count, channel buffer sizes
- JavaScript: Event loop blocking, memory retention
- C#: Boxing/unboxing, LINQ performance
- Rust: Unnecessary allocations, clone() usage

CODE:
{code}

For each issue, provide:
1. The problem
2. Performance impact (estimated)
3. Suggested fix with code example
```

### Example 3: Team-Specific Style Guide

Create `prompts/team-style.txt` that enforces your team's conventions:

```text
Review {filename} ({language}) against our team coding standards:

NAMING CONVENTIONS:
- Classes: PascalCase (UserService, not userService)
- Functions: camelCase (getUserById, not get_user_by_id)
- Constants: UPPER_SNAKE_CASE (MAX_RETRY_COUNT)
- Private members: _leadingUnderscore

ARCHITECTURE PATTERNS:
- Services must implement IService interface
- Use dependency injection, not new()
- Repository pattern for data access
- DTOs for API boundaries, not domain models

CODE ORGANIZATION:
- Max function length: 50 lines
- Max file length: 300 lines
- Max parameters: 5 (use options object if more)
- Group related functions together

DOCUMENTATION:
- Public APIs must have XML documentation
- Complex algorithms must have explanation comments
- TODOs must have ticket numbers (// TODO: ABC-123)

ERROR HANDLING:
- Never swallow exceptions silently
- Log at appropriate levels (Error, Warn, Info)
- User-facing errors must be localized
- Include correlation IDs for debugging

CODE:
{code}
```

### Example 4: Extending Language Prompts

Let's say you work heavily with Entity Framework in C#. Enhance `prompts/csharp.txt`:

```text
You are an expert C# code reviewer with deep Entity Framework knowledge.

Review {filename} for:

ENTITY FRAMEWORK SPECIFIC:
- N+1 queries (missing Include/ThenInclude)
- Unbounded queries (missing Take/Skip)
- AsNoTracking for read-only queries
- Proper async/await with EF Core (ToListAsync, not ToList)
- DbContext lifecycle (scoped, not singleton)
- Migrations instead of database.EnsureCreated()
- Composite keys properly configured
- Index attributes on frequently queried columns
- Global query filters for soft deletes/multi-tenancy

COMMON EF PITFALLS:
- Selecting entire entities when only few columns needed
- Not using compiled queries for frequently executed queries
- Tracking too many entities in memory
- Multiple SaveChanges in a loop (batch instead)
- Not using transactions for multi-step operations

... (rest of C# prompt)

CODE:
{code}
```

### Example 5: Learning Mode for Junior Developers

Create `prompts/learning.txt`:

```text
You are a patient mentor reviewing code from a junior developer.

For {filename} ({language}), provide:

1. WHAT YOU DID WELL:
   - Acknowledge correct patterns
   - Praise good naming, structure, testing
   - Highlight improvements from previous code

2. CRITICAL ISSUES (must fix):
   - Bugs that would cause failures
   - Security vulnerabilities
   - Performance problems

3. LEARNING OPPORTUNITIES (educational):
   - Alternative approaches with pros/cons
   - Language idioms they should know
   - Design patterns applicable here
   - References to documentation/articles

4. NEXT STEPS:
   - One specific skill to focus on
   - Resources for learning

Tone: Encouraging and educational, not critical. Explain WHY, not just WHAT.

CODE:
{code}
```

**Usage for code review sessions:**
```bash
python reviewer_claude.py student_code.py --prompt-file prompts/learning.txt
```

---

## Advanced Use Cases

### CI/CD Integration

**GitHub Actions Example:**

```yaml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install anthropic

      - name: Run AI Code Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python reviewer_claude.py src/ -e .py -r --json > review.json

      - name: Post Review as Comment
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const reviews = JSON.parse(fs.readFileSync('review.json'));

            let comment = '## 🤖 AI Code Review\n\n';
            reviews.forEach(r => {
              comment += `### ${r.file}\n\`\`\`\n${r.review}\n\`\`\`\n\n`;
            });

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Pre-commit Hook

**`.git/hooks/pre-commit`:**

```bash
#!/bin/bash

# Get staged files
FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|ts|go|rs|cs)$')

if [ -z "$FILES" ]; then
    exit 0
fi

echo "Running AI code review on staged files..."

# Review each file
for file in $FILES; do
    python reviewer_claude.py "$file" --json > /tmp/review_$$.json

    # Check for critical issues
    if grep -q "CRITICAL" /tmp/review_$$.json; then
        echo "❌ Critical issues found in $file"
        cat /tmp/review_$$.json
        rm /tmp/review_$$.json
        exit 1
    fi
done

rm /tmp/review_$$.json
echo "✅ AI review passed"
exit 0
```

### VS Code Integration

**`.vscode/tasks.json`:**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "AI Code Review (Current File)",
      "type": "shell",
      "command": "python",
      "args": [
        "reviewer_claude.py",
        "${file}"
      ],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "AI Code Review (Workspace)",
      "type": "shell",
      "command": "python",
      "args": [
        "reviewer_claude.py",
        "${workspaceFolder}/src",
        "-r",
        "-e", ".py", ".ts", ".js"
      ],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

Then use `Cmd+Shift+P` → "Run Task" → "AI Code Review (Current File)"

---

## Real-World Results

Let me show you what this catches in actual code:

### Example 1: Python FastAPI Application

**Input Code:**
```python
from fastapi import FastAPI

app = FastAPI()

users_db = {}

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    return users_db[user_id]

@app.post("/users")
async def create_user(user_data):
    user_id = str(len(users_db) + 1)
    users_db[user_id] = user_data
    return {"id": user_id}
```

**AI Review Output:**
```
CRITICAL ISSUES:

1. KeyError on missing user (line 8)
   - users_db[user_id] will raise KeyError if user doesn't exist
   - Fix: Return 404 with HTTPException

   async def get_user(user_id: str):
       if user_id not in users_db:
           raise HTTPException(status_code=404, detail="User not found")
       return users_db[user_id]

2. Missing type hints for user_data (line 12)
   - No validation on input data
   - Fix: Create Pydantic model

   from pydantic import BaseModel

   class UserCreate(BaseModel):
       name: str
       email: str

   async def create_user(user_data: UserCreate):
       ...

3. Race condition in user ID generation (line 13)
   - Multiple simultaneous requests could get same ID
   - Fix: Use UUID or database auto-increment

HIGH PRIORITY:

4. In-memory storage loses data on restart
   - Consider proper database (PostgreSQL, MongoDB)

5. No authentication/authorization
   - Anyone can read/create users

STYLE/BEST PRACTICES:

6. Add response models for type safety and API docs
7. Use dependency injection for database connection
8. Add logging for debugging
```

### Example 2: Go Microservice

**Input Code:**
```go
func processOrders(orders []Order) error {
    for _, order := range orders {
        go processOrder(order)  // Process concurrently
    }
    return nil
}

func processOrder(order Order) {
    // Expensive operation
    result := calculateShipping(order)
    saveToDatabase(result)
}
```

**AI Review Output:**
```
CRITICAL ISSUES:

1. Goroutine leak - no way to know when processing completes
   - Parent function returns immediately
   - No error handling from goroutines
   - Fix: Use sync.WaitGroup or errgroup

   func processOrders(orders []Order) error {
       var wg sync.WaitGroup
       errChan := make(chan error, len(orders))

       for _, order := range orders {
           wg.Add(1)
           order := order  // Capture loop variable!

           go func() {
               defer wg.Done()
               if err := processOrder(order); err != nil {
                   errChan <- err
               }
           }()
       }

       wg.Wait()
       close(errChan)

       // Check for errors
       for err := range errChan {
           if err != nil {
               return err
           }
       }
       return nil
   }

2. Missing loop variable capture (line 2)
   - All goroutines may process the same (last) order
   - Classic Go gotcha
   - Fix shown above: order := order

3. No limit on concurrent goroutines
   - Could spawn thousands for large order batches
   - Fix: Use worker pool pattern

   func processOrders(orders []Order) error {
       maxWorkers := 10
       orderChan := make(chan Order, len(orders))

       // Start worker pool
       g, ctx := errgroup.WithContext(context.Background())
       for i := 0; i < maxWorkers; i++ {
           g.Go(func() error {
               for order := range orderChan {
                   if err := processOrder(order); err != nil {
                       return err
                   }
               }
               return nil
           })
       }

       // Send orders to workers
       for _, order := range orders {
           orderChan <- order
       }
       close(orderChan)

       return g.Wait()
   }

4. processOrder doesn't return error
   - Can't propagate database failures
   - Fix: Return error from processOrder
```

### Example 3: TypeScript React Component

**Input Code:**
```typescript
function UserList() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetch('/api/users')
      .then(res => res.json())
      .then(data => setUsers(data));
  }, []);

  return (
    <div>
      {users.map(user => (
        <div onClick={() => deleteUser(user.id)}>
          {user.name}
        </div>
      ))}
    </div>
  );
}

function deleteUser(id) {
  fetch(`/api/users/${id}`, { method: 'DELETE' });
}
```

**AI Review Output:**
```
CRITICAL ISSUES:

1. Missing key prop in list (line 12)
   - React will warn and have reconciliation issues
   - Fix: <div key={user.id} onClick={...}>

2. Unhandled promise rejection in useEffect (line 6)
   - Network errors will be silent
   - Fix:

   useEffect(() => {
     fetch('/api/users')
       .then(res => {
         if (!res.ok) throw new Error('Failed to fetch');
         return res.json();
       })
       .then(data => setUsers(data))
       .catch(err => {
         console.error('Error fetching users:', err);
         // Show error UI to user
       });
   }, []);

3. No TypeScript types (line 2)
   - users is any[], defeats TypeScript purpose
   - Fix:

   interface User {
     id: string;
     name: string;
     email: string;
   }

   const [users, setUsers] = useState<User[]>([]);

4. deleteUser doesn't wait for completion or handle errors (line 21)
   - User might see deleted item still in list
   - Errors are silent
   - Fix:

   async function deleteUser(id: string): Promise<void> {
     try {
       const res = await fetch(`/api/users/${id}`, {
         method: 'DELETE'
       });
       if (!res.ok) throw new Error('Delete failed');

       // Update local state
       setUsers(prev => prev.filter(u => u.id !== id));
     } catch (err) {
       console.error('Error deleting user:', err);
       alert('Failed to delete user');
     }
   }

HIGH PRIORITY:

5. Inline arrow function in onClick recreated every render
   - Performance issue for large lists
   - Fix: Use useCallback or extract to handler

   const handleDelete = useCallback((id: string) => {
     deleteUser(id);
   }, []);

   {users.map(user => (
     <div key={user.id} onClick={() => handleDelete(user.id)}>
       {user.name}
     </div>
   ))}

6. No loading/error states
   - User sees blank screen while loading
   - Add loading spinner and error message UI

STYLE/BEST PRACTICES:

7. Use async/await instead of .then() for consistency
8. Consider useSWR or React Query for data fetching
9. Extract deleteUser to custom hook (useDeleteUser)
```

---

## Getting Started: 5-Minute Setup

### Option 1: Claude (Cloud)

```bash
# 1. Install dependencies
pip install anthropic

# 2. Get API key from https://console.anthropic.com
export ANTHROPIC_API_KEY='sk-ant-...'

# 3. Clone and run
git clone <your-repo>
cd codereviewer
python reviewer_claude.py path/to/your/code.py
```

### Option 2: Ollama (Local)

```bash
# 1. Install Ollama
# macOS/Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Windows:
# Download from https://ollama.com/download

# 2. Pull a code model
ollama pull deepseek-coder-v2:16b
# Or try: codellama:13b, codegemma:7b

# 3. Install Python dependency
pip install requests

# 4. Clone and run
git clone <your-repo>
cd codereviewer
python reviewer.py path/to/your/code.py
```

---

## What's Next: Extending the System

Here are ideas to take this further:

### 1. Add More Languages

Add to `EXTENSION_MAP`:
```python
".scala": "Scala",
".kt": "Kotlin",
".dart": "Dart",
```

Create `prompts/scala.txt`:
```text
Review {filename} for Scala best practices:

FUNCTIONAL PROGRAMMING:
- Avoid var, prefer val
- Use immutable collections
- Avoid null, use Option
- Use for-comprehensions for nested maps/flatMaps

CONCURRENCY:
- Use Future, not Thread
- Prefer Akka actors for stateful concurrency
- Use proper ExecutionContext

... (your expertise here)

CODE:
{code}
```

### 2. Multi-File Context

Enhance to understand imports and dependencies:

```python
def review_with_context(filepath, model, ...):
    # Read main file
    code = filepath.read_text()

    # Find imports
    imports = extract_imports(code, language)

    # Read imported files
    context = ""
    for imp in imports:
        imp_path = resolve_import(imp, filepath)
        if imp_path.exists():
            context += f"\n\n# {imp_path}:\n{imp_path.read_text()}"

    # Include context in prompt
    full_prompt = f"""
    Review {filepath} with context from imported files:

    MAIN FILE ({filepath}):
    {code}

    IMPORTED FILES:
    {context}
    """
```

### 3. Incremental Reviews (Git Integration)

Review only changed code:

```python
def review_git_diff(branch="main", model=...):
    # Get changed files
    result = subprocess.run(
        ["git", "diff", branch, "--name-only"],
        capture_output=True, text=True
    )
    files = result.stdout.strip().split('\n')

    # Review each changed file
    for file in files:
        filepath = Path(file)
        if filepath.suffix in EXTENSION_MAP:
            review_file(filepath, model, ...)
```

### 4. Severity Scoring

Add automatic issue severity:

```python
def parse_review_severity(review_text):
    """Extract issues by severity from review"""
    issues = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }

    current_severity = "medium"
    for line in review_text.split('\n'):
        if "CRITICAL" in line.upper():
            current_severity = "critical"
        elif "HIGH" in line.upper():
            current_severity = "high"
        elif line.strip().startswith(('1.', '2.', '-')):
            issues[current_severity].append(line)

    return issues

def should_block_ci(issues):
    """Determine if review should block CI pipeline"""
    return len(issues["critical"]) > 0 or len(issues["high"]) > 5
```

### 5. Interactive Fix Mode

Let the AI suggest fixes and apply them:

```python
def interactive_review(filepath, model, ...):
    result = review_file(filepath, model, ...)

    print(result["review"])

    if input("\nApply suggested fixes? (y/n): ").lower() == 'y':
        # Use Claude to generate fixed code
        fix_prompt = f"""
        Original code:
        {result["code"]}

        Review feedback:
        {result["review"]}

        Rewrite the code addressing all issues.
        Output ONLY the fixed code, no explanations.
        """

        fixed_code = review_code(fix_prompt, ...)

        # Write back
        filepath.write_text(fixed_code)
        print(f"✅ Applied fixes to {filepath}")
```

---

## Conclusion: Your Constant Coding Companion

You now have a code reviewer that:

✅ **Understands your language** - Python gotchas, Go race conditions, TypeScript `any` abuse
✅ **Works your way** - Free locally with Ollama, or premium with Claude
✅ **Customizes to your needs** - Security audits, performance reviews, team style guides
✅ **Integrates everywhere** - CI/CD, pre-commit hooks, VS Code tasks
✅ **Scales effortlessly** - Single files or entire repositories

The key insight: **Generic code review is useless. Language-specific review is invaluable.**

Instead of "add error handling," you get:
- "Use `Result<T, E>` instead of `unwrap()` (Rust)"
- "Missing null check with strict null checks enabled (TypeScript)"
- "Goroutine leak - channel never closed (Go)"
- "N+1 query - add `.Include()` (C# Entity Framework)"

That's the difference between a chatbot and a coding companion.

**Get started:**
```bash
git clone <your-repo>
cd codereviewer

# Cloud version
export ANTHROPIC_API_KEY='sk-ant-...'
python reviewer_claude.py yourcode.py

# Local version
ollama pull deepseek-coder-v2:16b
python reviewer.py yourcode.py
```

**Customize it:**
1. Edit `prompts/{language}.txt` for your coding style
2. Create `prompts/security-audit.txt` for security reviews
3. Create `prompts/team-style.txt` for your team's conventions

The code is yours. Make it review the way **you** want to code.

---

*Have questions or improvements? The codebase is straightforward - dive in and modify it. That's what it's for.*
