"""
Shared report generation utilities for GSH Benchmarker Suite

Provides PDF generation, result consolidation, and report formatting
that can be used across all benchmarker implementations.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from .colors import KARTOZA_COLORS
from .config import REPORTS_DIR, RESULTS_DIR
from .utils import BenchmarkResult

console = Console()


class ReportGenerator:
    """Universal report generator for all benchmarker types"""
    
    def __init__(self, service_type: str, reports_dir: Optional[Path] = None, results_dir: Optional[Path] = None):
        """Initialize report generator"""
        self.service_type = service_type
        self.reports_dir = reports_dir or REPORTS_DIR
        self.results_dir = results_dir or RESULTS_DIR
        
        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
    
    def consolidate_results(
        self, 
        results: List[BenchmarkResult], 
        timestamp: str,
        test_config: Dict[str, Any]
    ) -> Path:
        """
        Consolidate multiple benchmark results into a single report file
        
        Args:
            results: List of benchmark results
            timestamp: Test run timestamp  
            test_config: Configuration used for the test run
            
        Returns:
            Path to the consolidated results file
        """
        consolidated = {
            "test_suite": {
                "name": f"{self.service_type.title()} Comprehensive Benchmark",
                "service_type": self.service_type,
                "timestamp": timestamp,
                "date": datetime.now().isoformat(),
                "total_requests_per_test": test_config.get("total_requests", "unknown"),
                "concurrency_levels": test_config.get("concurrency_levels", []),
                "targets_tested": list(set(r.target for r in results)),
                "total_tests": len(results),
            },
            "configuration": test_config,
            "results": [],
        }
        
        # Add individual test results
        for result in results:
            result_data = {
                "target": result.target,
                "service_type": result.service_type,
                "timestamp": result.timestamp,
                "test_id": result.test_id,
                "total_requests": result.total_requests,
                "concurrency_level": result.concurrency,
                "test_date": datetime.now().isoformat(),
                "results": {
                    "requests_per_second": f"{result.requests_per_second:.2f}",
                    "mean_response_time_ms": f"{result.mean_response_time:.2f}",
                    "failed_requests": str(result.failed_requests),
                    "total_time_seconds": f"{result.total_time:.2f}",
                    "transfer_rate_kbps": f"{result.transfer_rate:.2f}",
                    "success_rate": f"{result.success_rate:.1f}%",
                },
                "metadata": result.metadata or {}
            }
            consolidated["results"].append(result_data)
        
        # Save consolidated results
        consolidated_file = self.results_dir / f"consolidated_{self.service_type}_results_{timestamp}.json"
        with open(consolidated_file, "w") as f:
            json.dump(consolidated, f, indent=2)
        
        console.print(
            f"[{KARTOZA_COLORS['highlight4']}]📋 Consolidated results saved: {consolidated_file}[/]"
        )
        
        return consolidated_file
    
    def create_summary_table(self, results: List[BenchmarkResult]) -> Table:
        """Create a rich summary table of results"""
        if not results:
            return None
        
        table = Table(title=f"{self.service_type.title()} Benchmark Results", show_header=True)
        table.add_column("Target", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Concurrency", justify="center")
        table.add_column("RPS", justify="right", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Avg Time (ms)", justify="right")
        table.add_column("Failed", justify="right", style=f"{KARTOZA_COLORS['alert']}")
        table.add_column("Success Rate", justify="right", style=f"{KARTOZA_COLORS['highlight4']}")
        
        for result in results:
            table.add_row(
                result.target,
                str(result.concurrency),
                f"{result.requests_per_second:.1f}",
                f"{result.mean_response_time:.1f}",
                str(result.failed_requests),
                f"{result.success_rate:.1f}%",
            )
        
        return table
    
    def get_results_summary_from_files(self) -> Optional[Table]:
        """Get a summary table from existing result files"""
        if not self.results_dir.exists():
            return None
        
        # Find JSON result files
        json_files = list(self.results_dir.glob("*.json"))
        if not json_files:
            return None
        
        table = Table(title=f"Recent {self.service_type.title()} Test Results", show_header=True)
        table.add_column("Target", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Concurrency", justify="center")
        table.add_column("RPS", justify="right", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Avg Time (ms)", justify="right")
        table.add_column("Failed", justify="right", style=f"{KARTOZA_COLORS['alert']}")
        table.add_column("Success Rate", justify="right", style=f"{KARTOZA_COLORS['highlight4']}")
        
        # Sort by modification time (newest first)
        json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        for json_file in json_files[:10]:  # Show last 10 results
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                # Skip consolidated result files (they have a different structure)
                if "test_suite" in data or "results" in data and isinstance(data["results"], list):
                    continue
                
                target = data.get("target", data.get("layer", "Unknown"))
                concurrency = data.get("concurrency_level", 0)
                results = data.get("results", {})
                
                # Ensure results is a dict, not a list
                if not isinstance(results, dict):
                    continue
                
                rps = results.get("requests_per_second", "0")
                avg_time = results.get("mean_response_time_ms", "0")
                failed = results.get("failed_requests", "0")
                success_rate = results.get("success_rate", "0")
                
                table.add_row(
                    str(target),
                    str(concurrency),
                    str(rps),
                    str(avg_time),
                    str(failed),
                    str(success_rate),
                )
                
            except (json.JSONDecodeError, KeyError, AttributeError):
                continue
        
        return table
    
    def generate_text_report(self, results: List[BenchmarkResult], output_file: Optional[Path] = None) -> Path:
        """Generate a comprehensive text report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.reports_dir / f"{self.service_type}_report_{timestamp}.txt"
        
        # Calculate summary statistics
        total_tests = len(results)
        avg_rps = sum(r.requests_per_second for r in results) / total_tests if total_tests > 0 else 0
        avg_response_time = sum(r.mean_response_time for r in results) / total_tests if total_tests > 0 else 0
        total_failed = sum(r.failed_requests for r in results)
        avg_success_rate = sum(r.success_rate for r in results) / total_tests if total_tests > 0 else 0
        
        # Group results by target
        targets = {}
        for result in results:
            if result.target not in targets:
                targets[result.target] = []
            targets[result.target].append(result)
        
        report_content = f"""
{self.service_type.upper()} BENCHMARK REPORT
{'=' * 50}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Service Type: {self.service_type.title()}
Total Tests: {total_tests}

SUMMARY STATISTICS
{'-' * 20}
Average RPS: {avg_rps:.2f}
Average Response Time: {avg_response_time:.2f} ms
Total Failed Requests: {total_failed}
Average Success Rate: {avg_success_rate:.1f}%

DETAILED RESULTS BY TARGET
{'-' * 30}
"""
        
        for target, target_results in targets.items():
            report_content += f"\n{target.upper()}\n"
            report_content += "-" * len(target) + "\n"
            
            for result in sorted(target_results, key=lambda x: x.concurrency):
                report_content += f"""
Concurrency: {result.concurrency}
  RPS: {result.requests_per_second:.2f}
  Response Time: {result.mean_response_time:.2f} ms
  Failed: {result.failed_requests}
  Success Rate: {result.success_rate:.1f}%
  Total Time: {result.total_time:.2f} s
  Transfer Rate: {result.transfer_rate:.2f} KB/s
"""
        
        # Write report
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        console.print(f"[{KARTOZA_COLORS['highlight4']}]📄 Text report saved: {output_file}[/]")
        return output_file


