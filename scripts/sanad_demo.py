#!/usr/bin/env python
"""
Enhanced CLI tool demonstrating the complete Sanad flow.
Combines trigger detection, retrieval, and baseline LLM.
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from core.baseline_llm import BaselineLLM
from retrieval.simple_retriever import SimpleRetriever
from rich import print as rprint
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from trigger.detector import TriggerDetector


class SanadCLI:
    """Enhanced CLI for Sanad verification system."""

    def __init__(self):
        """Initialize all components."""
        self.console = Console()

        self.console.print("[bold blue]Initializing Sanad Components...[/bold blue]")

        # Initialize components
        project_root = Path(__file__).parent.parent
        index_dir = project_root / "data" / "index"

        self.retriever = SimpleRetriever(index_dir)
        self.detector = TriggerDetector()
        self.baseline_llm = BaselineLLM()

        self.console.print("[bold green]✓ All components initialized![/bold green]\n")

    def run(self):
        """Run the main CLI loop."""
        self.console.print(
            Panel.fit(
                "[bold]Sanad v2 - Complete Flow Demo[/bold]\n"
                "Trigger → Baseline LLM → Retrieval → Verification",
                border_style="blue",
            )
        )

        while True:
            self.console.print(
                "\n[bold cyan]Enter your query (or 'quit' to exit):[/bold cyan]"
            )
            query = input("> ").strip()

            if query.lower() in ["quit", "exit", "q"]:
                break

            if not query:
                continue

            # Process the query
            self._process_query(query)

    def _process_query(self, query: str):
        """Process a single query through the Sanad pipeline."""
        start_time = time.time()

        # Step 1: Trigger Detection
        self.console.print("\n[bold yellow]Step 1: Trigger Detection[/bold yellow]")
        should_trigger = self.detector.use_sanad(query)
        trigger_reason = (
            self.detector.get_trigger_reason(query)
            if should_trigger
            else "No verification needed"
        )

        trigger_panel = Panel(
            f"[bold]Decision:[/bold] {'✓ YES - Use Sanad' if should_trigger else '✗ NO - Use baseline only'}\n"
            f"[bold]Reason:[/bold] {trigger_reason}",
            title="Trigger Detection",
            border_style="yellow" if should_trigger else "dim",
        )
        self.console.print(trigger_panel)

        # Step 2: Generate Draft Answer
        self.console.print("\n[bold yellow]Step 2: Generate Draft Answer[/bold yellow]")
        try:
            llm_response = self.baseline_llm.draft_sync(query)

            draft_panel = Panel(
                f"[bold]Answer:[/bold] {llm_response.answer}\n\n"
                f"[dim]Provider: {llm_response.provider} ({llm_response.model})\n"
                f"Tokens: {llm_response.tokens_used} | Latency: {llm_response.latency_ms:.0f}ms[/dim]",
                title="Baseline LLM Response",
                border_style="green",
            )
            self.console.print(draft_panel)

        except Exception as e:
            self.console.print(f"[red]Error generating draft: {str(e)}[/red]")
            return

        # Step 3: Retrieval (if triggered)
        if should_trigger:
            self.console.print(
                "\n[bold yellow]Step 3: Document Retrieval[/bold yellow]"
            )

            # Route and retrieve
            category = self.retriever.route(query)
            self.console.print(f"[bold]Routed to category:[/bold] {category}")

            # Get top passages
            passages = self.retriever.search(query, k=5, category=category)

            # Display retrieval results
            retrieval_table = Table(title="Retrieved Passages", show_lines=True)
            retrieval_table.add_column("Rank", style="cyan", width=6)
            retrieval_table.add_column("Score", style="magenta", width=8)
            retrieval_table.add_column("Document", style="green", width=25)
            retrieval_table.add_column("Text Preview", style="white", width=50)

            for i, passage in enumerate(passages, 1):
                text_preview = (
                    passage["text"][:80] + "..."
                    if len(passage["text"]) > 80
                    else passage["text"]
                )
                retrieval_table.add_row(
                    str(i), f"{passage['score']:.3f}", passage["doc_id"], text_preview
                )

            self.console.print(retrieval_table)

            # Step 4: Verification Preview (Agents would run here)
            self.console.print(
                "\n[bold yellow]Step 4: Verification (Preview)[/bold yellow]"
            )

            # Calculate a simple mock Sanad score based on retrieval scores
            avg_retrieval_score = (
                sum(p["score"] for p in passages[:3]) / 3 if passages else 0.0
            )
            mock_sanad_score = min(
                0.95, avg_retrieval_score + 0.3
            )  # Boost score for demo

            # Determine score color
            if mock_sanad_score >= 0.85:
                score_color = "green"
                confidence_level = "High Confidence"
            elif mock_sanad_score >= 0.70:
                score_color = "yellow"
                confidence_level = "Medium Confidence"
            else:
                score_color = "red"
                confidence_level = "Low Confidence"

            verification_panel = Panel(
                f"[bold {score_color}]Sanad Score: {mock_sanad_score:.2f}[/bold {score_color}]\n"
                f"[bold]Confidence Level:[/bold] {confidence_level}\n\n"
                f"[dim]Note: This is a preview. Full verification would run:\n"
                f"• IntegrityAgent (weight: 0.4)\n"
                f"• PrecisionAgent (weight: 0.3)\n"
                f"• ProvenanceAgent (weight: 0.2)\n"
                f"• DomainAgent (weight: 0.1)[/dim]",
                title="Verification Result (Mock)",
                border_style=score_color,
            )
            self.console.print(verification_panel)

        else:
            self.console.print(
                "\n[dim]No verification needed - baseline answer is sufficient.[/dim]"
            )

        # Summary
        elapsed_time = (time.time() - start_time) * 1000
        self.console.print(
            f"\n[bold]Total processing time:[/bold] {elapsed_time:.0f}ms"
        )

        if should_trigger:
            if elapsed_time <= 1000:
                self.console.print(
                    "[bold green]✓ Performance target met (≤1000ms)![/bold green]"
                )
            else:
                self.console.print(
                    f"[bold yellow]⚠ Performance target missed (target: ≤1000ms)[/bold yellow]"
                )


def main():
    """Main entry point."""
    try:
        cli = SanadCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n[bold red]Interrupted by user.[/bold red]")
    except Exception as e:
        print(f"\n[bold red]Error: {e}[/bold red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
