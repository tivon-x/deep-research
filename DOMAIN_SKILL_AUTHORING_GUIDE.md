# Domain Skill Authoring Guide

This guide explains how to write domain-specific skills for the Deep Research multi-agent workflow.

## Purpose

Domain skills customize **how each agent role** works in a specific field (finance, legal, biotech, etc.).
These skills are loaded on demand and should override generic research behavior when relevant.

## Directory Layout

Create one domain folder under `skills/`, then provide role-specific `SKILL.md` files:

```text
skills/
  <domain>/
    orchestrator/
      SKILL.md
    scoping/
      SKILL.md
    research/
      SKILL.md
    verification/
      SKILL.md
    report/
      SKILL.md
```

Only roles with an existing `SKILL.md` are loaded.

## How CLI Loads Skills

Use either:

```bash
python main.py --skills <domain> "Your query"
```

or interactive mode:

```bash
python main.py
```

In interactive mode, you can choose a skill domain first (or choose None), then enter your query.

At runtime (StateBackend), local skill files are seeded into virtual paths:

- `/skills/<domain>/orchestrator/SKILL.md`
- `/skills/<domain>/scoping/SKILL.md`
- `/skills/<domain>/research/SKILL.md`
- `/skills/<domain>/verification/SKILL.md`
- `/skills/<domain>/report/SKILL.md`

## SKILL.md Requirements

Every `SKILL.md` must include YAML frontmatter:

```markdown
---
name: finance-research
description: Domain-specific instructions for finance deep research tasks.
---
```

Then add practical instructions in markdown sections.

Recommended sections:

- `# Overview`
- `## When to Use`
- `## Priority Rules`
- `## Process`
- `## Output Requirements`
- `## Do / Don't`

## Role-Specific Writing Guidance

### `orchestrator/SKILL.md`

Define domain decomposition strategy and delegation rules:

- How to split questions into domain sub-questions
- Which evidence types are mandatory
- How to prioritize follow-up loops
- What quality bar is required before final report handoff

### `scoping/SKILL.md`

Define domain scoping criteria:

- Domain boundaries and exclusions
- Required dimensions for sub-questions
- Risk/ambiguity checks in brief design
- What counts as an acceptable research brief

### `research/SKILL.md`

Define domain evidence collection rules:

- Preferred source hierarchy (e.g., regulator docs > media)
- Domain-specific search keywords/patterns
- Required data points and citation format
- Validation checks before saving findings

### `verification/SKILL.md`

Define domain QA standards:

- Coverage checklist for each sub-question
- Evidence sufficiency criteria
- Contradiction detection rules
- Severity rubric for gaps (CRITICAL/HIGH/LOW)

### `report/SKILL.md`

Define domain reporting style and structure:

- Required sections and ordering
- Domain terminology and precision requirements
- Required caveats, assumptions, and limitations
- Citation density and formatting constraints

## Priority and Conflict Rules

When loaded, skill instructions are expected to take precedence over generic workflow guidance, except:

1. Safety/platform constraints always win.
2. Explicit user requirements in the current task always win.

## Minimal Template

```markdown
---
name: <domain>-<role>
description: Instructions for <role> in <domain> deep research.
---

# <Domain> <Role> Skill

## Overview
[What this role should optimize for in this domain]

## Priority Rules
- Follow this skill before generic workflow instructions.
- If conflict with safety or explicit user constraints, follow those constraints.

## Process
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Requirements
- [Required output format/checklist]

## Do / Don't
- Do: [...]
- Don't: [...]
```

## Common Mistakes

- Writing vague instructions ("do better research") without concrete checks.
- Mixing role responsibilities (e.g., verification logic inside research skill).
- Omitting source quality rules for domains with high factual risk.
- Forgetting explicit output constraints (file path behavior, mandatory sections).
- Using invalid domain names (allowed: letters, numbers, `_`, `-`).

## Practical Tips

- Start with `research` + `verification` first; add other roles as needed.
- Keep instructions executable and testable.
- Prefer short, strict checklists over long prose.
- Version your skills by domain folder naming conventions if needed.
