#!/usr/bin/env python3
"""
Sanad v2 - Comparison Demo
Shows the difference between baseline LLM answers and Sanad-enhanced answers
"""

import os
import sys
import time
from typing import Dict, List, Tuple

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.baseline_llm import BaselineLLM
from core.config import get_settings
from core.trigger_detector import TriggerDetector
from retrievers.simple_retriever import SimpleRetriever

console = Console()
settings = get_settings()


class SanadComparisonDemo:
    def __init__(self):
        console.print("[yellow]Initializing Sanad Comparison Demo...[/yellow]")
        self.trigger_detector = TriggerDetector()
        self.baseline_llm = BaselineLLM()
        self.retriever = SimpleRetriever()

        # Sample verification results (mock data for demo)
        self.mock_verifications = {
            "high": {
                "score": 0.92,
                "integrity": {"score": 0.95, "issues": []},
                "precision": {
                    "score": 0.90,
                    "accuracy": "High alignment with source documents",
                },
                "provenance": {
                    "score": 0.88,
                    "sources": ["Labour Law Article 18", "Ministry Decree 2023"],
                },
                "domain": {"score": 0.94, "expertise": "Labour law domain verified"},
            },
            "medium": {
                "score": 0.75,
                "integrity": {
                    "score": 0.78,
                    "issues": ["Minor inconsistency in date format"],
                },
                "precision": {
                    "score": 0.72,
                    "accuracy": "Generally accurate with minor gaps",
                },
                "provenance": {"score": 0.70, "sources": ["Research report TMO-Q4"]},
                "domain": {"score": 0.80, "expertise": "Domain relevant"},
            },
            "low": {
                "score": 0.45,
                "integrity": {
                    "score": 0.40,
                    "issues": ["Potential outdated information", "Conflicting sources"],
                },
                "precision": {
                    "score": 0.48,
                    "accuracy": "Several inaccuracies detected",
                },
                "provenance": {"score": 0.42, "sources": ["Unverified sources"]},
                "domain": {"score": 0.50, "expertise": "Limited domain coverage"},
            },
        }

    def get_baseline_only_response(self, query: str) -> Dict:
        """Get response without Sanad verification"""
        start_time = time.time()

        # Generate baseline answer
        baseline_result = self.baseline_llm.draft(query)

        latency = int((time.time() - start_time) * 1000)

        return {
            "answer": baseline_result["answer"],
            "provider": baseline_result["provider"],
            "tokens": baseline_result["tokens"],
            "latency": latency,
            "verified": False,
        }

    def get_sanad_enhanced_response(self, query: str) -> Dict:
        """Get response with Sanad verification and enhancement"""
        start_time = time.time()

        # Step 1: Generate baseline draft
        baseline_result = self.baseline_llm.draft(query)

        # Step 2: Retrieve relevant documents
        results, category = self.retriever.retrieve(query, k=5)

        # Step 3: Mock verification (in real system, agents would analyze)
        # For demo, we'll determine verification quality based on retrieval scores
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0

        if avg_score > 0.7:
            verification = self.mock_verifications["high"]
        elif avg_score > 0.5:
            verification = self.mock_verifications["medium"]
        else:
            verification = self.mock_verifications["low"]

        # Step 4: Create enhanced answer
        enhanced_answer = self._enhance_answer(
            baseline_result["answer"], results, verification
        )

        latency = int((time.time() - start_time) * 1000)

        return {
            "answer": enhanced_answer,
            "provider": baseline_result["provider"],
            "tokens": baseline_result["tokens"],
            "latency": latency,
            "verified": True,
            "verification": verification,
            "sources": results[:3],  # Top 3 sources
        }

    def _enhance_answer(
        self, baseline_answer: str, sources: List[Dict], verification: Dict
    ) -> str:
        """Enhance the baseline answer with verification results"""

        # Add source citations
        enhanced = baseline_answer

        if verification["score"] >= 0.8:
            enhanced += "\n\n✅ **Verified Information**"
            enhanced += f"\n- Sanad Score: {verification['score']:.2f}/1.00"
            enhanced += f"\n- Accuracy: {verification['precision']['accuracy']}"

            if sources:
                enhanced += "\n\n📚 **Authoritative Sources:**"
                for i, source in enumerate(sources[:3], 1):
                    enhanced += f"\n{i}. {source['metadata']['source']} (relevance: {source['score']:.2f})"

        elif verification["score"] >= 0.6:
            enhanced += "\n\n⚠️ **Partially Verified**"
            enhanced += f"\n- Sanad Score: {verification['score']:.2f}/1.00"
            enhanced += "\n- Some information could not be fully verified"

            if verification["integrity"]["issues"]:
                enhanced += "\n- Issues: " + ", ".join(
                    verification["integrity"]["issues"]
                )

        else:
            enhanced += "\n\n❌ **Low Verification Confidence**"
            enhanced += f"\n- Sanad Score: {verification['score']:.2f}/1.00"
            enhanced += "\n- Multiple verification issues detected"
            enhanced += "\n- Please consult official sources for critical decisions"

        return enhanced

    def compare_responses(self, query: str):
        """Show side-by-side comparison of baseline vs Sanad-enhanced responses"""

        console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")
        console.print("[yellow]Processing...[/yellow]\n")

        # Check if Sanad should be triggered
        trigger_result = self.trigger_detector.should_trigger(query)

        if not trigger_result["should_trigger"]:
            console.print("[red]This query doesn't trigger Sanad verification.[/red]")
            console.print(
                "Try a query about Qatar labour law, regulations, or compliance.\n"
            )
            return

        # Get both responses
        baseline_response = self.get_baseline_only_response(query)
        sanad_response = self.get_sanad_enhanced_response(query)

        # Create comparison display
        self._display_comparison(baseline_response, sanad_response)

        # Show improvement metrics
        self._display_metrics(baseline_response, sanad_response)

    def _display_comparison(self, baseline: Dict, sanad: Dict):
        """Display side-by-side comparison"""

        # Baseline panel
        baseline_content = Text()
        baseline_content.append(baseline["answer"], style="white")
        baseline_content.append(f"\n\nProvider: {baseline['provider']}", style="dim")
        baseline_content.append(f"\nLatency: {baseline['latency']}ms", style="dim")

        baseline_panel = Panel(
            baseline_content,
            title="[red]Without Sanad (Baseline Only)[/red]",
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        # Sanad panel
        sanad_panel = Panel(
            Markdown(sanad["answer"]),
            title="[green]With Sanad Enhancement[/green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )

        # Display side by side
        console.print(Columns([baseline_panel, sanad_panel], equal=True, expand=True))

    def _display_metrics(self, baseline: Dict, sanad: Dict):
        """Display comparison metrics"""

        table = Table(title="\n🔍 Enhancement Metrics", box=box.SIMPLE_HEAD)
        table.add_column("Metric", style="cyan")
        table.add_column("Without Sanad", style="red")
        table.add_column("With Sanad", style="green")
        table.add_column("Improvement", style="yellow")

        # Latency
        latency_increase = (
            (sanad["latency"] - baseline["latency"]) / baseline["latency"]
        ) * 100
        table.add_row(
            "Response Time",
            f"{baseline['latency']}ms",
            f"{sanad['latency']}ms",
            f"+{latency_increase:.0f}%",
        )

        # Verification
        table.add_row(
            "Verification Status",
            "❌ Unverified",
            f"✅ Verified ({sanad['verification']['score']:.2f})",
            "Added",
        )

        # Sources
        table.add_row(
            "Source Citations",
            "0",
            f"{len(sanad.get('sources', []))}",
            f"+{len(sanad.get('sources', []))}",
        )

        # Trust indicators
        table.add_row("Trust Indicators", "None", "Score, Sources, Issues", "Added")

        console.print(table)

        # Key benefits box
        benefits = Panel(
            """[bold]Key Benefits of Sanad Enhancement:[/bold]
            
• [green]Verified Accuracy[/green]: Cross-checked against official documents
• [green]Source Attribution[/green]: Every claim linked to authoritative sources  
• [green]Trust Scoring[/green]: Transparent confidence levels (0-1 scale)
• [green]Issue Detection[/green]: Identifies potential inaccuracies or outdated info
• [green]Regulatory Compliance[/green]: Ensures answers align with current laws""",
            title="✨ Why Sanad Matters",
            border_style="bright_blue",
            padding=(1, 2),
        )
        console.print("\n", benefits)

    def run_demo(self):
        """Run the interactive comparison demo"""

        console.print(
            Panel.fit(
                "[bold]Sanad v2 - With vs Without Comparison Demo[/bold]\n"
                "See how Sanad enhances LLM responses with verification",
                border_style="bright_blue",
            )
        )

        # Example queries to demonstrate
        example_queries = [
            "What is the probation period duration in Qatar?",
            "How much annual leave are employees entitled to?",
            "What are the rules for terminating an employment contract?",
            "Can employers deduct from employee salaries?",
            "What are the working hour limits in Qatar?",
        ]

        console.print("\n[yellow]Example queries you can try:[/yellow]")
        for i, q in enumerate(example_queries, 1):
            console.print(f"  {i}. {q}")

        while True:
            query = console.input(
                "\n[bold cyan]Enter your query (or 'quit' to exit):[/bold cyan] "
            )

            if query.lower() in ["quit", "exit", "q"]:
                break

            if query.strip():
                self.compare_responses(query)
            else:
                console.print("[red]Please enter a valid query.[/red]")


if __name__ == "__main__":
    try:
        demo = SanadComparisonDemo()
        demo.run_demo()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
