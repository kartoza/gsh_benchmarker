"""
Rich-based user interface for GeoServer load testing
"""

import sys
import subprocess
import glob
from pathlib import Path
from typing import Optional, List, Dict

from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn

try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False
    questionary = None

from .core import GeoServerTester
from .config import (
    KARTOZA_COLORS, CONCURRENCY_LEVELS, 
    DEFAULT_TOTAL_REQUESTS, DEFAULT_CONCURRENCY
)
from ..common.config import RESULTS_DIR
from .subdomain_manager import get_server_url_interactive
from .image_renderer import TerminalImageRenderer
from ..common import (
    ReportGenerator,
    execute_external_report_generator,
    find_latest_report_file,
    create_benchmark_summary_panel,
    TerminalImageRenderer as CommonImageRenderer
)
from ..common.monitoring_config import MonitoringConfigManager, MonitoringEndpoint
from ..common.test_config import TestConfigManager, parse_concurrency_list, validate_concurrency_list, format_concurrency_list

console = Console()

class MenuInterface:
    """Rich-based menu interface for the GeoServer testing suite"""
    
    def __init__(self):
        """Initialize the menu interface"""
        self.tester = GeoServerTester()
        self.server_configured = False
        self.image_renderer = TerminalImageRenderer()
        self.monitoring_config = MonitoringConfigManager()
        self.test_config = TestConfigManager()
        self.use_interactive_menus = QUESTIONARY_AVAILABLE
    
    def show_banner(self):
        """Display the main banner with Kartoza logo"""
        # Display Kartoza logo using chafa if available
        self._show_logo()
        
        banner_text = Text()
        banner_text.append("🌍 GeoServer Load Testing Suite", style=f"bold {KARTOZA_COLORS['highlight2']}")
        banner_text.append("\n\n")
        banner_text.append("Climate Adaptation Services", style=f"{KARTOZA_COLORS['highlight3']}")
        banner_text.append("\n")
        banner_text.append("WMTS Tile Performance Analysis", style=f"{KARTOZA_COLORS['highlight3']}")
        
        panel = Panel.fit(
            Align.center(banner_text),
            border_style=f"{KARTOZA_COLORS['highlight4']}",
            padding=(1, 2)
        )
        
        console.print(panel)
        console.print()
    
    def _show_logo(self):
        """Display Kartoza logo with improved terminal compatibility"""
        try:
            logo_path = Path(__file__).parent.parent / "resources" / "KartozaLogoVerticalCMYK-small.png"
            if not logo_path.exists():
                self._show_text_logo()
                return
            
            # Check if chafa is available first
            import os
            try:
                # Quick check if chafa is installed
                subprocess.run(["chafa", "--version"], capture_output=True, timeout=2, check=True)
                chafa_available = True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                chafa_available = False
            
            if chafa_available:
                try:
                    # Try the most basic chafa format first
                    result = subprocess.run([
                        "chafa", 
                        str(logo_path),
                        "--size", "40x10",  # Smaller size for better compatibility
                        "--format", "symbols",
                        "--colors", "16",
                        "--fill", "block",
                        "--optimize", "0"  # Disable optimizations that might cause issues
                    ], 
                    capture_output=True, text=True, timeout=5, check=False)
                    
                    if result.returncode == 0 and result.stdout:
                        # More aggressive filtering of ANSI sequences
                        output = result.stdout.strip()
                        
                        # Count various control characters that might be problematic
                        escape_count = output.count('\033')
                        control_chars = sum(1 for c in output if ord(c) < 32 and c not in '\n\r\t')
                        
                        # If output looks clean enough, use it
                        if (len(output) < 2000 and 
                            escape_count < 50 and 
                            control_chars < 20 and
                            '\033[' in output):  # Has some ANSI but not excessive
                            
                            logo_lines = output.split('\n')
                            for line in logo_lines:
                                if line.strip():  # Skip empty lines
                                    console.print(Align.center(line))
                            console.print()
                            return
                        
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                    pass
            
            # Fallback: Try the existing image renderer (for kitty/iterm)
            try:
                success = self.image_renderer.render_image(logo_path, max_width=40, max_height=10)
                if success:
                    console.print()
                    return
            except:
                pass
                
            # Final fallback: Clean text logo
            self._show_text_logo()
            
        except Exception:
            # Silent fallback to text logo
            self._show_text_logo()
    
    def _interactive_select(self, choices: List[str], message: str = "Select an option", 
                           show_skip_option: bool = False) -> Optional[int]:
        """Interactive arrow-key selection menu with optional fallback"""
        if not self.use_interactive_menus:
            # Fallback to numbered selection
            for i, choice in enumerate(choices):
                console.print(f"  [{KARTOZA_COLORS['highlight3']}]{i+1}[/] - {choice}")
            console.print()
            
            if show_skip_option:
                choices_with_skip = choices + ["🔙 Back"]
                max_choice = len(choices_with_skip)
            else:
                max_choice = len(choices)
                
            try:
                selection = IntPrompt.ask(
                    message,
                    choices=[str(i+1) for i in range(max_choice)],
                    show_choices=False
                )
                return selection - 1
            except (KeyboardInterrupt, EOFError):
                return None
        
        try:
            # Use questionary for interactive selection
            questionary_choices = choices.copy()
            if show_skip_option:
                questionary_choices.append("🔙 Back")
            
            # Custom style to match Kartoza theme
            custom_style = questionary.Style([
                ('question', '#ff8c00'),  # Orange for question
                ('answer', '#87ceeb'),    # Light blue for answer
                ('pointer', '#ff8c00 bold'),  # Orange pointer
                ('highlighted', '#87ceeb bold'),  # Highlighted option
                ('selected', '#32cd32 bold'),     # Green for selected
            ])
            
            result = questionary.select(
                message,
                choices=questionary_choices,
                style=custom_style,
                use_shortcuts=True
            ).ask()
            
            if result is None or result == "🔙 Back":
                return None
                
            # Find the index of the selected choice
            return choices.index(result) if result in choices else None
            
        except (KeyboardInterrupt, EOFError):
            return None
        except Exception:
            # Fallback to numbered selection on any error
            return self._interactive_select_fallback(choices, message, show_skip_option)
    
    def _interactive_select_fallback(self, choices: List[str], message: str, show_skip_option: bool) -> Optional[int]:
        """Fallback numbered selection when questionary fails"""
        for i, choice in enumerate(choices):
            console.print(f"  [{KARTOZA_COLORS['highlight3']}]{i+1}[/] - {choice}")
        console.print()
        
        if show_skip_option:
            console.print(f"  [{KARTOZA_COLORS['highlight3']}]{len(choices)+1}[/] - 🔙 Back")
            max_choice = len(choices) + 1
        else:
            max_choice = len(choices)
            
        try:
            selection = IntPrompt.ask(
                message,
                choices=[str(i+1) for i in range(max_choice)],
                show_choices=False
            )
            
            if show_skip_option and selection == max_choice:
                return None  # User selected "Back"
            return selection - 1
        except (KeyboardInterrupt, EOFError):
            return None
    
    def _show_text_logo(self):
        """Display a clean text-based Kartoza logo"""
        console.print()
        console.print(Align.center(f"[{KARTOZA_COLORS['highlight2']}]╔══════════════════════════════════╗[/]"))
        console.print(Align.center(f"[{KARTOZA_COLORS['highlight2']}]║[/] [{KARTOZA_COLORS['highlight1']}]            KARTOZA            [/] [{KARTOZA_COLORS['highlight2']}]║[/]"))
        console.print(Align.center(f"[{KARTOZA_COLORS['highlight2']}]║[/] [{KARTOZA_COLORS['highlight3']}] OPEN SOURCE GEOSPATIAL SOLUTIONS [/] [{KARTOZA_COLORS['highlight2']}]║[/]"))
        console.print(Align.center(f"[{KARTOZA_COLORS['highlight2']}]╚══════════════════════════════════╝[/]"))
        console.print()
    
    def setup_server(self):
        """Setup server connection and discover layers"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🔧 Server Setup[/]")
        console.print()
        
        # Get server URL
        server_url = get_server_url_interactive()
        if not server_url:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server URL provided[/]")
            return False
        
        # Set server URL and discover layers
        self.tester.set_server_url(server_url)
        
        if self.tester.discover_layers():
            self.server_configured = True
            console.print()
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Server configured: {server_url}[/]")
            
            # Show service info if available
            if self.tester.service_info:
                service_info = self.tester.service_info
                console.print(f"[{KARTOZA_COLORS['highlight3']}]Service: {service_info.get('title', 'Unknown')}[/]")
                if service_info.get('abstract'):
                    console.print(f"[{KARTOZA_COLORS['highlight3']}]Description: {service_info['abstract']}[/]")
            
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return True
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to discover layers[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return False
    
    def show_layer_info(self):
        """Display information about discovered layers"""
        if not self.server_configured or not self.tester.layers:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server configured or layers discovered[/]")
            console.print("Please run server setup first.")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        table = Table(title="Discovered Layers", show_header=True)
        table.add_column("Layer Name", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Title", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Abstract", style=f"{KARTOZA_COLORS['highlight3']}")
        table.add_column("SRS", justify="center", style=f"{KARTOZA_COLORS['highlight4']}")
        
        for layer_name, layer_info in self.tester.layers.items():
            # Truncate abstract if too long
            abstract = layer_info.abstract[:80] + "..." if len(layer_info.abstract) > 80 else layer_info.abstract
            
            # Show primary SRS
            primary_srs = layer_info.srs_list[0] if layer_info.srs_list else "Unknown"
            
            table.add_row(
                layer_name,
                layer_info.title,
                abstract,
                primary_srs
            )
        
        console.print(table)
        console.print()
        
        # Show additional info
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Total layers: {len(self.tester.layers)}[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Server: {self.tester.server_url}[/]")
        console.print()
        
        Prompt.ask("Press Enter to continue", default="")
    
    def test_connectivity_menu(self):
        """Test connectivity to all layers"""
        if not self.server_configured:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server configured. Please run server setup first.[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🔍 Testing connectivity to all layers...[/]")
        console.print()
        
        results = self.tester.test_all_connectivity()
        
        table = Table(title="Connectivity Test Results", show_header=True)
        table.add_column("Layer Name", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Title", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Status", justify="center")
        table.add_column("HTTP Code", justify="center")
        
        all_accessible = True
        for layer_name, (is_accessible, status_code) in results.items():
            layer_info = self.tester.get_layer_info(layer_name)
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
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ All layers are accessible![/]")
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Some layers are not accessible[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def preview_layer_menu(self):
        """Show layer preview menu"""
        if not self.server_configured:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server configured. Please run server setup first.[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
            
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🖼️  Layer Preview[/]")
        console.print()
        
        # Create layer choices from discovered layers
        layer_names = list(self.tester.layers.keys())
        if not layer_names:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No layers available[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create layer choices for interactive selection
        layer_choices = []
        for layer_name in layer_names:
            layer_info = self.tester.layers[layer_name]
            layer_choices.append(f"{layer_info.title} ({layer_name})")
        
        choice_index = self._interactive_select(
            layer_choices,
            "Select a layer to preview:",
            show_skip_option=True
        )
        
        if choice_index is not None:
            layer_name = layer_names[choice_index]
            self._show_layer_preview(layer_name)
    
    def _show_layer_preview(self, layer_name: str):
        """Show preview for a specific layer"""
        layer_info = self.tester.get_layer_info(layer_name)
        if not layer_info:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Layer not found: {layer_name}[/]")
            return
        
        console.print(f"[{KARTOZA_COLORS['highlight1']}]📍 Previewing: {layer_info.title}[/]")
        if layer_info.abstract:
            console.print(f"[{KARTOZA_COLORS['highlight3']}]{layer_info.abstract}[/]")
        console.print()
        
        with console.status(f"[{KARTOZA_COLORS['highlight2']}]Downloading map preview..."):
            preview_path = self.tester.download_map_preview(layer_name)
        
        if preview_path and preview_path.exists():
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Preview downloaded: {preview_path}[/]")
            console.print()
            
            # Use the enhanced image renderer
            success = self.image_renderer.render_image(preview_path, max_width=100, max_height=30)
            
            if not success:
                # Show capabilities info if rendering failed
                console.print()
                console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Image rendering capabilities:[/]")
                caps = self.image_renderer.get_capabilities_info()
                console.print(f"   Terminal: {caps['terminal_type']}")
                console.print(f"   Available renderers: {', '.join(caps['available_renderers']) if caps['available_renderers'] else 'None'}")
                
                if not caps['available_renderers']:
                    console.print()
                    console.print(f"[{KARTOZA_COLORS['highlight3']}]To view images in terminal, install:[/]")
                    console.print("   • chafa: [dim]sudo apt install chafa[/dim] or [dim]brew install chafa[/dim]")
                    console.print("   • Or use Kitty terminal for native image support")
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to download preview[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    
    def single_test_menu(self):
        """Menu for running a single layer test with multiple concurrency levels"""
        if not self.server_configured:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server configured. Please run server setup first.[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
            
        console.print(f"[{KARTOZA_COLORS['highlight2']}]⚡ Single Layer Load Test[/]")
        console.print()
        
        # Layer selection from discovered layers
        layer_names = list(self.tester.layers.keys())
        if not layer_names:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No layers available[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create layer choices for interactive selection
        layer_choices = []
        for layer_name in layer_names:
            layer_info = self.tester.layers[layer_name]
            layer_choices.append(f"{layer_info.title} ({layer_name})")
        
        choice_index = self._interactive_select(
            layer_choices,
            "Select a layer to test:",
            show_skip_option=True
        )
        
        if choice_index is None:
            return  # User cancelled
        
        layer_name = layer_names[choice_index]
        layer_info = self.tester.layers[layer_name]
        
        console.print(f"[{KARTOZA_COLORS['highlight1']}]Selected: {layer_info.title}[/]")
        console.print()
        
        # Test parameters - get last used values as defaults
        last_requests = self.test_config.get_last_total_requests()
        last_concurrency = self.test_config.get_last_concurrency_list()
        
        total_requests = IntPrompt.ask(
            "Number of requests",
            default=last_requests
        )
        
        # Get concurrency levels as comma-separated list
        default_concurrency_str = format_concurrency_list(last_concurrency)
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Enter concurrency levels as comma-separated values (e.g., 1,10,100,500)[/]")
        
        concurrency_input = Prompt.ask(
            "Concurrency levels",
            default=default_concurrency_str
        )
        
        # Parse and validate concurrency levels
        concurrency_list = parse_concurrency_list(concurrency_input)
        if not concurrency_list:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Invalid concurrency levels[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Remove concurrency levels greater than total requests
        valid_concurrency = validate_concurrency_list(concurrency_list, total_requests)
        removed_concurrency = [c for c in concurrency_list if c not in valid_concurrency]
        
        if removed_concurrency:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Removed concurrency levels greater than request count: {removed_concurrency}[/]")
        
        if not valid_concurrency:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No valid concurrency levels remaining[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Save configuration for next time
        self.test_config.update_test_config(concurrency_list, total_requests)
        
        console.print()
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Test Configuration:[/]")
        console.print(f"  Layer: {layer_info.title}")
        console.print(f"  Requests per test: {total_requests:,}")
        console.print(f"  Concurrency levels: {format_concurrency_list(valid_concurrency)}")
        console.print(f"  Total tests: {len(valid_concurrency)}")
        console.print(f"  Total requests: {total_requests * len(valid_concurrency):,}")
        console.print()
        
        if not Confirm.ask(f"[{KARTOZA_COLORS['highlight4']}]Start load test suite?[/]"):
            return
        
        # Run the tests for all concurrency levels
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🚀 Starting load test suite...[/]")
        console.print()
        
        results = []
        for i, concurrency in enumerate(valid_concurrency, 1):
            console.print(f"[{KARTOZA_COLORS['highlight1']}]Running test {i}/{len(valid_concurrency)}: {concurrency} concurrent connections[/]")
            
            with console.status(f"[{KARTOZA_COLORS['highlight1']}]Testing concurrency level {concurrency}..."):
                result = self.tester.run_single_test(layer_name, concurrency, total_requests)
            
            if result:
                results.append(result)
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Completed: {result.requests_per_second:.2f} RPS, {result.success_rate:.1f}% success[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Test failed for concurrency {concurrency}[/]")
            
            console.print()
        
        # Display comprehensive results
        if results:
            self._display_multiple_test_results(results, layer_info.title)
            
            # Save session-specific consolidated results for PDF generation
            session_results_file = None
            if len(results) > 1 and Confirm.ask(f"[{KARTOZA_COLORS['highlight4']}]Generate PDF report?[/]"):
                # Save current session results to a session-specific file
                from datetime import datetime
                from ..common import ReportGenerator
                
                session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_generator = ReportGenerator("geoserver")
                test_config = {
                    "total_requests": total_requests,
                    "concurrency_levels": valid_concurrency,
                    "layers_tested": [layer_name],  # Only the selected layer
                    "server": self.tester.server_url or "unknown",
                    "session_type": "single_layer"
                }
                session_results_file = report_generator.consolidate_results(results, session_timestamp, test_config)
                
                # Generate PDF from session-specific results
                self._generate_pdf_report(session_results_file)
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ All tests failed[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _display_test_result(self, result):
        """Display test result in a nice format"""
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Test completed successfully![/]")
        console.print()
        
        table = Table(title="Test Results", show_header=True)
        table.add_column("Metric", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Value", style=f"{KARTOZA_COLORS['highlight1']}")
        
        table.add_row("Requests per Second", f"{result.requests_per_second:.2f}")
        table.add_row("Mean Response Time", f"{result.mean_response_time:.2f} ms")
        table.add_row("Failed Requests", f"{result.failed_requests}/{result.total_requests}")
        table.add_row("Success Rate", f"{result.success_rate:.1f}%")
        table.add_row("Total Time", f"{result.total_time:.2f} seconds")
        table.add_row("Transfer Rate", f"{result.transfer_rate:.2f} KB/s")
        
        console.print(table)
    
    def _display_multiple_test_results(self, results, layer_title: str):
        """Display results from multiple concurrency tests in a comprehensive format"""
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Test suite completed successfully![/]")
        console.print()
        
        # Create comprehensive results table
        table = Table(title=f"Load Test Results: {layer_title}", show_header=True)
        table.add_column("Concurrency", justify="center", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("RPS", justify="right", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Mean Response (ms)", justify="right", style=f"{KARTOZA_COLORS['highlight3']}")
        table.add_column("Success Rate", justify="right", style=f"{KARTOZA_COLORS['highlight4']}")
        table.add_column("Failed Requests", justify="right")
        table.add_column("Total Time (s)", justify="right")
        
        for result in results:
            # Color code success rate
            success_color = KARTOZA_COLORS['highlight4'] if result.success_rate >= 95 else KARTOZA_COLORS['alert']
            
            table.add_row(
                str(result.concurrency),
                f"{result.requests_per_second:.2f}",
                f"{result.mean_response_time:.2f}",
                f"[{success_color}]{result.success_rate:.1f}%[/]",
                f"{result.failed_requests}/{result.total_requests}",
                f"{result.total_time:.2f}"
            )
        
        console.print(table)
        console.print()
        
        # Display performance summary
        if len(results) > 1:
            best_rps = max(results, key=lambda r: r.requests_per_second)
            best_response = min(results, key=lambda r: r.mean_response_time)
            
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Performance Summary:[/]")
            console.print(f"  🚀 Best RPS: {best_rps.requests_per_second:.2f} at {best_rps.concurrency} concurrency")
            console.print(f"  ⚡ Best Response Time: {best_response.mean_response_time:.2f}ms at {best_response.concurrency} concurrency")
            console.print()
    
    def comprehensive_test_menu(self):
        """Menu for running comprehensive tests"""
        if not self.server_configured:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No server configured. Please run server setup first.[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
            
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🔥 Comprehensive Load Test Suite[/]")
        console.print()
        
        if not self.tester.layers:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No layers available[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Test parameters - get last used values as defaults
        last_requests = self.test_config.get_last_total_requests()
        last_concurrency = self.test_config.get_last_concurrency_list()
        
        total_requests = IntPrompt.ask(
            "Requests per test",
            default=last_requests
        )
        
        # Get concurrency levels as comma-separated list
        default_concurrency_str = format_concurrency_list(last_concurrency)
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Enter concurrency levels as comma-separated values (e.g., 1,10,100,500)[/]")
        
        concurrency_input = Prompt.ask(
            "Concurrency levels for all layers",
            default=default_concurrency_str
        )
        
        # Parse and validate concurrency levels
        concurrency_list = parse_concurrency_list(concurrency_input)
        if not concurrency_list:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Invalid concurrency levels[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Remove concurrency levels greater than total requests
        valid_concurrency = validate_concurrency_list(concurrency_list, total_requests)
        removed_concurrency = [c for c in concurrency_list if c not in valid_concurrency]
        
        if removed_concurrency:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Removed concurrency levels greater than request count: {removed_concurrency}[/]")
        
        if not valid_concurrency:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No valid concurrency levels remaining[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Save configuration for next time
        self.test_config.update_test_config(concurrency_list, total_requests)
        
        console.print()
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Test Configuration:[/]")
        console.print(f"  • Layers: {len(self.tester.layers)}")
        console.print(f"  • Concurrency levels: {format_concurrency_list(valid_concurrency)}")
        console.print(f"  • Requests per test: {total_requests:,}")
        console.print(f"  • Total tests: {len(self.tester.layers) * len(valid_concurrency)}")
        console.print(f"  • Total requests: {total_requests * len(self.tester.layers) * len(valid_concurrency):,}")
        console.print(f"  • Estimated time: {self._estimate_test_time(len(valid_concurrency))} minutes")
        console.print()
        
        if not Confirm.ask(f"[{KARTOZA_COLORS['alert']}]⚠️  This is a comprehensive test. Continue?[/]"):
            return
        
        # Run comprehensive tests
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🚀 Starting comprehensive load tests...[/]")
        console.print()
        
        results = self.tester.run_comprehensive_test(total_requests, valid_concurrency)
        
        if results:
            self._display_comprehensive_results(results)
            
            if Confirm.ask(f"[{KARTOZA_COLORS['highlight4']}]Generate PDF report?[/]"):
                # Find the session-specific results file that was created by run_comprehensive_test
                from datetime import datetime
                # The comprehensive test should have already saved consolidated results
                # We need to get the path to the most recent file for this session
                import glob
                from pathlib import Path
                
                # Look for the most recent consolidated file (should be the one just created)
                results_pattern = f"{RESULTS_DIR}/consolidated_geoserver_results_*.json"
                result_files = sorted(glob.glob(results_pattern), key=lambda x: Path(x).stat().st_mtime, reverse=True)
                
                if result_files:
                    # Use the most recently created file (should be our session)
                    session_results_file = result_files[0]
                    console.print(f"[{KARTOZA_COLORS['highlight3']}]Using session results: {Path(session_results_file).name}[/]")
                    self._generate_pdf_report(session_results_file)
                else:
                    # Fallback to default behavior
                    self._generate_pdf_report()
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No test results generated[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _estimate_test_time(self, concurrency_count: int = None) -> int:
        """Estimate test completion time in minutes"""
        if concurrency_count is None:
            concurrency_count = len(CONCURRENCY_LEVELS)
        
        # Rough estimation: 30 seconds per test + overhead
        total_tests = len(self.tester.layers) * concurrency_count
        return (total_tests * 30) // 60
    
    def _display_comprehensive_results(self, results):
        """Display comprehensive test results summary"""
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Comprehensive testing completed![/]")
        console.print()
        
        # Summary table
        table = Table(title="Comprehensive Test Summary", show_header=True)
        table.add_column("Layer", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Tests", justify="center")
        table.add_column("Best RPS", justify="right", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("Worst RPS", justify="right")
        table.add_column("Avg Success Rate", justify="right", style=f"{KARTOZA_COLORS['highlight4']}")
        
        # Group results by layer
        layer_stats = {}
        for result in results:
            layer_name = getattr(result, 'layer', getattr(result, 'target', 'unknown'))
            if layer_name not in layer_stats:
                layer_stats[layer_name] = []
            layer_stats[layer_name].append(result)
        
        for layer_name, layer_results in layer_stats.items():
            layer_info = self.tester.get_layer_info(layer_name)
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
                f"{avg_success:.1f}%"
            )
        
        console.print(table)
    
    def _generate_pdf_report(self, session_results_file=None):
        """Generate PDF report using common PDF generator"""
        try:
            # Import the PDF generator
            from ..common.pdf_generator import generate_pdf_report
            
            if session_results_file:
                console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Generating PDF report for current session...[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Generating comprehensive PDF report...[/]")
            
            # Generate PDF report
            pdf_path = generate_pdf_report("geoserver", results_file=session_results_file)
            
            if pdf_path:
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated![/]")
                console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Report: {pdf_path}[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to generate PDF report[/]")
                
                # Offer to generate text report as fallback
                if Confirm.ask(f"[{KARTOZA_COLORS['highlight3']}]Generate text report instead?[/]"):
                    self._generate_text_report()
                    
        except ImportError:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ PDF generation requires matplotlib[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Install with: pip install matplotlib[/]")
            
            # Offer to generate text report as fallback
            if Confirm.ask(f"[{KARTOZA_COLORS['highlight3']}]Generate text report instead?[/]"):
                self._generate_text_report()
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating report: {e}[/]")
    
    def _generate_text_report(self):
        """Generate a text report as fallback"""
        try:
            # Get recent results (simplified - in real implementation you'd load actual results)
            report_generator = ReportGenerator("geoserver")
            
            # For now, just show that we could generate a report
            console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Text report functionality available[/]")
            console.print(f"[{KARTOZA_COLORS['highlight4']}]Future enhancement: Generate comprehensive text reports[/]")
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating text report: {e}[/]")
    
    def generate_report_from_latest_menu(self):
        """Generate PDF report from latest benchmark results"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Generate Report from Latest Results[/]")
        console.print()
        
        try:
            from ..common.pdf_generator import generate_pdf_report
            
            # Create a clean progress bar with messages on separate lines
            with Progress(
                SpinnerColumn(),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=True
            ) as progress:
                
                # Add main task
                task = progress.add_task("Generating PDF Report", total=100)
                
                # Step 1: Find latest results
                console.print("🔍 Looking for latest benchmark results...")
                progress.update(task, completed=10)
                
                # Step 2: Initialize PDF generator (simulated steps for better UX)
                console.print("📋 Initializing PDF generator...")
                progress.update(task, completed=20)
                
                # Step 3: Generate the actual PDF
                console.print("📄 Generating comprehensive PDF report...")
                progress.update(task, completed=30)
                pdf_path = generate_pdf_report("geoserver")
                
                # Step 4: Finalize
                console.print("✅ PDF generation complete!")
                progress.update(task, completed=100)
            
            console.print()
            if pdf_path:
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated successfully![/]")
                console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Report: {pdf_path}[/]")
                
                # Ask user if they want to open the PDF
                if Confirm.ask(f"[{KARTOZA_COLORS['highlight2']}]Open PDF report now?[/]", default=True):
                    try:
                        subprocess.run(["xdg-open", str(pdf_path)], check=False)
                        console.print(f"[{KARTOZA_COLORS['highlight4']}]📖 Opening PDF in default viewer...[/]")
                    except Exception as e:
                        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Could not open PDF: {e}[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ No recent results found or failed to generate report[/]")
                console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Run some benchmark tests first[/]")
                
        except ImportError:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ PDF generation requires additional dependencies[/]")
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating report: {e}[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def select_previous_report_menu(self):
        """Select and generate PDF report from previous benchmark results"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📋 Select Previous Benchmark Results[/]")
        console.print()
        
        # Find all available result files
        results_dir = Path("results")
        if not results_dir.exists():
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No results directory found[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        pattern = str(results_dir / "consolidated_*_results_*.json")
        result_files = sorted(glob.glob(pattern), reverse=True)
        
        if not result_files:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No previous benchmark results found[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]💡 Run some benchmark tests first[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Found {len(result_files)} previous benchmark results:[/]")
        console.print()
        
        # Create selection table
        table = Table(title="Available Benchmark Results", show_header=True)
        table.add_column("#", justify="center", style=f"{KARTOZA_COLORS['highlight3']}")
        table.add_column("Date/Time", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("File", style=f"{KARTOZA_COLORS['highlight2']}")
        
        # Show top 10 most recent files
        display_files = result_files[:10]
        
        for i, file_path in enumerate(display_files):
            filename = Path(file_path).name
            # Extract datetime from filename if possible
            try:
                # Example: consolidated_geoserver_results_20241116_093401.json
                parts = filename.replace('consolidated_', '').replace('_results_', '_').replace('.json', '').split('_')
                if len(parts) >= 3:
                    date_str = parts[-2]  # 20241116
                    time_str = parts[-1]  # 093401
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                else:
                    formatted_date = "Unknown"
            except:
                formatted_date = "Unknown"
            
            table.add_row(str(i + 1), formatted_date, filename)
        
        if len(result_files) > 10:
            table.add_row("...", f"({len(result_files) - 10} more files)", "...")
        
        console.print(table)
        console.print()
        
        if len(display_files) == 0:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No results to display[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create file choices for interactive selection
        file_choices = []
        for file_path in display_files:
            filename = Path(file_path).name
            # Extract datetime from filename if possible
            try:
                # Example: consolidated_geoserver_results_20241116_093401.json
                parts = filename.replace('consolidated_', '').replace('_results_', '_').replace('.json', '').split('_')
                if len(parts) >= 3:
                    date_str = parts[-2]  # 20241116
                    time_str = parts[-1]  # 093401
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                    file_choices.append(f"{formatted_date} - {filename}")
                else:
                    file_choices.append(filename)
            except:
                file_choices.append(filename)
        
        # Get user selection
        try:
            choice_index = self._interactive_select(
                file_choices,
                "Select result file to generate report from:",
                show_skip_option=True
            )
            
            if choice_index is None:
                return  # User cancelled
            
            selected_file = display_files[choice_index]
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Selected: {Path(selected_file).name}[/]")
            console.print()
            
            # Generate report from selected file with progress bar
            try:
                from ..common.pdf_generator import generate_pdf_report
                
                # Create a clean progress bar with messages on separate lines
                with Progress(
                    SpinnerColumn(),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True
                ) as progress:
                    
                    # Add main task
                    task = progress.add_task("Generating PDF Report", total=100)
                    
                    # Step 1: Load selected results
                    console.print(f"📂 Loading results from {Path(selected_file).name}...")
                    progress.update(task, completed=10)
                    
                    # Step 2: Initialize PDF generator
                    console.print("📋 Initializing PDF generator...")
                    progress.update(task, completed=20)
                    
                    # Step 3: Generate the actual PDF
                    console.print("📄 Generating comprehensive PDF report...")
                    progress.update(task, completed=30)
                    pdf_path = generate_pdf_report("geoserver", results_file=selected_file)
                    
                    # Step 4: Finalize
                    console.print("✅ PDF generation complete!")
                    progress.update(task, completed=100)
                
                console.print()
                if pdf_path:
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated successfully![/]")
                    console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Report: {pdf_path}[/]")
                    
                    # Ask user if they want to open the PDF
                    if Confirm.ask(f"[{KARTOZA_COLORS['highlight2']}]Open PDF report now?[/]", default=True):
                        try:
                            subprocess.run(["xdg-open", str(pdf_path)], check=False)
                            console.print(f"[{KARTOZA_COLORS['highlight4']}]📖 Opening PDF in default viewer...[/]")
                        except Exception as e:
                            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Could not open PDF: {e}[/]")
                else:
                    console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to generate report[/]")
                    
            except ImportError:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ PDF generation requires additional dependencies[/]")
            except Exception as e:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating report: {e}[/]")
                
        except (ValueError, KeyboardInterrupt):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]❌ Selection cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def view_results_menu(self):
        """Menu for viewing test results"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 View Test Results[/]")
        console.print()
        
        # Show summary table
        summary = self.tester.get_results_summary()
        if summary:
            console.print(summary)
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]No test results found. Run some tests first![/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def main_menu(self):
        """Display and handle the main menu"""
        
        while True:
            # Dynamic menu based on server configuration - evaluated each loop iteration
            if not self.server_configured:
                menu_options = [
                    ("🔧 Setup Server Connection", self.setup_server),
                    ("📄 Generate Report from Latest Results", self.generate_report_from_latest_menu),
                    ("📋 Select Previous Results for Report", self.select_previous_report_menu),
                    ("📊 Configure Monitoring", self.monitoring_config_menu),
                    ("📖 Help & Info", self._show_help),
                    ("❌ Exit", self.exit_app)
                ]
            else:
                menu_options = [
                    ("🔧 Change Server Connection", self.setup_server),
                    ("🖼️  Preview Layer Maps", self.preview_layer_menu),
                    ("⚡ Run Single Layer Test", self.single_test_menu), 
                    ("🔥 Run Comprehensive Tests", self.comprehensive_test_menu),
                    ("📊 View Test Results", self.view_results_menu),
                    ("📄 Generate Report from Latest Results", self.generate_report_from_latest_menu),
                    ("📋 Select Previous Results for Report", self.select_previous_report_menu),
                    ("📊 Configure Monitoring", self.monitoring_config_menu),
                    ("🔍 Test Connectivity", self.test_connectivity_menu),
                    ("🗺️  Show Layer Info", self.show_layer_info),
                    ("🎨 Image Rendering Info", self.show_image_capabilities),
                    ("❌ Exit", self.exit_app)
                ]
            
            console.clear()
            self.show_banner()
            
            console.print(f"[{KARTOZA_COLORS['highlight2']}]Main Menu[/]")
            console.print()
            
            # Extract option texts for interactive selection
            option_texts = [option_text for option_text, _ in menu_options]
            
            try:
                choice_index = self._interactive_select(
                    option_texts,
                    "Select an option:"
                )
                
                if choice_index is None:
                    # User cancelled or selected back
                    continue
                
                console.print()
                _, handler = menu_options[choice_index]
                handler()
                
            except (KeyboardInterrupt, EOFError):
                self.exit_app()
    
    def show_image_capabilities(self):
        """Show image rendering capabilities"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🎨 Image Rendering Capabilities[/]")
        console.print()
        
        self.image_renderer.print_capabilities()
        console.print()
        
        Prompt.ask("Press Enter to continue", default="")
    
    def _show_help(self):
        """Show help information"""
        help_text = Text()
        help_text.append("GeoServer Load Testing Suite", style=f"bold {KARTOZA_COLORS['highlight2']}")
        help_text.append("\n\n")
        help_text.append("This tool discovers layers dynamically from GeoServer instances\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("and provides comprehensive load testing capabilities.\n\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("Getting Started:\n", style=f"bold {KARTOZA_COLORS['highlight1']}")
        help_text.append("1. Setup server connection (provide subdomain)\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("2. Tool will discover layers via WMS GetCapabilities\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("3. Run connectivity tests, previews, or load tests\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("\n")
        help_text.append("Features:\n", style=f"bold {KARTOZA_COLORS['highlight1']}")
        help_text.append("• Dynamic layer discovery from any GeoServer\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("• Subdomain history management\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("• Apache Bench load testing integration\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("• Map previews with metadata from capabilities\n", style=f"{KARTOZA_COLORS['highlight3']}")
        help_text.append("• Rich progress tracking and reporting\n", style=f"{KARTOZA_COLORS['highlight3']}")
        
        panel = Panel.fit(
            help_text,
            border_style=f"{KARTOZA_COLORS['highlight4']}",
            title="Help & Information",
            padding=(1, 2)
        )
        
        console.print(panel)
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def monitoring_config_menu(self):
        """Main monitoring configuration menu"""
        while True:
            console.clear()
            self.show_banner()
            
            console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Monitoring Configuration[/]")
            console.print()
            
            # Show current configuration summary
            summary = self.monitoring_config.get_config_summary()
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Configuration Summary:[/]")
            console.print(f"  • Total endpoints: {summary['total_endpoints']}")
            console.print(f"  • Enabled endpoints: {summary['enabled_endpoints']}")
            console.print(f"  • Prometheus endpoints: {summary['prometheus_endpoints']}")
            console.print(f"  • Grafana endpoints: {summary['grafana_endpoints']}")
            console.print(f"  • Config file: {summary['config_file']}")
            console.print()
            
            menu_options = [
                ("📋 List All Endpoints", self._list_monitoring_endpoints),
                ("➕ Add New Endpoint", self._add_monitoring_endpoint), 
                ("✏️  Edit Endpoint", self._edit_monitoring_endpoint),
                ("🔧 Test Endpoint Connection", self._test_monitoring_endpoint),
                ("🔄 Toggle Endpoint Enable/Disable", self._toggle_monitoring_endpoint),
                ("❌ Delete Endpoint", self._delete_monitoring_endpoint),
                ("📤 Export Environment Variables", self._export_monitoring_env_vars),
            ]
            
            # Extract option texts for interactive selection
            option_texts = [option_text for option_text, _ in menu_options]
            
            try:
                choice_index = self._interactive_select(
                    option_texts,
                    "Select an option:",
                    show_skip_option=True
                )
                
                if choice_index is None:
                    break  # User selected back or cancelled
                    
                console.print()
                _, handler = menu_options[choice_index]
                if handler:
                    handler()
                    
            except (KeyboardInterrupt, EOFError):
                break
    
    def _list_monitoring_endpoints(self):
        """List all monitoring endpoints"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📋 Monitoring Endpoints[/]")
        console.print()
        
        endpoints = self.monitoring_config.read_all_endpoints()
        
        if not endpoints:
            console.print(f"[{KARTOZA_COLORS['alert']}]No monitoring endpoints configured[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create endpoints table
        table = Table(title="Monitoring Endpoints", show_header=True)
        table.add_column("Name", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Type", style=f"{KARTOZA_COLORS['highlight1']}")
        table.add_column("URL", style=f"{KARTOZA_COLORS['highlight3']}")
        table.add_column("Status", justify="center")
        table.add_column("Description", style=f"{KARTOZA_COLORS['highlight4']}")
        
        for name, endpoint in endpoints.items():
            status = "✅ Enabled" if endpoint.enabled else "❌ Disabled"
            description = endpoint.description or "No description"
            
            table.add_row(
                endpoint.name,
                endpoint.endpoint_type.upper(),
                endpoint.url,
                status,
                description[:50] + "..." if len(description) > 50 else description
            )
        
        console.print(table)
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _add_monitoring_endpoint(self):
        """Add a new monitoring endpoint"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]➕ Add New Monitoring Endpoint[/]")
        console.print()
        
        try:
            # Get endpoint details
            name = Prompt.ask("Endpoint name", default="")
            if not name:
                console.print(f"[{KARTOZA_COLORS['alert']}]Name is required[/]")
                Prompt.ask("Press Enter to continue", default="")
                return
            
            # Check if name already exists
            if self.monitoring_config.read_endpoint(name):
                console.print(f"[{KARTOZA_COLORS['alert']}]Endpoint '{name}' already exists[/]")
                Prompt.ask("Press Enter to continue", default="")
                return
            
            # Interactive endpoint type selection
            endpoint_types = ["Prometheus", "Grafana"]
            type_index = self._interactive_select(
                endpoint_types,
                "Select endpoint type:"
            )
            
            if type_index is None:
                console.print(f"[{KARTOZA_COLORS['highlight3']}]Operation cancelled[/]")
                console.print()
                Prompt.ask("Press Enter to continue", default="")
                return
            
            endpoint_type = endpoint_types[type_index].lower()
            
            url = Prompt.ask("Endpoint URL", default="http://localhost:9090" if endpoint_type == "prometheus" else "http://localhost:3000")
            
            api_key = None
            if endpoint_type == "grafana":
                api_key = Prompt.ask("API Key (optional, press Enter to skip)", default="")
                if not api_key:
                    api_key = None
            
            description = Prompt.ask("Description (optional)", default="")
            if not description:
                description = None
            
            enabled = Confirm.ask("Enable endpoint?", default=True)
            
            # Create the endpoint
            success = self.monitoring_config.create_endpoint(
                name=name,
                endpoint_type=endpoint_type,
                url=url,
                api_key=api_key,
                description=description,
                enabled=enabled
            )
            
            if success:
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Endpoint '{name}' created successfully![/]")
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to create endpoint[/]")
            
        except (KeyboardInterrupt, EOFError):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Operation cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _edit_monitoring_endpoint(self):
        """Edit an existing monitoring endpoint"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]✏️  Edit Monitoring Endpoint[/]")
        console.print()
        
        endpoints = self.monitoring_config.read_all_endpoints()
        if not endpoints:
            console.print(f"[{KARTOZA_COLORS['alert']}]No endpoints to edit[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create endpoint choices for interactive selection
        endpoint_names = list(endpoints.keys())
        endpoint_choices = []
        for name in endpoint_names:
            endpoint = endpoints[name]
            status = "✅" if endpoint.enabled else "❌"
            endpoint_choices.append(f"{status} {name} ({endpoint.endpoint_type.upper()})")
        
        try:
            choice_index = self._interactive_select(
                endpoint_choices,
                "Select endpoint to edit:",
                show_skip_option=True
            )
            
            if choice_index is None:
                return  # User cancelled
            
            selected_name = endpoint_names[choice_index]
            endpoint = endpoints[selected_name]
            
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Editing: {selected_name}[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Leave fields empty to keep current values[/]")
            console.print()
            
            # Edit fields
            new_url = Prompt.ask(f"URL (current: {endpoint.url})", default="")
            
            new_api_key = None
            if endpoint.endpoint_type == "grafana":
                current_key = endpoint.api_key or "Not set"
                new_api_key = Prompt.ask(f"API Key (current: {current_key})", default="")
                if not new_api_key:
                    new_api_key = endpoint.api_key
            
            new_description = Prompt.ask(f"Description (current: {endpoint.description or 'Not set'})", default="")
            
            # Prepare update data
            update_data = {}
            if new_url:
                update_data['url'] = new_url
            if endpoint.endpoint_type == "grafana" and new_api_key != endpoint.api_key:
                update_data['api_key'] = new_api_key
            if new_description:
                update_data['description'] = new_description
            
            if update_data:
                success = self.monitoring_config.update_endpoint(selected_name, **update_data)
                if success:
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Endpoint updated successfully![/]")
                else:
                    console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to update endpoint[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['highlight3']}]No changes made[/]")
                
        except (KeyboardInterrupt, EOFError, ValueError):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Operation cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _test_monitoring_endpoint(self):
        """Test connection to a monitoring endpoint"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🔧 Test Endpoint Connection[/]")
        console.print()
        
        endpoints = self.monitoring_config.read_all_endpoints()
        if not endpoints:
            console.print(f"[{KARTOZA_COLORS['alert']}]No endpoints to test[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create endpoint choices for interactive selection  
        endpoint_names = list(endpoints.keys())
        endpoint_choices = []
        for name in endpoint_names:
            endpoint = endpoints[name]
            status = "✅" if endpoint.enabled else "❌"
            endpoint_choices.append(f"{status} {name} ({endpoint.endpoint_type.upper()}) - {endpoint.url}")
        
        try:
            choice_index = self._interactive_select(
                endpoint_choices,
                "Select endpoint to test:",
                show_skip_option=True
            )
            
            if choice_index is None:
                return  # User cancelled
            
            selected_name = endpoint_names[choice_index]
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Testing connection to {selected_name}...[/]")
            
            with console.status("Testing connection..."):
                success, message = self.monitoring_config.test_endpoint_connection(selected_name)
            
            if success:
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Connection successful: {message}[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Connection failed: {message}[/]")
                
        except (KeyboardInterrupt, EOFError, ValueError):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Test cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _toggle_monitoring_endpoint(self):
        """Toggle enable/disable status of an endpoint"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]🔄 Toggle Endpoint Status[/]")
        console.print()
        
        endpoints = self.monitoring_config.read_all_endpoints()
        if not endpoints:
            console.print(f"[{KARTOZA_COLORS['alert']}]No endpoints to toggle[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create endpoint choices for interactive selection
        endpoint_names = list(endpoints.keys())
        endpoint_choices = []
        for name in endpoint_names:
            endpoint = endpoints[name]
            status = "✅ Enabled" if endpoint.enabled else "❌ Disabled"
            endpoint_choices.append(f"{status} {name} ({endpoint.endpoint_type.upper()})")
        
        try:
            choice_index = self._interactive_select(
                endpoint_choices,
                "Select endpoint to toggle:",
                show_skip_option=True
            )
            
            if choice_index is None:
                return  # User cancelled
            
            selected_name = endpoint_names[choice_index]
            endpoint = endpoints[selected_name]
            
            current_status = "enabled" if endpoint.enabled else "disabled"
            new_status = "disabled" if endpoint.enabled else "enabled"
            
            if Confirm.ask(f"Toggle '{selected_name}' from {current_status} to {new_status}?"):
                success = self.monitoring_config.toggle_endpoint(selected_name)
                if success:
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Endpoint '{selected_name}' is now {new_status}[/]")
                else:
                    console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to toggle endpoint[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['highlight3']}]No changes made[/]")
                
        except (KeyboardInterrupt, EOFError, ValueError):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Operation cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _delete_monitoring_endpoint(self):
        """Delete a monitoring endpoint"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]❌ Delete Monitoring Endpoint[/]")
        console.print()
        
        endpoints = self.monitoring_config.read_all_endpoints()
        if not endpoints:
            console.print(f"[{KARTOZA_COLORS['alert']}]No endpoints to delete[/]")
            console.print()
            Prompt.ask("Press Enter to continue", default="")
            return
        
        # Create endpoint choices for interactive selection
        endpoint_names = list(endpoints.keys())
        endpoint_choices = []
        for name in endpoint_names:
            endpoint = endpoints[name]
            status = "✅" if endpoint.enabled else "❌"
            endpoint_choices.append(f"{status} {name} ({endpoint.endpoint_type.upper()}) - {endpoint.url}")
        
        try:
            choice_index = self._interactive_select(
                endpoint_choices,
                "Select endpoint to delete:",
                show_skip_option=True
            )
            
            if choice_index is None:
                return  # User cancelled
            
            selected_name = endpoint_names[choice_index]
            
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  WARNING: This will permanently delete the endpoint '{selected_name}'[/]")
            console.print()
            
            if Confirm.ask(f"Are you sure you want to delete '{selected_name}'?", default=False):
                success = self.monitoring_config.delete_endpoint(selected_name)
                if success:
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Endpoint '{selected_name}' deleted successfully[/]")
                else:
                    console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to delete endpoint[/]")
            else:
                console.print(f"[{KARTOZA_COLORS['highlight3']}]Deletion cancelled[/]")
                
        except (KeyboardInterrupt, EOFError, ValueError):
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Operation cancelled[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def _export_monitoring_env_vars(self):
        """Export monitoring configuration as environment variables"""
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📤 Export Environment Variables[/]")
        console.print()
        
        env_vars = self.monitoring_config.export_to_env_vars()
        
        if env_vars:
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Environment variables for active endpoints:[/]")
            console.print()
            
            for var_name, var_value in env_vars.items():
                console.print(f"export {var_name}=\"{var_value}\"")
            
            console.print()
            console.print(f"[{KARTOZA_COLORS['highlight4']}]💡 You can copy these commands to set environment variables[/]")
            console.print(f"[{KARTOZA_COLORS['highlight4']}]   or add them to your shell profile (.bashrc, .zshrc, etc.)[/]")
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]No active endpoints found[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]Enable at least one endpoint to export environment variables[/]")
        
        console.print()
        Prompt.ask("Press Enter to continue", default="")
    
    def exit_app(self):
        """Exit the application"""
        console.print(f"[{KARTOZA_COLORS['highlight4']}]👋 Goodbye![/]")
        sys.exit(0)
    
    def run(self):
        """Main entry point for the UI"""
        try:
            self.main_menu()
        except KeyboardInterrupt:
            self.exit_app()