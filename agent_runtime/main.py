"""GitPulse Multi-Agent Orchestration CLI.

Entry point to execute tasks, inspect system status, evaluate quality gates,
and audit execution telemetry.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_runtime.master.graph import MasterGraphOrchestrator
from agent_runtime.shared.permissions import AGENT_WRITE_PERMISSIONS
from agent_runtime.shared.task_store import TaskStore
from agent_runtime.tools.test_tools import TestTools

console = Console()


@click.group()
def cli() -> None:
    """GitPulse Multi-Agent System CLI."""
    pass


@cli.command()
@click.option("--task", "-t", required=True, help="Task prompt or user epic description")
@click.option("--epic-id", "-e", default=None, help="Optional custom Epic ID")
def run(task: str, epic_id: str | None) -> None:
    """Execute a task through the Master Orchestrator hierarchy."""
    console.print(
        Panel(
            f"[bold cyan]Submitting Task to Master Orchestrator:[/bold cyan]\n{task}",
            title="GitPulse MAS",
        )
    )

    orchestrator = MasterGraphOrchestrator()
    result = orchestrator.run_epic(prompt=task, epic_id=epic_id)

    table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Epic ID", result.epic_id)
    table.add_row("Task Type", result.task_type)
    table.add_row(
        "Final State",
        (
            f"[bold green]{result.state.value}[/bold green]"
            if result.state.value == "DONE"
            else f"[bold red]{result.state.value}[/bold red]"
        ),
    )
    table.add_row(
        "Quality Gates",
        "[green]PASSED[/green]" if result.quality_gates_passed else "[red]FAILED[/red]",
    )
    table.add_row(
        "Independent Review",
        "[green]APPROVED[/green]" if result.review_approved else "[yellow]PENDING[/yellow]",
    )
    table.add_row("Subtasks Executed", str(len(result.subtasks)))

    console.print(table)


@cli.command()
def status() -> None:
    """Display active and completed tasks from the Task Store."""
    store = TaskStore()
    tasks = store.list_tasks()

    if not tasks:
        console.print("[yellow]No tasks recorded in Task Store.[/yellow]")
        return

    table = Table(title="GitPulse Task Ledger", show_header=True, header_style="bold blue")
    table.add_column("Task ID", style="cyan")
    table.add_column("State", style="bold")
    table.add_column("Agent")
    table.add_column("Title")
    table.add_column("Updated At")

    for t in tasks:
        state_color = (
            "green"
            if t.state.value == "DONE"
            else ("yellow" if t.state.value == "IN_PROGRESS" else "red")
        )
        table.add_row(
            t.id,
            f"[{state_color}]{t.state.value}[/{state_color}]",
            t.assigned_agent,
            t.title[:40],
            t.updated_at[:19],
        )

    console.print(table)


@cli.command()
def gates() -> None:
    """Evaluate and report the status of all 4 Quality Gates."""
    test_tools = TestTools()
    console.print("[cyan]Evaluating Quality Gates...[/cyan]")
    eval_res = test_tools.evaluate_quality_gates()

    table = Table(title="Quality Gates Audit", show_header=True, header_style="bold green")
    table.add_column("Gate", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row(
        "Gate 1: Static Analysis / Compilation",
        (
            "[green]PASS[/green]"
            if eval_res["gate_1_syntax_compilation"]["passed"]
            else "[red]FAIL[/red]"
        ),
        str(eval_res["gate_1_syntax_compilation"]["details"])[:60],
    )
    table.add_row(
        "Gate 2: Automated Tests",
        (
            "[green]PASS[/green]"
            if eval_res["gate_2_automated_tests"]["passed"]
            else "[red]FAIL[/red]"
        ),
        f"Exit Code: {eval_res['gate_2_automated_tests']['exit_code']}",
    )
    table.add_row(
        "Gate 3: Security & Secrets Audit",
        "[green]PASS[/green]" if eval_res["gate_3_security_audit"]["passed"] else "[red]FAIL[/red]",
        f"Violations: {len(eval_res['gate_3_security_audit']['violations'])}",
    )
    table.add_row(
        "Overall Gate Status",
        (
            "[bold green]ALL GREEN[/bold green]"
            if eval_res["all_gates_passed"]
            else "[bold red]GATES FAILED[/bold red]"
        ),
        (
            "Ready for Independent Code Review"
            if eval_res["all_gates_passed"]
            else "Remediation required"
        ),
    )

    console.print(table)


@cli.command(name="list-agents")
def list_agents() -> None:
    """List all registered agents and their authorized file ownership scopes."""
    table = Table(
        title="GitPulse Agent Ownership Directory", show_header=True, header_style="bold cyan"
    )
    table.add_column("Agent Identifier", style="bold yellow")
    table.add_column("Permitted Write Scopes")

    for agent_id, scopes in sorted(AGENT_WRITE_PERMISSIONS.items()):
        table.add_row(agent_id, "\n".join(scopes))

    console.print(table)


if __name__ == "__main__":
    cli()
