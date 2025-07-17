#!/usr/bin/env python
"""
CLI tool to test the Sanad retrieval and trigger system.
This demonstrates the first milestone: retrieval + trigger detection.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from retrieval.simple_retriever import SimpleRetriever
from trigger.detector import TriggerDetector
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import time


def main():
    console = Console()
    
    # Initialize components
    console.print("[bold blue]Initializing Sanad Components...[/bold blue]")
    
    project_root = Path(__file__).parent.parent
    index_dir = project_root / "data" / "index"
    
    # Initialize retriever and trigger detector
    retriever = SimpleRetriever(index_dir)
    detector = TriggerDetector()
    
    console.print("[bold green]✓ Components initialized successfully![/bold green]\n")
    
    # CLI loop
    while True:
        console.print("\n[bold cyan]Enter your query (or 'quit' to exit):[/bold cyan]")
        query = input("> ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        # Start timing
        start_time = time.time()
        
        # Check trigger
        console.print("\n[bold yellow]Processing query...[/bold yellow]")
        should_trigger = detector.use_sanad(query)
        trigger_reason = detector.get_trigger_reason(query) if should_trigger else "No verification needed"
        
        # Display trigger result
        trigger_panel = Panel(
            f"[bold]Trigger Decision:[/bold] {'✓ YES' if should_trigger else '✗ NO'}\n"
            f"[bold]Reason:[/bold] {trigger_reason}",
            title="Trigger Detection",
            border_style="yellow" if should_trigger else "dim"
        )
        console.print(trigger_panel)
        
        if should_trigger:
            # Route and retrieve
            category = retriever.route(query)
            console.print(f"\n[bold]Document Category:[/bold] {category}")
            
            # Get top passages
            results = retriever.search(query, k=5, category=category)
            
            # Display results in a table
            table = Table(title="Top 5 Retrieved Passages", show_lines=True)
            table.add_column("Rank", style="cyan", width=6)
            table.add_column("Score", style="magenta", width=8)
            table.add_column("Document", style="green", width=30)
            table.add_column("Text Preview", style="white", width=60)
            
            for i, result in enumerate(results, 1):
                text_preview = result['text'][:100] + "..." if len(result['text']) > 100 else result['text']
                table.add_row(
                    str(i),
                    f"{result['score']:.3f}",
                    result['doc_id'],
                    text_preview
                )
            
            console.print(table)
        else:
            console.print("\n[dim]Query does not require verification. Would be answered by baseline LLM.[/dim]")
        
        # Show timing
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        console.print(f"\n[bold]Processing time:[/bold] {elapsed_time:.2f} ms")
        
        # Check if we meet the <10ms retrieval target
        if should_trigger and elapsed_time < 10:
            console.print("[bold green]✓ Retrieval target met (<10 ms)![/bold green]")
        elif should_trigger:
            console.print(f"[bold red]✗ Retrieval target not met (target: <10 ms, actual: {elapsed_time:.2f} ms)[/bold red]")
            console.print("[dim]Note: This is expected with the simple retriever. FAISS-GPU will meet the target.[/dim]")


if __name__ == "__main__":
    console = Console()
    console.print(Panel.fit(
        "[bold]Sanad v2 - CLI Verification Demo[/bold]\n"
        "Milestone 1: Retrieval + Trigger Detection",
        border_style="blue"
    ))
    
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted by user.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc() 