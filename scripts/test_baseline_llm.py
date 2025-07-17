#!/usr/bin/env python
"""
Test script for the BaselineLLM service.
Tests both OpenAI and Anthropic integration.
"""

import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.baseline_llm import BaselineLLM
from core.config import get_config


def test_baseline_llm():
    """Test the BaselineLLM service with various questions."""
    console = Console()

    console.print(
        Panel.fit(
            "[bold]BaselineLLM Service Test[/bold]\n"
            "Testing OpenAI and Anthropic integration",
            border_style="blue",
        )
    )

    # Initialize LLM service
    try:
        console.print("\n[yellow]Initializing BaselineLLM service...[/yellow]")
        llm = BaselineLLM()
        config = get_config()
        console.print("[green]✓ BaselineLLM initialized successfully![/green]")
        console.print(f"[dim]Primary provider: {config.llm.primary_provider}[/dim]")
        console.print(f"[dim]Fallback provider: {config.llm.fallback_provider}[/dim]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize BaselineLLM: {str(e)}[/red]")
        return

    # Test questions
    test_questions = [
        {
            "question": "What are the working hours according to Qatar labor law?",
            "category": "Legal/Regulatory",
        },
        {
            "question": "What is the GDP growth rate of Qatar in 2024?",
            "category": "Economic/Statistical",
        },
        {
            "question": "Explain the concept of machine learning in simple terms.",
            "category": "General Knowledge",
        },
        {
            "question": "What are the employee termination procedures?",
            "category": "Legal/Regulatory",
        },
    ]

    # Create results table
    table = Table(title="BaselineLLM Test Results", show_lines=True)
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Question", style="white", width=40)
    table.add_column("Answer", style="green", width=60)
    table.add_column("Provider", style="magenta", width=15)
    table.add_column("Latency (ms)", style="yellow", width=12)
    table.add_column("Tokens", style="blue", width=10)

    # Test each question
    for test_case in test_questions:
        question = test_case["question"]
        category = test_case["category"]

        console.print(f"\n[bold]Testing:[/bold] {question[:50]}...")

        try:
            # Time the response
            start_time = time.time()
            response = llm.draft_sync(question)

            # Add to table
            answer_preview = (
                response.answer[:80] + "..."
                if len(response.answer) > 80
                else response.answer
            )
            table.add_row(
                category,
                question[:40] + "..." if len(question) > 40 else question,
                answer_preview,
                f"{response.provider}\n({response.model})",
                f"{response.latency_ms:.0f}",
                str(response.tokens_used),
            )

        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            table.add_row(
                category,
                question[:40] + "...",
                f"[red]Error: {str(e)[:60]}...[/red]",
                "N/A",
                "N/A",
                "N/A",
            )

    # Display results
    console.print("\n")
    console.print(table)

    # Test fallback mechanism
    console.print("\n[bold yellow]Testing Fallback Mechanism[/bold yellow]")
    console.print("[dim]Simulating primary provider failure...[/dim]")

    # Temporarily break the primary provider
    original_client = None
    if config.llm.primary_provider == "openai":
        original_client = llm.openai_client
        llm.openai_client = None
    else:
        original_client = llm.anthropic_client
        llm.anthropic_client = None

    try:
        response = llm.draft_sync("What is 2+2?")
        console.print(f"[green]✓ Fallback successful! Used {response.provider}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Fallback failed: {str(e)}[/red]")

    # Restore original client
    if config.llm.primary_provider == "openai":
        llm.openai_client = original_client
    else:
        llm.anthropic_client = original_client

    # Summary
    console.print("\n[bold]Test Summary:[/bold]")
    console.print(f"• Primary provider configured: {config.llm.primary_provider}")
    console.print(f"• Fallback provider configured: {config.llm.fallback_provider}")
    console.print(f"• All tests completed")


if __name__ == "__main__":
    test_baseline_llm()