def find_latest_report_file(reports_dir: Path, file_pattern: str = "*.pdf") -> Optional[Path]:
    """Find the latest report file in the reports directory"""
    if not reports_dir.exists():
        return None
    
    report_files = list(reports_dir.glob(file_pattern))
    if not report_files:
        return None
    
    return max(report_files, key=lambda p: p.stat().st_mtime)


def execute_external_report_generator(
    script_name: str, 
    working_dir: Optional[Path] = None,
    timeout: int = 300
) -> Tuple[bool, Optional[str]]:
    """
    Execute an external report generation script
    
    Args:
        script_name: Name of the script to execute
        working_dir: Working directory for execution
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        with console.status(f"[{KARTOZA_COLORS['highlight2']}]Executing {script_name}..."):
            result = subprocess.run(
                ["python3", script_name],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        
        if result.returncode == 0:
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ {script_name} executed successfully![/]")
            return True, None
        else:
            error_msg = f"{script_name} failed with code {result.returncode}"
            if result.stderr:
                error_msg += f": {result.stderr}"
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"{script_name} timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, f"{script_name} not found"
    except Exception as e:
        return False, f"Error executing {script_name}: {e}"


def create_benchmark_summary_panel(results: List[BenchmarkResult], service_type: str) -> Panel:
    """Create a rich panel with benchmark summary"""
    if not results:
        return Panel("No results available", title="Summary", border_style=KARTOZA_COLORS['alert'])
    
    # Calculate statistics
    total_tests = len(results)
    avg_rps = sum(r.requests_per_second for r in results) / total_tests
    avg_response_time = sum(r.mean_response_time for r in results) / total_tests
    total_failed = sum(r.failed_requests for r in results)
    avg_success_rate = sum(r.success_rate for r in results) / total_tests
    
    # Get unique targets and concurrency levels
    unique_targets = len(set(r.target for r in results))
    concurrency_levels = sorted(set(r.concurrency for r in results))
    
    summary_text = Text()
    summary_text.append(f"Service: ", style="bold")
    summary_text.append(f"{service_type.title()}\n", style=f"bold {KARTOZA_COLORS['highlight2']}")
    
    summary_text.append(f"Targets: ", style="bold")
    summary_text.append(f"{unique_targets}\n", style=f"{KARTOZA_COLORS['highlight3']}")
    
    summary_text.append(f"Tests: ", style="bold")
    summary_text.append(f"{total_tests}\n", style=f"{KARTOZA_COLORS['highlight3']}")
    
    summary_text.append(f"Concurrency: ", style="bold")
    summary_text.append(f"{min(concurrency_levels)}-{max(concurrency_levels)}\n", style=f"{KARTOZA_COLORS['highlight3']}")
    
    summary_text.append(f"Avg RPS: ", style="bold")
    summary_text.append(f"{avg_rps:.1f}\n", style=f"{KARTOZA_COLORS['highlight1']}")
    
    summary_text.append(f"Avg Response: ", style="bold")
    summary_text.append(f"{avg_response_time:.1f}ms\n", style=f"{KARTOZA_COLORS['highlight3']}")
    
    summary_text.append(f"Failed: ", style="bold")
    summary_text.append(f"{total_failed}\n", style=f"{KARTOZA_COLORS['alert'] if total_failed > 0 else KARTOZA_COLORS['highlight4']}")
    
    summary_text.append(f"Success Rate: ", style="bold")
    summary_text.append(f"{avg_success_rate:.1f}%", style=f"{KARTOZA_COLORS['highlight4'] if avg_success_rate > 95 else KARTOZA_COLORS['alert']}")
    
    return Panel(
        summary_text,
        title=f"{service_type.title()} Benchmark Summary",
        border_style=KARTOZA_COLORS['highlight4']
    )