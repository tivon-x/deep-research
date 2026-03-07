"""Rich CLI for the Deep Research agent."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import click
from langgraph.types import Command
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


console = Console()


def _normalize_content(content: Any) -> str:
    """Convert LangChain/LangGraph message content into displayable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    chunks.append(str(item["text"]))
                elif "content" in item:
                    chunks.append(str(item["content"]))
        return "\n".join(chunk for chunk in chunks if chunk.strip())

    return str(content)


def _extract_final_answer(result: dict[str, Any]) -> str:
    """Extract the latest assistant message from graph state."""
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") in {"assistant", "ai"}:
            return _normalize_content(message.get("content", ""))
        msg_type = getattr(message, "type", None)
        if msg_type in {"assistant", "ai"}:
            return _normalize_content(getattr(message, "content", ""))
    return ""


def _extract_interrupt_payload(interrupt_obj: Any) -> dict[str, Any]:
    """Get payload from LangGraph interrupt wrappers."""
    payload = getattr(interrupt_obj, "value", interrupt_obj)
    if isinstance(payload, dict):
        return payload
    return {"message": str(payload)}


def _render_banner() -> None:
    title = Text("Deep Research CLI", style="bold white")
    subtitle = Text("Multi-agent research workflow powered by Deep Agents", style="cyan")
    console.print(Panel.fit(f"{title}\n{subtitle}", border_style="bright_blue", padding=(1, 2)))



def _render_mcp_status(agent_module: Any) -> None:
    mcp_status = getattr(agent_module, "MCP_STATUS", None)
    if not isinstance(mcp_status, dict):
        return

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold cyan", width=14)
    table.add_column(style="white")

    enabled = bool(mcp_status.get("enabled"))
    server_count = int(mcp_status.get("server_count", 0))
    tool_count = int(mcp_status.get("tool_count", 0))
    config_error = str(mcp_status.get("config_error", "")).strip()

    if enabled:
        status_text = "enabled"
    elif server_count > 0 and config_error:
        status_text = "configured but load failed"
    elif server_count > 0:
        status_text = "configured (no tools loaded)"
    else:
        status_text = "disabled"

    table.add_row("MCP Status", status_text)
    table.add_row("MCP Servers", str(server_count))
    table.add_row("MCP Tools", str(tool_count))

    prompt_guidance = bool(mcp_status.get("prompt_guidance_enabled"))
    table.add_row("Prompt MCP", "on" if prompt_guidance else "off")

    capabilities = str(mcp_status.get("capabilities", "")).strip()
    if capabilities:
        table.add_row("Capabilities", capabilities)

    if config_error:
        table.add_row("Load Error", config_error)

    border_style = "green" if enabled else "yellow"
    console.print(Panel(table, title="MCP Configuration", border_style=border_style))


