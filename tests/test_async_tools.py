from __future__ import annotations

import asyncio
import importlib

import pytest


@pytest.fixture
def tools_module(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    import src.tools as tools

    return importlib.reload(tools)


def test_tavily_search_fetches_results_concurrently(monkeypatch, tools_module) -> None:
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    search_calls: list[tuple[str, int, str]] = []

    def fake_search(query: str, max_results: int, topic: str):
        search_calls.append((query, max_results, topic))
        return {
            "results": [
                {"url": "https://example.com/1", "title": "First"},
                {"url": "https://example.com/2", "title": "Second"},
            ]
        }

    async def fake_fetch_webpage_content(client, url: str, timeout: float = 10.0) -> str:
        return f"content for {url}"

    monkeypatch.setattr(tools_module, "tavily_client", type("FakeClient", (), {"search": staticmethod(fake_search)})())
    monkeypatch.setattr(tools_module.httpx, "AsyncClient", lambda **kwargs: FakeAsyncClient())
    monkeypatch.setattr(tools_module, "fetch_webpage_content", fake_fetch_webpage_content)

    result = asyncio.run(tools_module.tavily_search.ainvoke({"query": "async python"}))

    assert search_calls == [("async python", 1, "general")]
    assert "Found 2 result(s)" in result
    assert "content for https://example.com/1" in result
    assert "content for https://example.com/2" in result


def test_record_source_metadata_returns_markdown(tools_module) -> None:
    result = asyncio.run(
        tools_module.record_source_metadata.ainvoke(
        {
            "request": {
                "question_title": "Question",
                "sources": [
                    {
                        "title": "Source Title",
                        "url": "https://example.com",
                        "publisher": "Example",
                    }
                ],
            }
        }
    )
    )

    assert "# Source Metadata Log: Question" in result
    assert "- Title: Source Title" in result
