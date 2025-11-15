#!/usr/bin/env python3
"""
GSH Benchmarker CLI - Unified Command Line Interface

A comprehensive benchmarking framework for geospatial services supporting:
- GeoServer WMTS tiles
- G3W (coming soon)  
- PostgreSQL/PostGIS (coming soon)
- GeoNode (coming soon)

Usage:
    python3 -m gsh_benchmarker.cli --service geoserver --url https://example.com/geoserver --layer LayerName -t 100 -c 1,10,100
    python3 -m gsh_benchmarker.cli --service geoserver --comprehensive --url https://example.com/geoserver -t 5000 -c 1,10,100,500,1000
    python3 -m gsh_benchmarker.cli --service geoserver --connectivity --url https://example.com/geoserver
    python3 -m gsh_benchmarker.cli --results
    python3 -m gsh_benchmarker.cli --generate-report

Examples:
    # Test single layer with 100 requests at concurrency levels 1,10,100
    python3 -m gsh_benchmarker.cli --service geoserver --url https://climate-adaptation-services.geospatialhosting.com/geoserver --layer CAS:AfstandTotKoelte -t 100 -c 1,10,100
    
    # Run comprehensive test suite
    python3 -m gsh_benchmarker.cli --service geoserver --comprehensive --url https://climate-adaptation-services.geospatialhosting.com/geoserver -t 5000 -c 1,10,100,500,1000
    
    # Test connectivity to all layers
    python3 -m gsh_benchmarker.cli --service geoserver --connectivity --url https://climate-adaptation-services.geospatialhosting.com/geoserver
    
    # Generate PDF report from existing results
    python3 -m gsh_benchmarker.cli --generate-report
"""

import sys
import argparse
from typing import List, Optional, Dict, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .common.colors import KARTOZA_COLORS
from .common.config import DEFAULT_TOTAL_REQUESTS, CONCURRENCY_LEVELS

console = Console()

# Service type registry - extensible for future services
SUPPORTED_SERVICES = {
    'geoserver': {
        'module': 'gsh_benchmarker.geoserver',
        'tester_class': 'GeoServerTester',
        'description': 'GeoServer WMTS tile benchmarking'
    },
    'g3w': {
        'module': 'gsh_benchmarker.g3w',
        'tester_class': 'G3WTester', 
        'description': 'G3W Suite benchmarking (coming soon)'
    },
    'geonode': {
        'module': 'gsh_benchmarker.geonode',
        'tester_class': 'GeoNodeTester',
        'description': 'GeoNode benchmarking (coming soon)'
    },
    'postgres': {
        'module': 'gsh_benchmarker.postgres',
        'tester_class': 'PostgresTester',
        'description': 'PostgreSQL/PostGIS benchmarking (coming soon)'
    }
}