def _render_session_info(thread_id: str, query: str, output_dir: Path) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold cyan", width=12)
    table.add_column(style="white")
    table.add_row("Thread ID", thread_id)
    table.add_row("Start Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("Query", query)
    table.add_row("Output Dir", str(output_dir))
    console.print(Panel(table, title="Session", border_style="cyan"))
    

def _request_approval(interrupt_payload: dict[str, Any]) -> dict[str, Any]:
    action = str(interrupt_payload.get("action", "Review and decide"))
    approval_item = str(interrupt_payload.get("approval_item", ""))
    payload_type = str(interrupt_payload.get("type", ""))

    meta = Table(show_header=False, box=None, pad_edge=False)
    meta.add_column(style="bold yellow", width=8)
    meta.add_column(style="white")
    meta.add_row("Action", action)
    if payload_type:
        meta.add_row("Type", payload_type)

    console.print(Panel(meta, title="Approval Required", border_style="yellow"))

    intro = "Please approve or reject:"
    console.print(Panel(Markdown(intro), border_style="yellow"))

    console.print(
        Panel(
            Markdown(approval_item),
            title="Pending Research Brief",
            border_style="bright_magenta",
        )
    )

    approved = Prompt.ask("Approve? (y/n)", choices=["y", "n"], default="y")
    if approved == "y":
        return {"approved": True}

    reason = Prompt.ask("Rejection reason", default="Need revision")
    return {"approved": False, "reason": reason}


def _file_data_to_text(file_data: Any) -> str:
    if isinstance(file_data, dict):
        content = file_data.get("content")
        if isinstance(content, list):
            return "\n".join(str(line) for line in content)
        if isinstance(content, str):
            return content
    return str(file_data)


def _extract_state_files(
    result: dict[str, Any],
    agent: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    files = result.get("files", {})
    if isinstance(files, dict):
        return files

    state_snapshot = agent.get_state(config)
    values = getattr(state_snapshot, "values", {})
    if isinstance(values, dict):
        snapshot_files = values.get("files", {})
        if isinstance(snapshot_files, dict):
            return snapshot_files

    return {}


def _persist_final_report(
    result: dict[str, Any],
    agent: Any,
    config: dict[str, Any],
    output_dir: Path,
) -> Path | None:
    state_files = _extract_state_files(result, agent, config)
    final_report = state_files.get("/final_report.md")
    if final_report is None:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "final_report.md"
    output_path.write_text(_file_data_to_text(final_report), encoding="utf-8")
    return output_path


def _render_output_files(working_dir: Path) -> None:
    tracked_paths = [
        "research_request.md",
        "research_brief.md",
        "research_verification.md",
        "final_report.md",
    ]
    findings_dir = working_dir / "research_findings"

    table = Table(title="Generated Files", border_style="green")
    table.add_column("Path", style="bold")
    table.add_column("Size", justify="right")

    found = False
    for rel in tracked_paths:
        path = working_dir / rel
        if path.exists() and path.is_file():
            found = True
            table.add_row(rel, f"{path.stat().st_size} B")

    if findings_dir.exists() and findings_dir.is_dir():
        for file in sorted(findings_dir.glob("*.md")):
            found = True
            rel_path = file.relative_to(working_dir)
            table.add_row(str(rel_path), f"{file.stat().st_size} B")

    if found:
        console.print(table)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("query", required=False)
@click.option("--thread-id", default=None, help="Session thread ID for resume/continuation.")
@click.option("--plain", is_flag=True, help="Render final answer as plain text instead of Markdown.")
def main(query: str | None, thread_id: str | None, plain: bool) -> None:
    """Run Deep Research from the terminal with a Rich interface."""
    _render_banner()

    user_query = query or Prompt.ask("What would you like to research?")
    session_thread_id = thread_id or f"research-{uuid4().hex[:8]}"
    try:
        from src import agent as agent_module
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]Failed to initialize agent:[/bold red]\n{exc}",
                title="Startup Error",
                border_style="red",
            )
        )
        raise SystemExit(1) from exc

    agent = agent_module.agent
    output_dir = Path(getattr(agent_module, "WORKING_DIR", Path.cwd()))
    _render_session_info(session_thread_id, user_query, output_dir)
    _render_mcp_status(agent_module)

    config = {"configurable": {"thread_id": session_thread_id}}
    graph_input: dict[str, Any] | Command = {"messages": [{"role": "user", "content": user_query}]}

    while True:
        with console.status("[cyan]Running research workflow...[/cyan]", spinner="dots"):
            result = agent.invoke(graph_input, config=config)

        interrupts = result.get("__interrupt__", [])
        if not interrupts:
            break

        interrupt_payload = _extract_interrupt_payload(interrupts[0])
        approval = _request_approval(interrupt_payload)
        graph_input = Command(resume=approval)

    final_answer = _extract_final_answer(result).strip()
    if not final_answer:
        final_answer = "Workflow completed, but no assistant message was returned."

    persisted_report_path = _persist_final_report(result, agent, config, output_dir)

    console.print()
    console.print(Panel("Research Completed", border_style="green", style="bold green"))
    if plain:
        console.print(final_answer)
    else:
        console.print(Panel(Markdown(final_answer), title="Final Answer", border_style="bright_blue"))

    if persisted_report_path is not None:
        console.print(
            Panel(
                f"Persisted state file to disk:\n[bold]{persisted_report_path}[/bold]",
                title="Final Report Saved",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "No `/final_report.md` found in the current thread state.",
                title="Final Report Not Found",
                border_style="yellow",
            )
        )

    _render_output_files(output_dir)


if __name__ == "__main__":
    main()




