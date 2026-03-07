# Deep Research

中文版: [README_zh.md](./README_zh.md)

Deep Research is a multi-agent system designed to autonomously perform high-fidelity research on any subject. Built on the [Deep Agents](https://github.com/deepagents/deepagents) framework, it coordinates a specialized team of AI agents to plan, search, verify, and synthesize information into professional reports.

The system moves beyond simple search-and-summarize loops by treating research as a structured engineering pipeline. It transforms vague user queries into clear research briefs, executes parallel search tasks, audits findings for quality, and generates cited reports with minimal human intervention.

## 🛠️ Tech Stack

- **Framework**: Python 3.12+, Deep Agents (`>=0.4.5`)
- **Orchestration**: LangChain + LangGraph
- **Intelligence**: LangChain OpenAI (supports any OpenAI-compatible API)
- **Search**: Tavily Search API (for high-signal web data and markdown conversion)
- **Interface**: Rich CLI for structured terminal feedback

## 🏗️ Architecture

The system uses a hierarchical "Hub and Spoke" model. A central Orchestrator manages the process and delegates specific technical tasks to four specialized subagents.

| Agent | Model Role | Primary Responsibility |
| :--- | :--- | :--- |
| **Orchestrator** | `MAIN_MODEL_ID` | High-level planning, task delegation, and state management. |
| **Scoping** | `SUBAGENT_MODEL_ID` | Intent analysis and sub-question generation with human approval. |
| **Researcher** | `SUBAGENT_MODEL_ID` | Deep web search via Tavily and raw data extraction. |
| **Verification** | `SUBAGENT_MODEL_ID` | Quality auditing of findings against the initial research brief. |
| **Report Writer** | `SUBAGENT_MODEL_ID` | Synthesis of verified data into a final, cited markdown document. |

## 🔄 How It Works

Deep Research follows a strict 8-step execution pipeline to ensure consistency and depth.

```text
[1. Plan] --> [2. Scope] --> [3. Decompose] --> [4. Research]
                                                     |
[8. Finish] <-- [7. Report] <-- [6. Iterate] <-- [5. Verify]
```

### Step 1 — Plan
The Orchestrator initializes a thread-scoped virtual workspace (StateBackend), creates a task list via `write_todos`, and logs the original request to `/research_request.md`.

### Step 2 — Scope
The Scoping Agent breaks the topic into 2–5 focused sub-questions. It pauses for a **Human-in-the-Loop** interrupt to get sign-off on the research direction before executing any search tasks. In the Rich CLI, the pending approval is rendered as a dedicated `Pending Research Brief` panel so the reviewer can inspect the full brief before approving or rejecting.

### Step 3 — Decompose Research Tasks
The Orchestrator analyzes the brief to determine the required parallelization. It scales from a single task for simple topics up to a configurable maximum (default 3) for complex subjects.

### Step 4 — Execute Research (Parallel)
Each sub-question is handled by an independent Research Agent. These agents fetch full webpage content in markdown and save findings to `/research_findings/`. Search calls are tracked by middleware with a configurable hard cap (`RESEARCH_SEARCH_TOOL_LIMIT`, default `15`).

### Step 5 — Verify
A dedicated Verification Agent audits the findings. It checks for coverage gaps and rates the research as `COMPLETE`, `NEEDS_MINOR_ADDITIONS`, or `NEEDS_MAJOR_REWORK`.

### Step 6 — Iterate (if needed)
If the auditor identifies high-priority gaps, the Orchestrator dispatches targeted follow-up research tasks. The system builds on existing files rather than starting from scratch.

### Step 7 — Write Report
The Report Agent synthesizes all verified findings. It selects an appropriate structure template (comparison, analytical, overview, etc.) and generates a professional report with inline citations at `/final_report.md`.

### Step 8 — Final Check
The Orchestrator performs a final read-through to ensure the user's original question was fully answered, then presents the summary and file path.

## ✨ Key Design Highlights

- **Adaptive Task Decomposition**: The system dynamically scales the number of researchers based on topic complexity rather than using hardcoded thread counts. A narrow question gets one focused agent; a broad topic gets up to three working in parallel.

- **StateBackend as Shared Workspace**: Intermediate artifacts (`/research_brief.md`, `/research_findings/*`, `/research_verification.md`, `/final_report.md`) are stored in thread state rather than local disk. This avoids file collisions in multi-user/server deployments while preserving file-tool workflows.

- **Stateless Subagent Design**: Every subagent call is self-contained. The Orchestrator passes complete context (sub-question, file paths, constraints) on each call, ensuring reliability and making individual agents trivially replaceable.

- **Verification Gate**: No data makes it into the final report without passing a dedicated audit step. The Verification Agent checks coverage against the brief's sub-questions and flags unverified or contradicted claims before synthesis begins.

- **Human-in-the-Loop Scoping**: Uses LangGraph interrupts (`request_approval`) to pause execution and get human sign-off on the Research Brief before any web searches begin — preventing wasted API calls on a misunderstood scope. The CLI surfaces both approval metadata and the full pending brief content for terminal review.

- **Search + Full Content**: Instead of relying on search snippets, the `tavily_search` tool fetches full webpage content and converts it to markdown, giving Research Agents substantially richer material to work with.

- **Multi-Model Architecture**: A powerful model drives the reasoning-heavy Orchestrator; multiple models handle the execution agents. This lets you use a powerful model where it matters and a faster/cheaper model for bulk search work.

- **OpenAI-Compatible Model Flexibility**: Works with any OpenAI-compatible endpoint — OpenAI, Azure OpenAI, Ollama, vLLM, or any other provider — by simply setting `BASE_URL`.

## 📁 File Structure

```text
deep-research/
├── src/
│   ├── agent.py              # Orchestrator definition
│   ├── prompts.py            # System prompts for all five agents
│   ├── tools.py              # tavily_search, think_tool, request_approval
│   ├── llm.py                # ChatOpenAI model instances
│   ├── config.py             # Environment variable loading + limits
│   └── subagents/
│       ├── research_agent.py
│       ├── scoping_agent.py
│       ├── verification_agent.py
│       └── report_agent.py
├── .env.example
├── pyproject.toml
└── langgraph.json
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.12+
- A [Tavily API key](https://tavily.com)
- An OpenAI-compatible API key and endpoint

### 2. Install

```bash
# Using uv (recommended)
uv sync

```

### 3. Configure

Copy `.env.example` to `.env` and fill in your credentials:

```env
API_KEY=your-api-key-here
BASE_URL=https://api.openai.com/v1        # any OpenAI-compatible endpoint
MAIN_MODEL_ID=gpt-4o                      # orchestrator model
SUBAGENT_MODEL_ID=gpt-4o-mini            # research/verification/report model
TAVILY_API_KEY=tvly-your-key-here
RESEARCH_SEARCH_TOOL_LIMIT=15          # optional: max tavily_search calls per research-agent task
```

### 4. Run

Recommended (no packaging required):

```bash
python main.py "Research the latest 2026 changes in U.S. AI chip export controls"
```
Alternative direct module script run:

```bash
python src/cli.py "Research the latest 2026 changes in U.S. AI chip export controls"
```
Interactive mode:

```bash
python main.py
```
Common options:

```bash
python main.py --thread-id my-session "Your query"
python main.py --plain "Your query"
```
--thread-id resumes/continues a session, and --plain prints the final answer as plain text.

If you prefer LangGraph development mode, you can still run:

```bash
langgraph dev
```
The workflow pauses once at scoping for approval, then continues to generate research artifacts.

## Output Files

With `StateBackend`, research artifacts are maintained in the current thread state (virtual filesystem paths like `/research_brief.md`).

The CLI now persists the final report from state to local disk at the end of a run:

| Artifact | Persistence |
| :--- | :--- |
| `/research_request.md`, `/research_brief.md`, `/research_findings/<topic>.md`, `/research_verification.md`, `/final_report.md` | In thread state (`StateBackend`) |
| `research/final_report.md` | Written to local disk by CLI after completion |

---
中文版: [README_zh.md](./README_zh.md)

