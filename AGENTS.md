# AGENTS.md — Deep Research Codebase Guide

> Reference for AI coding agents operating in this repository.

## Project Overview

Python 3.12+ multi-agent research system built on **Deep Agents** (`deepagents>=0.4.5`),
orchestrated with **LangChain + LangGraph**. A central Orchestrator delegates to four
specialized subagents (Scoping, Researcher, Verification, Report Writer). No TypeScript.

---

## Environment Setup

```bash
# Install dependencies (uv is the package manager)
uv sync

# Copy and fill credentials
cp .env.example .env
```

Required `.env` variables:

```
API_KEY=          # OpenAI-compatible API key
BASE_URL=         # OpenAI-compatible endpoint (e.g. https://api.openai.com/v1)
MAIN_MODEL_ID=    # Orchestrator model (e.g. gpt-4o)
TAVILY_API_KEY=   # Tavily search API key
```

Optional:
```
REPORT_MODEL_ID / RESEARCH_MODEL_ID / SCOPING_MODEL_ID / VERIFY_MODEL_ID
RESEARCH_SEARCH_TOOL_LIMIT=15   # max tavily_search calls per research agent run
MCP_CONFIG_FILE=mcp_config.json
```

---

## Commands

| Purpose | Command |
|---|---|
| Run CLI (recommended) | `python main.py "Your query"` |
| Run CLI (direct) | `python src/cli.py "Your query"` |
| Interactive mode | `python main.py` |
| With thread resume | `python main.py --thread-id my-session "query"` |
| With skill | `python main.py --skills finance "query"` |
| Plain output | `python main.py --plain "query"` |
| LangGraph dev server | `langgraph dev` |
| Add dependency | `uv add <package>` |
| Run linter | `ruff check src/` |
| Run formatter | `ruff format src/` |

**No test suite is present.** There is no `pytest`, `unittest`, or test directory in this repo.
If adding tests, use `pytest` and place them in a `tests/` directory.

---

## File Structure

```
src/
├── agent.py              # Orchestrator: build_agent(), default agent instance
├── cli.py                # Click CLI entrypoint with async runtime driver
├── config.py             # env var loading, limits (max_concurrent_research_units=3)
├── llm.py                # ChatOpenAI instances per role (temperature=0.0)
├── mcp.py                # MCP config loading, tool initialization, atexit cleanup
├── prompts.py            # All system prompts for all five agents
├── schemas.py            # Pydantic models for tool inputs
├── skills.py             # Skill discovery, path resolution, state seeding
├── tools.py              # LangChain tools: tavily_search, think_tool, request_approval, record_source_metadata
└── subagents/
    ├── research_agent.py
    ├── scoping_agent.py
    ├── verification_agent.py
    └── report_agent.py
middleware/
└── search_usage_limit.py # AgentMiddleware subclass capping tavily_search calls
main.py                   # Thin entrypoint: load_dotenv() then runs the Click CLI
langgraph.json            # LangGraph deployment config
```

---

## Code Style Guidelines

### Python Version & Type Hints

- **Python 3.12+** — use modern union syntax: `str | None` (not `Optional[str]`)
- Use `from __future__ import annotations` at top of files that need forward references
- Annotate all function signatures (params + return type)
- Use `list[str]`, `dict[str, Any]` etc. (not `List`, `Dict` from `typing`)
- Use `Any` from `typing` for truly dynamic values; avoid suppressing type errors

```python
# Correct
def build_research_subagent(skills: list[str] | None = None) -> dict:

# Avoid
def build_research_subagent(skills: Optional[List[str]] = None) -> Dict:
```

### Imports

Order (enforced by ruff/isort):
1. `__future__` imports
2. Standard library
3. Third-party packages
4. Local `src.*` imports (absolute, not relative)

```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel

from src.config import research_search_tool_limit
from src.llm import research_model
```

- Always use **absolute imports** (`from src.config import ...`), never relative (`from .config import ...`)
- Group imports with blank lines between groups; no blank lines within a group

### Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Modules / files | `snake_case` | `research_agent.py` |
| Functions | `snake_case` | `build_research_subagent()` |
| Classes | `PascalCase` | `SearchUsageLimitMiddleware` |
| Constants / env-loaded config | `UPPER_SNAKE_CASE` | `MAIN_MODEL_ID`, `MCP_STATUS` |
| Pydantic models | `PascalCase` | `SourceMetadataInput` |
| Private helpers | `_leading_underscore` | `_load_json_file()` |
| LangGraph tool functions | `snake_case` | `tavily_search`, `think_tool` |

### Functions & Classes

- Prefer `def` over lambda for anything non-trivial
- Prefer `async def` for execution paths that perform model calls, network I/O, state access, or MCP lifecycle work
- Factory functions returning agent config dicts: name them `build_<role>_subagent()` / `build_<role>_agent()`
- Keep module-level initialization minimal — side effects (MCP init, model instantiation) in module scope are intentional but must be documented

### Error Handling

- Use `try/except Exception` only at integration boundaries (file I/O, external API calls, MCP initialization)
- Always log caught exceptions: `logger.warning("...: %s", exc)` — never silently swallow
- Return sensible defaults (empty dict `{}`, empty list `[]`) on non-critical failures
- Raise `ValueError` for invalid config/arguments with a descriptive message
- Do **not** use bare `except:` — always specify the exception type

```python
# Correct
try:
    return json.loads(path.read_text(encoding="utf-8"))
except Exception:
    return {}

# Avoid
try:
    ...
except:
    pass
```

### Pydantic Models

- Use `BaseModel` from `pydantic` for all structured tool inputs/outputs
- Add `Field(description="...")` on every field — these become LLM tool schemas
- Use `field_validator` with `@classmethod` for validation and normalization
- Keep validators in the schema file (`schemas.py`); do not inline validation in tools

### LangChain Tools

- Decorate with `@tool(parse_docstring=True)` — the docstring becomes the LLM-visible description
- Use `Args:` and `Returns:` Google-style docstring sections; these are parsed by LangChain
- Use `Annotated[T, InjectedToolArg]` for arguments injected at runtime (not from LLM)
- Tools return `str`; format multi-section output with markdown headers

### Prompts

- All system prompts live in `src/prompts.py` as module-level string constants (`UPPER_SNAKE_CASE`)
- Use `.format(**kwargs)` for dynamic injection; keep format placeholders documented
- Never embed prompt strings inline in agent/subagent builder functions

### Module-Level State

- Module-level singletons (LLM instances, MCP client, MCP tools list) are intentional
- Register cleanup with `atexit.register()` for resources that need teardown
- Use `logging.getLogger(__name__)` — never `print()` for operational logging

---

## Architecture Patterns

### Adding a New Subagent

1. Create `src/subagents/<role>_agent.py`
2. Add a `build_<role>_subagent(skills: list[str] | None = None) -> dict` factory
3. Add system prompt constant in `src/prompts.py`
4. Add a model instance in `src/llm.py` using the appropriate `SUBAGENT_MODEL_ID` key
5. Register in `src.agent.build_agent()` under `subagents=[...]`
6. Add role to `ROLE_NAMES` in `src/skills.py` if it should support domain skills

### Adding a New Tool

1. Define function in `src/tools.py` (or a new module if complex)
2. Decorate with `@tool(parse_docstring=True)`
3. Add `Args:` / `Returns:` in Google docstring format
4. Add Pydantic input model to `src/schemas.py` if the tool takes structured input
5. Add the tool to the relevant subagent's `tools=[...]` list

### Middleware

- Subclass `AgentMiddleware` from `langchain.agents.middleware`
- Override `wrap_tool_call(request, handler)` — call `handler(request)` to pass through
- Store run-scoped state in `request.state` (dict)
- Add middleware to subagent config: `"middleware": [MyMiddleware()]`

---

## Key Constraints

- **Never commit `.env`** — it is gitignored; use `.env.example` for documentation
- **No local disk writes during research** — artifacts go to `StateBackend` virtual paths (e.g. `/research_brief.md`); only the CLI writes `research/final_report.md` to disk at the end
- `temperature=0.0` on all models — do not change without discussion
- `max_concurrent_research_units = 3` — hardcoded in `config.py`; change there, not inline
- MCP initialization is **explicit and asynchronous at runtime**; initialize it before building the agent and shut it down on process exit
