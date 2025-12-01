"""
Core functionality for GeoServer load testing
"""

import json
import subprocess
import tempfile
import requests
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import (
    TILE_MATRIX_SET,
    TILE_FORMAT,
    DEFAULT_ZOOM_LEVEL,
    DEFAULT_TILE_ROW,
    DEFAULT_TILE_COL,
    AB_ACCEPT_HEADER,
)
from .capabilities import discover_layers, LayerInfo, CapabilitiesParser
from .subdomain_manager import get_server_url_interactive
from ..common import (
    KARTOZA_COLORS,
    CONCURRENCY_LEVELS,
    DEFAULT_TOTAL_REQUESTS,
    RESULTS_DIR,
    REPORTS_DIR,
    TEMP_DIR,
    AB_USER_AGENT,
    REQUEST_TIMEOUT,
    BaseBenchmarker,
    BenchmarkResult,
    run_apache_bench,
    save_benchmark_result,
    format_timestamp,
    ReportGenerator
)

console = Console()


class GeoServerTester(BaseBenchmarker):
    """Main class for GeoServer load testing operations"""

    def __init__(self, server_url: Optional[str] = None):
        """Initialize the tester with server configuration"""
        super().__init__("geoserver", server_url)
        self.layers: Dict[str, LayerInfo] = {}
        self.service_info: Dict[str, str] = {}
        self.wmts_base = ""
        self.wms_base = ""

        if self.server_url:
            self._setup_urls()

    def _setup_urls(self):
        """Setup WMTS and WMS URLs from server URL"""
        if self.server_url:
            base_url = self.server_url.rstrip("/")
            self.wmts_base = f"{base_url}/gwc/service/wmts"
            self.wms_base = f"{base_url}/wms"

    def set_server_url(self, server_url: str):
        """Set the server URL and update endpoints"""
        self.server_url = server_url
        self._setup_urls()

        # Clear existing layer data when changing servers
        self.layers = {}
        self.service_info = {}

    def discover_layers(self) -> bool:
        """Discover layers from the GeoServer via GetCapabilities"""
        if not self.server_url:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server URL configured[/]")
            return False

        try:
            layer_list, self.service_info = discover_layers(self.server_url)

            # Convert list to dictionary for easier access
            self.layers = {}
            for layer_info in layer_list:
                # Use layer name as key
                self.layers[layer_info.name] = layer_info

            if not self.layers:
                console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  No layers discovered[/]")
                return False

            console.print(
                f"[{KARTOZA_COLORS['highlight4']}]✅ Discovered {len(self.layers)} layers[/]"
            )
            return True

        except Exception as e:
            console.print(
                f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers: {e}[/]"
            )
            return False

    def get_layer_list(self) -> List[str]:
        """Get list of available layer names"""
        return list(self.layers.keys())

    def get_layer_info(self, layer_name: str) -> Optional[LayerInfo]:
        """Get layer information by name"""
        return self.layers.get(layer_name)

    def generate_tile_url(
        self,
        layer_name: str,
        zoom: int = DEFAULT_ZOOM_LEVEL,
        row: int = DEFAULT_TILE_ROW,
        col: int = DEFAULT_TILE_COL,
    ) -> str:
        """Generate WMTS tile URL for a layer"""
        if not self.wmts_base:
            raise ValueError("Server URL not configured. Call set_server_url() first.")

        return (
            f"{self.wmts_base}?"
            f"SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&"
            f"LAYER={layer_name}&STYLE=&"
            f"TILEMATRIXSET={TILE_MATRIX_SET}&"
            f"TILEMATRIX={zoom}&TILEROW={row}&TILECOL={col}&"
            f"FORMAT={TILE_FORMAT}"
        )

    def generate_wms_url(
        self, layer_name: str, width: int = 600, height: int = 400, crs: str = "EPSG:4326"
    ) -> str:
        """Generate WMS URL for map preview"""
        if not self.wms_base:
            raise ValueError("Server URL not configured. Call set_server_url() first.")

        # Use layer's bbox if available from capabilities
        layer_info = self.get_layer_info(layer_name)
        if layer_info and layer_info.bbox:
            bbox = layer_info.bbox
            bbox_str = f"{bbox['minx']},{bbox['miny']},{bbox['maxx']},{bbox['maxy']}"
        else:
            # If no layer bbox available, request full world extent 
            # This will be transformed by the server to the layer's actual extent
            from .config import WORLD_BBOX_4326, WORLD_BBOX_3857
            if crs == "EPSG:4326" or crs == "CRS:84":
                bbox_str = ",".join(map(str, WORLD_BBOX_4326))
            else:
                # For other CRS, use Web Mercator world extent as default
                bbox_str = ",".join(map(str, WORLD_BBOX_3857))

        return (
            f"{self.wms_base}?"
            f"SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&"
            f"LAYERS={layer_name}&STYLES=&SRS={crs}&"
            f"BBOX={bbox_str}&WIDTH={width}&HEIGHT={height}&"
            f"FORMAT={TILE_FORMAT}"
        )

    def test_connectivity(self, layer_name: str) -> Tuple[bool, int]:
        """Test if a layer is accessible"""
        try:
            tile_url = self.generate_tile_url(layer_name)
            response = requests.get(tile_url, timeout=REQUEST_TIMEOUT)
            return response.status_code == 200, response.status_code
        except (requests.RequestException, ValueError):
            return False, 0

    def test_all_connectivity(self) -> Dict[str, Tuple[bool, int]]:
        """Test connectivity for all discovered layers"""
        if not self.layers:
            console.print(
                f"[{KARTOZA_COLORS['alert']}]❌ No layers discovered. Run discover_layers() first.[/]"
            )
            return {}

        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                "Testing layer connectivity...", total=len(self.layers)
            )

            for layer_name, layer_info in self.layers.items():
                progress.update(task, description=f"Testing {layer_info.title}")
                results[layer_name] = self.test_connectivity(layer_name)
                progress.advance(task)

        return results

    def download_map_preview(self, layer_name: str) -> Optional[Path]:
        """Download a WMS map preview using the same working logic as report generation"""
        import requests
        
        # Use previews directory instead of temp directory
        previews_dir = Path(__file__).parent.parent.parent / "previews"
        previews_dir.mkdir(exist_ok=True)
        preview_path = previews_dir / f"{layer_name.replace(':', '_')}_preview.png"
        
        # Use the same working bbox that works in report generation
        # Netherlands bounding box - this produces good previews
        bbox = "3.0501,50.7286,7.3450,53.7185"
        
        # Try both with and without workspace prefix (same as report generation)
        layer_variations = [f"CAS:{layer_name}", layer_name]
        
        for layer_variant in layer_variations:
            # Use the exact same WMS parameters that work in report generation
            wms_params = {
                'SERVICE': 'WMS',
                'VERSION': '1.1.1',
                'REQUEST': 'GetMap',
                'LAYERS': layer_variant,
                'STYLES': '',
                'BBOX': bbox,
                'WIDTH': '800',
                'HEIGHT': '600',
                'FORMAT': 'image/png',
                'SRS': 'EPSG:4326'
            }
            
            try:
                console.print(f"[dim]Capturing map image for {layer_variant}...[/dim]")
                response = requests.get(self.wms_base, params=wms_params, timeout=60)
                
                if response.status_code == 200:
                    # Check if response is actually an image (same logic as report generation)
                    if response.content.startswith(b'<?xml') or b'ServiceException' in response.content:
                        console.print(f"[dim]WMS error for {layer_variant}[/dim]")
                        continue
                    
                    # Check for reasonable image size
                    if len(response.content) < 1000:
                        console.print(f"[dim]Small/blank image for {layer_variant} ({len(response.content)} bytes)[/dim]")
                        continue
                    
                    # Save the image
                    with open(preview_path, 'wb') as f:
                        f.write(response.content)
                    
                    console.print(f"[dim]✓ Map image saved: {preview_path}[/dim]")
                    
                    # Try to display image inline for compatible terminals (kitty, etc)
                    import os
                    if os.environ.get('TERM', '').startswith('xterm-kitty') or 'KITTY_WINDOW_ID' in os.environ:
                        # Use kitty's icat for inline display - no additional popup needed
                        try:
                            subprocess.run(['kitten', 'icat', str(preview_path)], check=False)
                        except Exception:
                            console.print(f"[dim]View manually: {preview_path}[/dim]")
                    else:
                        # For non-kitty terminals, prompt user to open external viewer
                        from rich.prompt import Confirm
                        if Confirm.ask(f"[{KARTOZA_COLORS['highlight2']}]Open preview image?[/]"):
                            try:
                                subprocess.run(['fim', str(preview_path)], check=False)
                            except Exception:
                                try:
                                    subprocess.run(['xdg-open', str(preview_path)], check=False)
                                except Exception:
                                    console.print(f"[dim]View manually: {preview_path}[/dim]")
                    
                    return preview_path
                        
            except Exception as e:
                console.print(f"[dim]Failed to capture {layer_variant}: {e}[/dim]")
                continue
        
        console.print(f"[{KARTOZA_COLORS['danger_red']}]Could not capture map for {layer_name}[/]")
        return None

    def run_single_test(
        self,
        layer_key: str,
        concurrency: int,
        total_requests: int = DEFAULT_TOTAL_REQUESTS,
        timestamp: Optional[str] = None,
    ) -> Optional[BenchmarkResult]:
        """Run a single load test for a layer"""

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        test_id = f"{layer_key}_c{concurrency}_{timestamp}"
        output_prefix = self.results_dir / test_id
        tile_url = self.generate_tile_url(layer_key)

        layer_info = self.layers[layer_key]

        # Run the test  
        headers = {"Accept": AB_ACCEPT_HEADER}
        success, ab_results = run_apache_bench(
            tile_url, total_requests, concurrency, str(output_prefix), headers
        )

        if not success:
            console.print(
                f"[{KARTOZA_COLORS['alert']}]❌ Test failed: {ab_results.get('error', 'Unknown error')}[/]"
            )
            return None

        # Calculate success rate
        failed_requests = ab_results.get("failed_requests", 0)
        success_requests = total_requests - failed_requests
        success_rate = (success_requests / total_requests) * 100

        # Create test result object
        result = BenchmarkResult(
            target=layer_key,
            service_type="geoserver",
            concurrency=concurrency,
            total_requests=total_requests,
            requests_per_second=ab_results.get("requests_per_second", 0.0),
            mean_response_time=ab_results.get("mean_response_time", 0.0),
            failed_requests=failed_requests,
            total_time=ab_results.get("total_time", 0.0),
            transfer_rate=ab_results.get("transfer_rate", 0.0),
            success_rate=success_rate,
            test_id=test_id,
            timestamp=timestamp,
        )

        # Save detailed test metadata to JSON
        self._save_test_metadata(result, tile_url, layer_info)

        return result

    def _save_test_metadata(
        self, result: BenchmarkResult, tile_url: str, layer_info
    ):
        """Save detailed test metadata to JSON file"""

        metadata = {
            "layer": result.target,
            "description": layer_info.title,
            "timestamp": result.timestamp,
            "test_id": result.test_id,
            "total_requests": result.total_requests,
            "concurrency_level": result.concurrency,
            "tile_url": tile_url,
            "test_date": datetime.now().isoformat(),
            "server": "climate-adaptation-services.geospatialhosting.com",
            "protocol": "WMTS",
            "tile_matrix": str(DEFAULT_ZOOM_LEVEL),
            "tile_row": str(DEFAULT_TILE_ROW),
            "tile_col": str(DEFAULT_TILE_COL),
            "format": TILE_FORMAT,
            "results": {
                "requests_per_second": f"{result.requests_per_second:.2f}",
                "mean_response_time_ms": f"{result.mean_response_time:.2f}",
                "failed_requests": str(result.failed_requests),
                "total_time_seconds": f"{result.total_time:.2f}",
                "transfer_rate_kbps": f"{result.transfer_rate:.2f}",
                "success_rate": f"{result.success_rate:.1f}",
            },
        }

        json_file = self.results_dir / f"{result.test_id}.json"
        with open(json_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def run_comprehensive_test(
        self,
        total_requests: int = DEFAULT_TOTAL_REQUESTS,
        concurrency_levels: Optional[List[int]] = None,
    ) -> List[BenchmarkResult]:
        """Run comprehensive tests across all layers and concurrency levels"""

        if concurrency_levels is None:
            concurrency_levels = CONCURRENCY_LEVELS

        # Trim concurrency levels that exceed request count (Apache Bench requirement)
        original_count = len(concurrency_levels)
        concurrency_levels = [c for c in concurrency_levels if c <= total_requests]
        
        if len(concurrency_levels) < original_count:
            removed_count = original_count - len(concurrency_levels)
            console.print(f"[{KARTOZA_COLORS['highlight3']}]📝 Trimmed {removed_count} concurrency levels that exceed request count ({total_requests})[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Concurrency cannot exceed total requests (Apache Bench limitation)[/]")
            
        # Ensure we have at least one valid concurrency level
        if not concurrency_levels:
            concurrency_levels = [min(100, total_requests)]
            console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Using concurrency level: {concurrency_levels[0]}[/]")

        # Clear previous results
        self.clear_results()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_results = []
        total_tests = len(self.layers) * len(concurrency_levels)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:

            main_task = progress.add_task(
                "Running comprehensive load tests...", total=total_tests
            )

            for layer_key in self.layers:
                layer_info = self.layers[layer_key]

                # Test connectivity first
                is_accessible, status_code = self.test_connectivity(layer_key)
                if not is_accessible:
                    console.print(
                        f"[{KARTOZA_COLORS['alert']}]❌ Skipping {layer_info.title} - "
                        f"not accessible (HTTP {status_code})[/]"
                    )
                    # Skip all concurrency levels for this layer
                    for _ in concurrency_levels:
                        progress.advance(main_task)
                    continue

                console.print(
                    f"[{KARTOZA_COLORS['highlight2']}]🗺️  Testing: {layer_info.title}[/]"
                )

                for concurrency in concurrency_levels:
                    progress.update(
                        main_task, description=f"Testing {layer_key} (C={concurrency})"
                    )

                    result = self.run_single_test(
                        layer_key, concurrency, total_requests, timestamp
                    )

                    if result:
                        all_results.append(result)
                        console.print(
                            f"[{KARTOZA_COLORS['highlight4']}]  ✅ C={concurrency}: "
                            f"{result.requests_per_second:.1f} RPS, "
                            f"{result.mean_response_time:.1f}ms avg[/]"
                        )
                    else:
                        console.print(
                            f"[{KARTOZA_COLORS['alert']}]  ❌ C={concurrency}: Failed[/]"
                        )

                    progress.advance(main_task)

        # Save consolidated results
        if all_results:
            report_generator = ReportGenerator("geoserver")
            test_config = {
                "total_requests": total_requests,
                "concurrency_levels": concurrency_levels,
                "layers_tested": list(self.layers.keys()),
                "server": self.server_url or "unknown"
            }
            report_generator.consolidate_results(all_results, timestamp, test_config)

        return all_results

    def get_results_summary(self) -> Table:
        """Get a summary table of recent test results using common report utilities"""
        report_generator = ReportGenerator("geoserver")
        return report_generator.get_results_summary_from_files()

