"""Research Tools.

This module provides search and content processing utilities for the research agent,
using Tavily for URL discovery and fetching full webpage content.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
from langchain_core.tools import InjectedToolArg, tool
from langgraph.types import interrupt
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal

from src.schemas import SourceMetadataRequest

tavily_client = TavilyClient()

DEFAULT_HTTP_TIMEOUT = 10.0
DEFAULT_FETCH_CONCURRENCY = 5
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}


async def fetch_webpage_content(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        client: Shared async HTTP client
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown
    """
    try:
        response = await client.get(url, headers=_FETCH_HEADERS, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as exc:
        return f"Error fetching content from {url}: {exc}"


async def _search_tavily(
    query: str,
    max_results: int,
    topic: Literal["general", "news", "finance"],
) -> dict[str, Any]:
    return await asyncio.to_thread(
        tavily_client.search,
        query,
        max_results=max_results,
        topic=topic,
    )


async def _format_search_result(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    result: dict[str, Any],
) -> str:
    url = str(result["url"])
    title = str(result["title"])

    async with semaphore:
        content = await fetch_webpage_content(client, url)

    return f"""## {title}
**URL:** {url}

{content}

---
"""


@tool(parse_docstring=True)
async def tavily_search(
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
    search_results = await _search_tavily(
        query=query,
        max_results=max_results,
        topic=topic,
    )

    results = search_results.get("results", [])
    semaphore = asyncio.Semaphore(DEFAULT_FETCH_CONCURRENCY)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        result_texts = await asyncio.gather(
            *[
                _format_search_result(client, semaphore, result)
                for result in results
            ]
        )

    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}':

{chr(10).join(result_texts)}"""

    return response


@tool(parse_docstring=True)
async def think_tool(reflection: str) -> str:
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
async def record_source_metadata(request: SourceMetadataRequest) -> str:
    """Generate a normalized source metadata markdown document from structured source metadata.

    Use this tool to build a standards-compliant metadata log for research sources.
    The returned markdown should be written to `/research_sources/<name>.sources.md` using `write_file`.

    Args:
        request: Structured request containing the research question title and
            a non-empty list of source metadata objects. Each source must include
            title and url, and may also include citation_id, publisher, authors,
            published_date, evidence_type, and relevance.

    Returns:
        Markdown text for the source metadata log file.
    """

    today = datetime.now().strftime("%Y-%m-%d")

    def _txt(value: Any, default: str = "Unknown") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    title_header = request.question_title
    lines: list[str] = [f"# Source Metadata Log: {title_header}", ""]

    for index, item in enumerate(request.sources, start=1):
        citation_id = _txt(item.citation_id, default=f"[{index}]")
        title = _txt(item.title)
        url = _txt(item.url)
        publisher = _txt(item.publisher)
        authors = _txt(item.authors)
        published_date = _txt(item.published_date)
        evidence_type = _txt(item.evidence_type, default="other")
        relevance = _txt(item.relevance)

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
async def request_approval(research_brief: str) -> str:
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
