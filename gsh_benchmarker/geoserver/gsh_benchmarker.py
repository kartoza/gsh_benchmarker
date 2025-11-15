#!/usr/bin/env python3
"""
GeoServer Load Testing Suite

A comprehensive Python-based load testing framework for GeoServer WMTS tiles
with rich UI components and detailed reporting capabilities.

Usage:
    python3 geotest.py                    # Interactive menu
    python3 geotest.py --help             # Show help
    python3 geotest.py --connectivity     # Test connectivity only
    python3 geotest.py --single LAYER     # Run single layer test
    python3 geotest.py --comprehensive    # Run all tests
    python3 geotest.py --results          # Show results summary

Examples:
    python3 geotest.py --single AfstandTotKoelte
    python3 geotest.py --comprehensive --requests 1000 --concurrency 1,10,100
"""

import sys
import argparse
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import GeoServerTester, MenuInterface, KARTOZA_COLORS, CONCURRENCY_LEVELS
from .subdomain_manager import get_server_url_interactive

console = Console()


def show_help():
    """Show detailed help information"""
    help_text = Text()
    help_text.append(
        "GeoServer Load Testing Suite", style=f"bold {KARTOZA_COLORS['highlight2']}"
    )
    help_text.append("\n\n")
    help_text.append(
        "Available Commands:", style=f"bold {KARTOZA_COLORS['highlight1']}"
    )
    help_text.append("\n")
    help_text.append(
        "  --help              Show this help message\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  --connectivity      Test connectivity to all layers\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  --single LAYER      Run test for specific layer\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  --comprehensive     Run comprehensive test suite\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  --results           Show summary of recent results\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append("\n")
    help_text.append("Options:", style=f"bold {KARTOZA_COLORS['highlight1']}")
    help_text.append("\n")
    help_text.append(
        "  --requests N        Number of requests per test (default: 5000)\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  --concurrency LIST  Comma-separated concurrency levels\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "                      (default: 1,10,100,500,1000,2000,3000,4000,5000)\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append("\n")
    help_text.append("Layer Discovery:", style=f"bold {KARTOZA_COLORS['highlight1']}")
    help_text.append("\n")
    help_text.append(
        "  Layers are discovered dynamically from GeoServer GetCapabilities\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append(
        "  No hardcoded layer list - works with any GeoServer instance\n",
        style=f"{KARTOZA_COLORS['highlight3']}",
    )
    help_text.append("\n")
    help_text.append("Examples:", style=f"bold {KARTOZA_COLORS['highlight1']}")
    help_text.append("\n")
    help_text.append("  python3 geotest.py\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append(
        "  python3 geotest.py --connectivity\n", style=f"{KARTOZA_COLORS['highlight4']}"
    )
    help_text.append(
        "  python3 geotest.py --single AfstandTotKoelte --requests 1000\n",
        style=f"{KARTOZA_COLORS['highlight4']}",
    )
    help_text.append(
        "  python3 geotest.py --comprehensive --concurrency 1,10,100\n",
        style=f"{KARTOZA_COLORS['highlight4']}",
    )

    panel = Panel.fit(
        help_text,
        border_style=f"{KARTOZA_COLORS['highlight4']}",
        title="Help",
        padding=(1, 2),
    )

    console.print(panel)


def test_connectivity(server_url=None):
    """Test connectivity to all layers"""
    # Get server URL interactively if not provided
    if not server_url:
        server_url = get_server_url_interactive()
        if not server_url:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server URL provided[/]")
            return

    tester = GeoServerTester(server_url)

    # Discover layers
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Discovering layers...[/]")
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return

    console.print(
        f"[{KARTOZA_COLORS['highlight2']}]🔍 Testing connectivity to all layers...[/]"
    )
    console.print()

    results = tester.test_all_connectivity()

    from rich.table import Table

    table = Table(title="Connectivity Test Results", show_header=True)
    table.add_column("Layer Name", style=f"{KARTOZA_COLORS['highlight2']}")
    table.add_column("Title", style=f"{KARTOZA_COLORS['highlight1']}")
    table.add_column("Status", justify="center")
    table.add_column("HTTP Code", justify="center")

    all_accessible = True
    for layer_name, (is_accessible, status_code) in results.items():
        layer_info = tester.get_layer_info(layer_name)
        layer_title = layer_info.title if layer_info else layer_name

        if is_accessible:
            status = f"[{KARTOZA_COLORS['highlight4']}]✅ Accessible[/]"
        else:
            status = f"[{KARTOZA_COLORS['alert']}]❌ Failed[/]"
            all_accessible = False

        table.add_row(layer_name, layer_title, status, str(status_code))

    console.print(table)
    console.print()

    if all_accessible:
        console.print(
            f"[{KARTOZA_COLORS['highlight4']}]✅ All layers are accessible![/]"
        )
    else:
        console.print(
            f"[{KARTOZA_COLORS['alert']}]⚠️  Some layers are not accessible[/]"
        )


def run_single_test(layer_name: str, requests: int, concurrency: int, server_url=None):
    """Run a single layer test"""
    # Get server URL interactively if not provided
    if not server_url:
        server_url = get_server_url_interactive()
        if not server_url:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server URL provided[/]")
            return

    tester = GeoServerTester(server_url)

    # Discover layers
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Discovering layers...[/]")
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return

    # Check if layer exists
    layer_info = tester.get_layer_info(layer_name)
    if not layer_info:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Layer not found: {layer_name}[/]")
        console.print(
            f"[{KARTOZA_COLORS['highlight3']}]Available layers: {', '.join(tester.get_layer_list())}[/]"
        )
        return

    console.print(f"[{KARTOZA_COLORS['highlight2']}]⚡ Running single layer test[/]")
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Layer: {layer_info.title}[/]")
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Requests: {requests:,}[/]")
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Concurrency: {concurrency}[/]")
    console.print()

    # Test connectivity first
    is_accessible, status_code = tester.test_connectivity(layer_name)
    if not is_accessible:
        console.print(
            f"[{KARTOZA_COLORS['alert']}]❌ Layer not accessible (HTTP {status_code})[/]"
        )
        return

    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Layer accessible[/]")
    console.print()

    # Run the test
    with console.status(
        f"[{KARTOZA_COLORS['highlight1']}]Running Apache Bench test..."
    ):
        result = tester.run_single_test(layer_name, concurrency, requests)

    if result:
        console.print(
            f"[{KARTOZA_COLORS['highlight4']}]✅ Test completed successfully![/]"
        )
        console.print()

        from rich.table import Table

        table = Table(title="Test Results", show_header=True)
        table.add_column("Metric", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Value", style=f"{KARTOZA_COLORS['highlight1']}")

        table.add_row("Requests per Second", f"{result.requests_per_second:.2f}")
        table.add_row("Mean Response Time", f"{result.mean_response_time:.2f} ms")
        table.add_row(
            "Failed Requests", f"{result.failed_requests}/{result.total_requests}"
        )
        table.add_row("Success Rate", f"{result.success_rate:.1f}%")
        table.add_row("Total Time", f"{result.total_time:.2f} seconds")
        table.add_row("Transfer Rate", f"{result.transfer_rate:.2f} KB/s")

        console.print(table)

        console.print()
        console.print(
            f"[{KARTOZA_COLORS['highlight3']}]Results saved to: {tester.results_dir}/{result.test_id}.*[/]"
        )
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Test failed[/]")


def run_comprehensive_test(
    requests: int, concurrency_levels: List[int], server_url=None
):
    """Run comprehensive test suite"""
    # Get server URL interactively if not provided
    if not server_url:
        server_url = get_server_url_interactive()
        if not server_url:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server URL provided[/]")
            return

    tester = GeoServerTester(server_url)

    # Discover layers
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Discovering layers...[/]")
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return

    console.print(
        f"[{KARTOZA_COLORS['highlight2']}]🔥 Running comprehensive load test suite[/]"
    )
    console.print()
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Configuration:[/]")
    console.print(f"  • Layers: {len(tester.layers)}")
    console.print(f"  • Concurrency levels: {concurrency_levels}")
    console.print(f"  • Requests per test: {requests:,}")
    console.print(f"  • Total tests: {len(tester.layers) * len(concurrency_levels)}")
    console.print(
        f"  • Total requests: {requests * len(tester.layers) * len(concurrency_levels):,}"
    )
    console.print()

    results = tester.run_comprehensive_test(requests, concurrency_levels)

    if results:
        console.print(
            f"[{KARTOZA_COLORS['highlight4']}]✅ Comprehensive testing completed![/]"
        )
        console.print()

        # Summary table
        from rich.table import Table

        table = Table(title="Comprehensive Test Summary", show_header=True)
        table.add_column("Layer", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Tests", justify="center")
        table.add_column(
            "Best RPS", justify="right", style=f"{KARTOZA_COLORS['highlight1']}"
        )
        table.add_column("Worst RPS", justify="right")
        table.add_column(
            "Avg Success Rate", justify="right", style=f"{KARTOZA_COLORS['highlight4']}"
        )

        # Group results by layer
        layer_stats = {}
        for result in results:
            if result.layer not in layer_stats:
                layer_stats[result.layer] = []
            layer_stats[result.layer].append(result)

        for layer_name, layer_results in layer_stats.items():
            layer_info = tester.get_layer_info(layer_name)
            layer_title = layer_info.title if layer_info else layer_name
            test_count = len(layer_results)

            rps_values = [r.requests_per_second for r in layer_results]
            success_rates = [r.success_rate for r in layer_results]

            best_rps = max(rps_values)
            worst_rps = min(rps_values)
            avg_success = sum(success_rates) / len(success_rates)

            table.add_row(
                layer_title,
                str(test_count),
                f"{best_rps:.2f}",
                f"{worst_rps:.2f}",
                f"{avg_success:.1f}%",
            )

        console.print(table)
        console.print()
        console.print(
            f"[{KARTOZA_COLORS['highlight3']}]Results saved to: {tester.results_dir}/[/]"
        )
        console.print(
            f"[{KARTOZA_COLORS['highlight3']}]Generate PDF report with: python3 benchmark_report_generator.py[/]"
        )
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ No test results generated[/]")


def show_results():
    """Show summary of recent results"""
    tester = GeoServerTester()

    console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Recent Test Results[/]")
    console.print()

    summary = tester.get_results_summary()
    if summary:
        console.print(summary)
    else:
        console.print(
            f"[{KARTOZA_COLORS['alert']}]No test results found. Run some tests first![/]"
        )


def parse_concurrency_levels(concurrency_str: str, max_requests: int = None) -> List[int]:
    """Parse comma-separated concurrency levels and trim based on request count"""
    try:
        concurrency_levels = [int(x.strip()) for x in concurrency_str.split(",")]
        
        # Trim concurrency levels that exceed request count (Apache Bench requirement)
        if max_requests:
            original_count = len(concurrency_levels)
            concurrency_levels = [c for c in concurrency_levels if c <= max_requests]
            
            if len(concurrency_levels) < original_count:
                removed_count = original_count - len(concurrency_levels)
                console.print(f"[{KARTOZA_COLORS['highlight3']}]📝 Trimmed {removed_count} concurrency levels that exceed request count ({max_requests})[/]")
                console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Concurrency cannot exceed total requests (Apache Bench limitation)[/]")
        
        return concurrency_levels if concurrency_levels else [min(100, max_requests or 100)]
        
    except ValueError as e:
        console.print(
            f"[{KARTOZA_COLORS['alert']}]❌ Invalid concurrency format: {e}[/]"
        )
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="GeoServer Load Testing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 geotest.py                           # Interactive menu
  python3 geotest.py --connectivity            # Test connectivity
  python3 geotest.py --single "CAS:AfstandTotKoelte" # Test single layer
  python3 geotest.py --comprehensive           # Run all tests
        """,
    )

    # Commands
    parser.add_argument(
        "--connectivity", action="store_true", help="Test connectivity to all layers"
    )
    parser.add_argument("--single", metavar="LAYER", help="Run test for specific layer")
    parser.add_argument(
        "--layer",
        metavar="LAYER",
        help="Run test for specific layer (alias for --single)",
    )
    parser.add_argument(
        "--comprehensive", action="store_true", help="Run comprehensive test suite"
    )
    parser.add_argument(
        "--results", action="store_true", help="Show summary of recent results"
    )

    # Options
    parser.add_argument(
        "--requests",
        type=int,
        default=5000,
        help="Number of requests per test (default: 5000)",
    )
    parser.add_argument(
        "--concurrency",
        type=str,
        default="1,10,100,500,1000,2000,3000,4000,5000",
        help="Comma-separated concurrency levels",
    )
    parser.add_argument(
        "--duration", type=int, help="Duration in seconds (currently not used)"
    )
    parser.add_argument(
        "--output-format",
        action="append",
        help="Output format (json, csv - currently not used)",
    )
    parser.add_argument(
        "--url", type=str, help="GeoServer URL (e.g., https://example.com/geoserver)"
    )

    # If no arguments, show interactive menu
    if len(sys.argv) == 1:
        menu = MenuInterface()
        menu.run()
        return

    args = parser.parse_args()

    # Parse concurrency levels with request count validation
    concurrency_levels = parse_concurrency_levels(args.concurrency, args.requests)

    # Handle commands
    if args.connectivity:
        test_connectivity(args.url)
    elif args.single or args.layer:
        # For single tests, use first concurrency level or default
        concurrency = concurrency_levels[0] if concurrency_levels else 100
        layer_name = args.single or args.layer
        run_single_test(layer_name, args.requests, concurrency, args.url)
    elif args.comprehensive:
        run_comprehensive_test(args.requests, concurrency_levels, args.url)
    elif args.results:
        show_results()
    else:
        show_help()


if __name__ == "__main__":
    main()

