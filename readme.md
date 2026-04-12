# AI Code Refactorer

An AI-powered CLI tool that automatically refactors Python, Java, and JavaScript source files by applying **SOLID principles** and **Clean Code** best practices — powered by Claude (cloud), Ollama (local), and the Model Context Protocol (MCP).

---

## How it works

```
Input file (.py / .java / .js)
        ↓
  main.py  (CLI)
        ↓
  MCP Server  (reads & writes files)
        ↓
  Claude API / Ollama (analyses + refactors)
        ↓
  Refactored output file + report
```

The tool spawns a local MCP server that exposes file I/O tools to Claude. Claude then runs an agentic loop — reading the file, planning the refactor, producing clean code, writing it to disk, and returning a detailed report of every change made.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| pip | latest |
| Anthropic API key | required for cloud mode |
| Ollama | required for local mode |

---

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:LucasGrc/SmartRefactoring.git
cd ai-code-refactorer
```

### 2. Create and activate a virtual environment

```bash
# Create the venv
python -m venv .venv

# Activate it
# macOS / Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install anthropic openai "mcp[cli]" uv
```

### 4. Set your Anthropic API key

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

> Get your API key at [console.anthropic.com](https://console.anthropic.com).  
> New accounts receive a small free credit to get started.  
> To make the key permanent, add the export line to your `~/.bashrc` or `~/.zshrc`.

### 5. Setup Ollama (Local mode)

#### How to use it

Install the extra dependency for local mode:
```bash
pip install openai
```

Pull a model (one time):
```bash
ollama pull qwen2.5-coder:14b
```

Start Ollama (keep this running in a separate terminal):
```bash
ollama serve
```

Run in local mode — free, no API key needed:
```bash
python main.py refactor examples/BadCode.java --local
python main.py batch src/ --recursive --local
```

Cloud mode still works exactly as before:
```bash
python main.py refactor examples/BadCode.java
```

To switch the local model, just change `LOCAL_MODEL` at the top of `agent.py`:
```python
LOCAL_MODEL = "qwen2.5-coder:7b"   # lighter, faster
LOCAL_MODEL = "qwen2.5-coder:32b"  # heavier, better quality
```

---

## Project structure

```
ai-code-refactorer/
├── main.py                      # CLI entry point
├── mcp_server/
│   ├── __init__.py
│   └── server.py                # MCP server (file I/O tools)
├── refactor/
│   ├── __init__.py
│   └── agent.py                 # Claude agentic loop
├── prompts/
│   ├── __init__.py
│   └── solid_cleancode.py       # System prompt (SOLID + Clean Code rules)
├── examples/
│   ├── BadCode.java             # Sample file with violations
│   └── ComplexBadCode.java      # More complex sample
└── README.md
```

---

## Usage

### Refactor a single file

```bash
python main.py refactor path/to/YourFile.java
```

### Refactor with extra instructions

```bash
python main.py refactor path/to/YourFile.py --instructions "focus on naming and DRY"
```

### Refactor all files in a directory

```bash
python main.py batch src/
```

### Refactor recursively

```bash
python main.py batch src/ --recursive
```

### Inspect a file without refactoring

```bash
python main.py info path/to/YourFile.js
```

### Specify a custom Python interpreter

```bash
python main.py refactor path/to/YourFile.py --python /usr/bin/python3
```

---

## Supported languages

| Language | Extension |
|---|---|
| Python | `.py` |
| Java | `.java` |
| JavaScript | `.js` |
| TypeScript | `.ts` |

---

## What gets refactored

### SOLID principles

| Principle | What the tool fixes |
|---|---|
| **S** — Single Responsibility | Splits God classes and multi-purpose functions |
| **O** — Open/Closed | Replaces if/else chains with strategy pattern or registries |
| **L** — Liskov Substitution | Fixes broken inheritance hierarchies using interfaces |
| **I** — Interface Segregation | Splits fat interfaces into small, focused ones |
| **D** — Dependency Inversion | Injects dependencies instead of hardcoding concretions |

### Clean Code practices

- Intention-revealing names (no `a`, `b`, `x`, `tmp`)
- Named constants instead of magic numbers
- Guard clauses to eliminate deep nesting
- DRY — extracts duplicated logic into shared functions
- Removes silent `catch` blocks and dead code
- Applies language-specific formatting (PEP 8 / Google Java Style / Prettier)

---

## Output

The tool never overwrites your original file. The refactored version is saved as:

```
YourFile_refactored.java
```

After writing the file, Claude prints a **refactoring report** in the terminal:

```
## Refactoring Report
**File:** YourFile.java
**Language:** java

### SOLID Improvements
- S: Extracted DatabaseService and EmailService from the God class ...
- O: Replaced if/else discount chain with DiscountStrategy pattern ...
...

### Clean Code Improvements
- Renamed `a`, `b`, `c` to `baseAmount`, `multiplier`, `additionalCost`
- Replaced magic number 42 with named constant THRESHOLD_VALUE
...
```

---

## Cost estimate

The tool uses **Claude Sonnet** by default. Approximate cost per refactoring run:

| File size | Estimated cost |
|---|---|
| Small (~100 lines) | ~$0.01 |
| Medium (~500 lines) | ~$0.04 |
| Large (~2000 lines) | ~$0.15 |

To reduce costs during testing, switch to Claude Haiku in `refactor/agent.py`:

```python
MODEL = "claude-haiku-4-5-20251001"
```

---

## Troubleshooting

### `ANTHROPIC_API_KEY` not set

```
❌  ANTHROPIC_API_KEY environment variable is not set.
```

Run `export ANTHROPIC_API_KEY=sk-ant-...` and try again.

### Credit balance too low

```
❌  Your credit balance is too low to access the Anthropic API.
```

Add credits at [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing).

### MCP server not found

```
❌  MCP server script not found: .../mcp_server/server.py
```

Make sure you are running `main.py` from the project root directory.

### `mcp` command not found

Use the module directly:

```bash
python -m mcp dev mcp_server/server.py
```

Or install inside the venv:

```bash
pip install "mcp[cli]"
```

---

## Dependencies

```
anthropic
mcp[cli]
uv
```

Install all at once:

```bash
pip install anthropic "mcp[cli]" uv
```

---

## License

MIT