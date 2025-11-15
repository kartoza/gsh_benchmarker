"""
Shared utility functions for GSH Benchmarker Suite
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn
from rich.table import Table

from .colors import KARTOZA_COLORS
from .config import (
    RESULTS_DIR, REPORTS_DIR, TEMP_DIR, AB_USER_AGENT, AB_ACCEPT_HEADER, 
    REQUEST_TIMEOUT, DEFAULT_TOTAL_REQUESTS
)

console = Console()


@dataclass
class BenchmarkResult:
    """Generic container for benchmark results across all service types"""
    
    target: str  # Layer, table, endpoint, etc.
    service_type: str  # geoserver, g3w, postgres, geonode
    concurrency: int
    total_requests: int
    requests_per_second: float
    mean_response_time: float
    failed_requests: int
    total_time: float
    transfer_rate: float
    success_rate: float
    test_id: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class BaseBenchmarker:
    """Base class for all benchmarker implementations"""
    
    def __init__(self, service_type: str, server_url: Optional[str] = None):
        """Initialize the benchmarker with service type and server configuration"""
        self.service_type = service_type
        self.server_url = server_url
        self.results_dir = RESULTS_DIR
        self.reports_dir = REPORTS_DIR
        self.temp_dir = TEMP_DIR
        
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories"""
        for directory in [self.results_dir, self.reports_dir, self.temp_dir]:
            directory.mkdir(exist_ok=True)
    
    def clear_results(self):
        """Clear the results directory before new tests"""
        if self.results_dir.exists():
            console.print(
                f"[{KARTOZA_COLORS['highlight3']}]🗑️  Clearing previous results...[/]"
            )
            shutil.rmtree(self.results_dir)
            self.results_dir.mkdir(exist_ok=True)
            console.print(
                f"[{KARTOZA_COLORS['highlight4']}]✅ Results directory cleared[/]"
            )


def run_apache_bench(
    url: str, 
    total_requests: int, 
    concurrency: int, 
    output_prefix: str,
    headers: Optional[Dict[str, str]] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Run Apache Bench test and parse results
    
    This is a shared function that can be used by any benchmarker that needs HTTP load testing.
    """
    
    log_file = f"{output_prefix}.log"
    csv_file = f"{output_prefix}.csv"
    
    # Construct ab command
    cmd = [
        "ab",
        f"-n", str(total_requests),
        f"-c", str(concurrency),
        f"-g", csv_file,
        f"-H", f"User-Agent: {AB_USER_AGENT}",
        f"-H", f"Accept: {AB_ACCEPT_HEADER}",
    ]
    
    # Add custom headers if provided
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    
    cmd.append(url)
    
    try:
        # Run Apache Bench
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Save log output
        with open(log_file, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write(f"\n--- STDERR ---\n{result.stderr}")
        
        if result.returncode != 0:
            return False, {
                "error": f"Apache Bench failed with code {result.returncode}"
            }
        
        # Parse results from stdout
        return True, parse_ab_output(result.stdout)
        
    except subprocess.TimeoutExpired:
        return False, {"error": "Apache Bench test timed out"}
    except Exception as e:
        return False, {"error": f"Failed to run Apache Bench: {e}"}


def parse_ab_output(output: str) -> Dict[str, Any]:
    """Parse Apache Bench output to extract metrics"""
    results = {}
    
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        
        if "Requests per second:" in line:
            results["requests_per_second"] = float(line.split()[3])
        elif "Time per request:" in line and "(mean)" in line:
            results["mean_response_time"] = float(line.split()[3])
        elif "Failed requests:" in line:
            results["failed_requests"] = int(line.split()[2])
        elif "Time taken for tests:" in line:
            results["total_time"] = float(line.split()[4])
        elif "Transfer rate:" in line:
            results["transfer_rate"] = float(line.split()[2])
    
    return results


def save_benchmark_result(
    result: BenchmarkResult, 
    url: str,
    results_dir: Path,
    additional_metadata: Optional[Dict[str, Any]] = None
):
    """Save benchmark result metadata to JSON file"""
    
    metadata = {
        "target": result.target,
        "service_type": result.service_type,
        "timestamp": result.timestamp,
        "test_id": result.test_id,
        "total_requests": result.total_requests,
        "concurrency_level": result.concurrency,
        "test_url": url,
        "test_date": datetime.now().isoformat(),
        "results": {
            "requests_per_second": f"{result.requests_per_second:.2f}",
            "mean_response_time_ms": f"{result.mean_response_time:.2f}",
            "failed_requests": str(result.failed_requests),
            "total_time_seconds": f"{result.total_time:.2f}",
            "transfer_rate_kbps": f"{result.transfer_rate:.2f}",
            "success_rate": f"{result.success_rate:.1f}",
        },
    }
    
    # Add service-specific metadata
    if result.metadata:
        metadata.update(result.metadata)
    
    if additional_metadata:
        metadata.update(additional_metadata)
    
    json_file = results_dir / f"{result.test_id}.json"
    with open(json_file, "w") as f:
        json.dump(metadata, f, indent=2)


def create_results_summary_table(results: List[BenchmarkResult], service_type: str) -> Table:
    """Create a summary table of benchmark results"""
    
    if not results:
        return None
    
    table = Table(title=f"{service_type.title()} Benchmark Results", show_header=True)
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


def format_timestamp() -> str:
    """Generate a standardized timestamp for test IDs"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def validate_concurrency_level(concurrency: int, max_concurrency: int = 10000) -> bool:
    """Validate concurrency level is within reasonable bounds"""
    return 1 <= concurrency <= max_concurrency