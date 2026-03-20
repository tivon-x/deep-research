from __future__ import annotations


DEFAULT_SEARCH_LIBRARY = {
    "remote work": [
        {
            "title": "Remote Work Productivity Study",
            "url": "https://example.com/remote-work-productivity",
            "content": (
                "A multi-company 2025 study found remote software teams gained productivity "
                "from fewer interruptions, but onboarding and coordination became harder."
            ),
        },
        {
            "title": "Hybrid Collaboration Report",
            "url": "https://example.com/hybrid-collaboration",
            "content": (
                "Hybrid teams with explicit documentation norms reduced meeting load and "
                "reported better decision traceability than office-only teams."
            ),
        },
    ],
    "ai chip export": [
        {
            "title": "Export Control Briefing",
            "url": "https://example.com/export-controls-briefing",
            "content": (
                "The briefing summarizes compliance obligations, licensing scope changes, "
                "and operational risk for AI accelerator shipments."
            ),
        },
        {
            "title": "Semiconductor Policy Analysis",
            "url": "https://example.com/semiconductor-policy-analysis",
            "content": (
                "Analysts compare restrictions across geographies and note uncertainty around "
                "implementation timelines and enforcement guidance."
            ),
        },
    ],
    "open-source llm": [
        {
            "title": "Open Source LLM Landscape",
            "url": "https://example.com/open-source-llm",
            "content": (
                "Recent open-source LLM releases differ on license, context length, and "
                "fine-tuning support. Benchmark claims vary by task."
            ),
        }
    ],
    "supply chain": [
        {
            "title": "Supplier Risk Review",
            "url": "https://example.com/supplier-risk",
            "content": (
                "Supplier concentration and shipping delays remain the largest operational risks. "
                "Firms mitigate them with multi-sourcing and inventory buffers."
            ),
        }
    ],
}


def render_search_payload(query: str, results: list[dict[str, str]]) -> str:
    blocks: list[str] = [f"## Mock Search Results for {query}"]
    for item in results:
        blocks.append(f"### {item['title']}")
        blocks.append(f"**URL:** {item['url']}")
        blocks.append("")
        blocks.append(item["content"])
        blocks.append("")
    return "\n".join(blocks).strip()


def resolve_mock_search_results(query: str) -> str:
    lowered = query.lower()
    for key, results in DEFAULT_SEARCH_LIBRARY.items():
        if key in lowered:
            return render_search_payload(query, results)
    fallback = [
        {
            "title": "General Research Note",
            "url": "https://example.com/general-research-note",
            "content": (
                "This mocked result provides grounded but generic evidence so the agent can "
                "complete the workflow without external web access."
            ),
        }
    ]
    return render_search_payload(query, fallback)

