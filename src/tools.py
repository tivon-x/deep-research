"""Research Tools.

This module provides search and content processing utilities for the research agent,
using Tavily for URL discovery and fetching full webpage content.
"""

import json
from datetime import datetime
from typing import Any

import httpx
from langchain_core.tools import InjectedToolArg, tool
from langgraph.types import interrupt
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal

tavily_client = TavilyClient()


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching content from {url}: {str(e)}"


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with full webpage content
    """
    # Use Tavily to discover URLs
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )

    # Fetch full content for each URL
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]

        # Fetch webpage content
        content = fetch_webpage_content(url)

        result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
        result_texts.append(result_text)

    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}':

{chr(10).join(result_texts)}"""

    return response


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"




@tool(parse_docstring=True)
def record_source_metadata(question_title: str, sources_json: str) -> str:
    """Generate a normalized source metadata markdown document from structured JSON input.

    Use this tool to build a standards-compliant metadata log for research sources.
    The returned markdown should be written to `/research_sources/<name>.sources.md` using `write_file`.

    Args:
        question_title: Human-readable title for this research question
        sources_json: JSON array string. Each item should include: citation_id, title, url.
            Optional keys: publisher, authors, published_date, evidence_type, relevance.

    Returns:
        Markdown text for the source metadata log file on success.
        On validation failure, returns a machine-readable JSON error string.
    """

    def _error(
        error_code: str,
        message: str,
        *,
        source_index: int | None = None,
        fields: list[str] | None = None,
        details: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "ok": False,
            "error_code": error_code,
            "message": message,
        }
        if source_index is not None:
            payload["source_index"] = source_index
        if fields:
            payload["fields"] = fields
        if details is not None:
            payload["details"] = details
        return json.dumps(payload, ensure_ascii=False)

    try:
        raw_sources = json.loads(sources_json)
    except json.JSONDecodeError as e:
        return _error(
            "INVALID_JSON",
            "sources_json must be a JSON array string.",
            details=str(e),
        )

    if not isinstance(raw_sources, list):
        return _error(
            "INVALID_TOP_LEVEL_TYPE",
            "sources_json must decode to a JSON array.",
            details=f"got={type(raw_sources).__name__}",
        )

    if not raw_sources:
        return _error(
            "EMPTY_SOURCES",
            "sources_json must contain at least one source object.",
        )

    today = datetime.now().strftime("%Y-%m-%d")

    def _txt(value: Any, default: str = "Unknown") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    title_header = _txt(question_title, default="Untitled Question")
    lines: list[str] = [f"# Source Metadata Log: {title_header}", ""]

    for index, item in enumerate(raw_sources, start=1):
        if not isinstance(item, dict):
            return _error(
                "INVALID_SOURCE_TYPE",
                "Each source entry must be a JSON object.",
                source_index=index,
                details=f"got={type(item).__name__}",
            )

        missing_fields = [
            field for field in ("title", "url") if _txt(item.get(field), default="") == ""
        ]
        if missing_fields:
            return _error(
                "MISSING_REQUIRED_FIELDS",
                "Source is missing required fields.",
                source_index=index,
                fields=missing_fields,
            )

        citation_id = _txt(item.get("citation_id"), default=f"[{index}]")
        title = _txt(item.get("title"))
        url = _txt(item.get("url"))
        publisher = _txt(item.get("publisher"))
        authors = _txt(item.get("authors"))
        published_date = _txt(item.get("published_date"))
        evidence_type = _txt(item.get("evidence_type"), default="other")
        relevance = _txt(item.get("relevance"))

        lines.extend(
            [
                f"## Source {index}",
                f"- Citation ID: {citation_id}",
                f"- Title: {title}",
                f"- URL: {url}",
                f"- Publisher / Organization: {publisher}",
                f"- Author(s): {authors}",
                f"- Published Date: {published_date}",
                f"- Accessed Date: {today}",
                f"- Evidence Type: {evidence_type}",
                f"- Relevance: {relevance}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


@tool(parse_docstring=True)
def request_approval(research_brief: str) -> str:
    """
    Request human approval for your research brief before finishing.
    
    Args:
        research_brief: your proposed research brief.
    """
    approval = interrupt({
        "type": "approval_request",
        "action": "Review and approve/reject the research brief",
        "approval_item": research_brief
    })

    if approval.get("approved"):
        return "Your research brief was APPROVED. Proceeding..."
    else:
        return f"Your research brief was REJECTED. Reason: {approval.get('reason', 'No reason provided')}. Please revise the brief and request approval again."