def show_help():
    """Show detailed help information"""
    help_text = Text()
    help_text.append("GSH Benchmarker Suite", style=f"bold {KARTOZA_COLORS['highlight2']}")
    help_text.append("\n\n")
    help_text.append("A unified benchmarking framework for geospatial services\n", style=f"{KARTOZA_COLORS['highlight3']}")
    help_text.append("\n")
    
    help_text.append("Supported Services:", style=f"bold {KARTOZA_COLORS['highlight1']}")
    help_text.append("\n")
    for service_id, service_info in SUPPORTED_SERVICES.items():
        status = "✅" if service_id == 'geoserver' else "🚧"
        help_text.append(f"  {status} {service_id:<12} - {service_info['description']}\n", 
                        style=f"{KARTOZA_COLORS['highlight3']}")
    
    help_text.append("\n")
    help_text.append("Common Usage Patterns:", style=f"bold {KARTOZA_COLORS['highlight1']}")
    help_text.append("\n")
    help_text.append("  # Non-interactive single layer test\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("  python3 -m gsh_benchmarker.cli --service geoserver \\\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("    --url https://example.com/geoserver \\\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("    --layer LayerName -t 100 -c 1,10,100\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("\n")
    help_text.append("  # Comprehensive test suite\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("  python3 -m gsh_benchmarker.cli --service geoserver \\\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("    --comprehensive --url https://example.com/geoserver \\\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("    -t 5000 -c 1,10,100,500,1000\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("\n")
    help_text.append("  # Generate PDF report from results\n", style=f"{KARTOZA_COLORS['highlight4']}")
    help_text.append("  python3 -m gsh_benchmarker.cli --generate-report\n", style=f"{KARTOZA_COLORS['highlight4']}")
    
    panel = Panel.fit(
        help_text,
        border_style=f"{KARTOZA_COLORS['highlight4']}",
        title="GSH Benchmarker Help",
        padding=(1, 2),
    )
    
    console.print(panel)

def parse_concurrency_levels(concurrency_string: str, max_requests: int = None) -> List[int]:
    """Parse comma-separated concurrency levels and trim based on request count"""
    try:
        concurrency_levels = [int(c.strip()) for c in concurrency_string.split(',')]
        
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
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Invalid concurrency format: {e}[/]")
        fallback = min(100, max_requests or 100) if max_requests else 100
        return [fallback]

def get_service_tester(service_type: str, url: str):
    """Dynamically import and instantiate the appropriate service tester"""
    if service_type not in SUPPORTED_SERVICES:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Unsupported service type: {service_type}[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Supported services: {', '.join(SUPPORTED_SERVICES.keys())}[/]")
        return None
    
    service_info = SUPPORTED_SERVICES[service_type]
    
    try:
        if service_type == 'geoserver':
            from .geoserver import GeoServerTester
            return GeoServerTester(url)
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Service '{service_type}' not yet implemented[/]")
            return None
    except ImportError as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to import {service_type} module: {e}[/]")
        return None

def test_connectivity(service_type: str, url: str):
    """Test connectivity to service"""
    if not url:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ URL is required for non-interactive mode[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Use: --url https://example.com/service[/]")
        return False
    
    tester = get_service_tester(service_type, url)
    if not tester:
        return False
    
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Testing connectivity to {service_type} at {url}[/]")
    
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return False
    
    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Successfully connected to {service_type}[/]")
    console.print(f"[{KARTOZA_COLORS['highlight3']}]📊 Discovered {len(tester.layers)} layers[/]")
    
    # Show layer list
    from rich.table import Table
    table = Table(title=f"{service_type.title()} Layers", show_header=True)
    table.add_column("Layer Name", style=f"{KARTOZA_COLORS['highlight2']}")
    table.add_column("Title", style=f"{KARTOZA_COLORS['highlight3']}")
    
    # Convert dict to list and show first 10 layers
    layer_list = list(tester.layers.values())
    for layer in layer_list[:10]:
        table.add_row(layer.name, layer.title or "No title")
    
    if len(layer_list) > 10:
        table.add_row("...", f"({len(layer_list) - 10} more layers)")
    
    console.print(table)
    return True

def run_single_test(service_type: str, url: str, layer_name: str, requests: int, concurrency_levels: List[int]):
    """Run test for a specific layer"""
    if not url:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ URL is required for non-interactive mode[/]")
        return False
    
    tester = get_service_tester(service_type, url)
    if not tester:
        return False
    
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🎯 Running {service_type} test for layer: {layer_name}[/]")
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Configuration:[/]")
    console.print(f"  • Layer: {layer_name}")
    console.print(f"  • Concurrency levels: {concurrency_levels}")
    console.print(f"  • Requests per test: {requests:,}")
    console.print(f"  • Total tests: {len(concurrency_levels)}")
    console.print(f"  • Total requests: {requests * len(concurrency_levels):,}")
    console.print()
    
    # Discover layers first
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return False
    
    # Run tests for each concurrency level
    results = []
    for concurrency in concurrency_levels:
        result = tester.run_single_test(layer_name, requests, concurrency)
        if result:
            results.append(result)
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Completed test: concurrency {concurrency}, RPS {result.requests_per_second:.1f}[/]")
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed test at concurrency {concurrency}[/]")
    
    if results:
        console.print(f"[{KARTOZA_COLORS['highlight4']}]🎉 Single layer testing completed![/]")
        return True
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ All tests failed[/]")
        return False

def run_comprehensive_test(service_type: str, url: str, requests: int, concurrency_levels: List[int]):
    """Run comprehensive test suite for all layers"""
    if not url:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ URL is required for non-interactive mode[/]")
        return False
    
    tester = get_service_tester(service_type, url)
    if not tester:
        return False
    
    # Discover layers
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Discovering layers...[/]")
    if not tester.discover_layers():
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
        return False
    
    console.print(f"[{KARTOZA_COLORS['highlight2']}]🔥 Running comprehensive {service_type} test suite[/]")
    console.print()
    console.print(f"[{KARTOZA_COLORS['highlight3']}]Configuration:[/]")
    console.print(f"  • Service: {service_type}")
    console.print(f"  • Layers: {len(tester.layers)}")
    console.print(f"  • Concurrency levels: {concurrency_levels}")
    console.print(f"  • Requests per test: {requests:,}")
    console.print(f"  • Total tests: {len(tester.layers) * len(concurrency_levels)}")
    console.print(f"  • Total requests: {requests * len(tester.layers) * len(concurrency_levels):,}")
    console.print()
    
    results = tester.run_comprehensive_test(requests, concurrency_levels)
    
    if results:
        console.print(f"[{KARTOZA_COLORS['highlight4']}]🎉 Comprehensive testing completed![/]")
        return True
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Comprehensive testing failed[/]")
        return False

def generate_report():
    """Generate PDF report from existing results"""
    from .common.pdf_generator import generate_pdf_report
    
    console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Generating PDF report from existing results...[/]")
    
    pdf_path = generate_pdf_report("geoserver", use_reportlab=True)
    
    if pdf_path:
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated successfully![/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Report location: {pdf_path}[/]")
        return True
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to generate PDF report[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Make sure you have test results first[/]")
        return False

def show_results():
    """Show summary of recent results"""
    from .common.reports import ReportGenerator
    
    report_gen = ReportGenerator("geoserver")  # TODO: make service type configurable
    table = report_gen.get_results_summary_from_files()
    
    if table:
        console.print(table)
    else:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ No results found[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Run some tests first to generate results[/]")

def main():
    """Main entry point for unified CLI"""
    parser = argparse.ArgumentParser(
        description="GSH Benchmarker Suite - Unified benchmarking for geospatial services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single layer test
  python3 -m gsh_benchmarker.cli --service geoserver --url https://example.com/geoserver --layer LayerName -t 100 -c 1,10,100
  
  # Comprehensive test  
  python3 -m gsh_benchmarker.cli --service geoserver --comprehensive --url https://example.com/geoserver -t 5000 -c 1,10,100,500,1000
  
  # Test connectivity
  python3 -m gsh_benchmarker.cli --service geoserver --connectivity --url https://example.com/geoserver
  
  # Generate report
  python3 -m gsh_benchmarker.cli --generate-report
        """,
    )
    
    # Service type
    parser.add_argument(
        "--service", "-s",
        choices=list(SUPPORTED_SERVICES.keys()),
        help="Service type to benchmark (geoserver, g3w, geonode, postgres)"
    )
    
    # Service URL
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="Service URL (e.g., https://example.com/geoserver)"
    )
    
    # Test modes
    parser.add_argument(
        "--connectivity", 
        action="store_true", 
        help="Test connectivity and discover layers"
    )
    parser.add_argument(
        "--layer", "--single",
        metavar="LAYER",
        help="Run test for specific layer"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive test suite for all layers"
    )
    
    # Test parameters
    parser.add_argument(
        "--requests", "-t",
        type=int,
        default=DEFAULT_TOTAL_REQUESTS,
        help=f"Number of requests per test (default: {DEFAULT_TOTAL_REQUESTS})"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=str,
        default=",".join(map(str, CONCURRENCY_LEVELS)),
        help=f"Comma-separated concurrency levels (default: {','.join(map(str, CONCURRENCY_LEVELS))})"
    )
    
    # Reporting
    parser.add_argument(
        "--results",
        action="store_true",
        help="Show summary of recent results"
    )
    parser.add_argument(
        "--generate-report", "--report",
        action="store_true",
        help="Generate PDF report from existing results"
    )
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        show_help()
        return
    
    args = parser.parse_args()
    
    # Parse concurrency levels with request count validation
    concurrency_levels = parse_concurrency_levels(args.concurrency, args.requests)
    
    # Handle commands that don't require service type
    if args.results:
        show_results()
        return
    elif args.generate_report:
        generate_report()
        return
    
    # Commands that require service type
    if not args.service:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Service type is required[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Use --service [geoserver|g3w|geonode|postgres][/]")
        return
    
    # Handle service-specific commands
    if args.connectivity:
        test_connectivity(args.service, args.url)
    elif args.layer:
        run_single_test(args.service, args.url, args.layer, args.requests, concurrency_levels)
    elif args.comprehensive:
        run_comprehensive_test(args.service, args.url, args.requests, concurrency_levels)
    else:
        console.print(f"[{KARTOZA_COLORS['highlight1']}]💡 Specify a command: --connectivity, --layer, --comprehensive, --results, or --generate-report[/]")
        show_help()

if __name__ == "__main__":
    main()