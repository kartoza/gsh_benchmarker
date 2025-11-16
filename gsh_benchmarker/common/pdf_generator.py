#!/usr/bin/env python3
"""
Comprehensive Benchmark PDF Report Generator for GSH Benchmarker Suite

Generates detailed PDF reports from benchmark test results including charts,
statistics, and performance analysis for all benchmarker types.
"""

import json
import argparse
import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_pdf import PdfPages
    import seaborn as sns
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import ReportLab for advanced PDF generation
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from io import BytesIO
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .reports import ReportGenerator, find_latest_report_file
from .config import REPORTS_DIR, RESULTS_DIR
from .colors import KARTOZA_COLORS

console = Console()

# Dynamic layer metadata discovery
def get_layer_metadata_from_capabilities(geoserver_url: str, layer_name: str) -> Dict[str, str]:
    """Get layer metadata from GeoServer capabilities instead of hardcoded values"""
    try:
        from ..geoserver.capabilities import discover_layers
        layers, service_info = discover_layers(geoserver_url)
        
        # Find matching layer
        for layer in layers:
            if layer.name == layer_name or layer.name == f"CAS:{layer_name}":
                return {
                    "title": layer.title or layer_name.replace('_', ' ').title(),
                    "description": layer.abstract or f"Analysis for {layer.title or layer_name}",
                    "data_source": service_info.get('title', 'GeoServer Service'),
                    "resolution": "From service capabilities",
                    "update_frequency": "Unknown"
                }
    except Exception as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Could not fetch layer metadata: {e}[/]")
    
    # Fallback to basic metadata if capabilities discovery fails
    return {
        "title": layer_name.replace('_', ' ').title(),
        "description": f"Performance analysis for {layer_name}",
        "data_source": "Unknown",
        "resolution": "Unknown", 
        "update_frequency": "Unknown"
    }


class PDFReportGenerator:
    """Generate comprehensive PDF reports from benchmark results"""
    
    def __init__(self, service_type: str = "benchmark", output_dir: Path = None):
        self.service_type = service_type
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(exist_ok=True)
        
        if not MATPLOTLIB_AVAILABLE:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Matplotlib not available. Install with: pip install matplotlib[/]")
            raise ImportError("Matplotlib required for PDF generation")
    
    def generate_comprehensive_report(
        self, 
        results_pattern: str = None,
        output_filename: str = None
    ) -> Optional[Path]:
        """Generate a comprehensive PDF report from consolidated results"""
        
        if results_pattern is None:
            results_pattern = f"consolidated_{self.service_type}_results_*.json"
        
        # Find latest consolidated results file
        consolidated_files = list(RESULTS_DIR.glob(results_pattern))
        if not consolidated_files:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No consolidated results found matching: {results_pattern}[/]")
            return None
        
        latest_file = max(consolidated_files, key=lambda p: p.stat().st_mtime)
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Generating report from: {latest_file}[/]")
        
        # Load results
        with open(latest_file) as f:
            data = json.load(f)
        
        # Generate output filename if not provided
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            service_type = data.get('test_suite', {}).get('service_type', self.service_type)
            output_filename = f"{service_type}_comprehensive_report_{timestamp}.pdf"
        
        output_path = self.output_dir / output_filename
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating PDF report...", total=100)
            
            with PdfPages(output_path) as pdf:
                # Page 1: Title and Summary
                progress.update(task, advance=20, description="Creating title page...")
                self._create_title_page(pdf, data)
                
                # Page 2: Executive Summary
                progress.update(task, advance=20, description="Creating summary...")
                self._create_summary_page(pdf, data)
                
                # Page 3-N: Performance Charts
                progress.update(task, advance=30, description="Creating performance charts...")
                self._create_performance_charts(pdf, data)
                
                # Page N+1: Detailed Results Table
                progress.update(task, advance=20, description="Creating detailed tables...")
                self._create_detailed_tables(pdf, data)
                
                # Final page: Recommendations
                progress.update(task, advance=10, description="Creating recommendations...")
                self._create_recommendations_page(pdf, data)
        
        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated: {output_path}[/]")
        return output_path
    
    def _create_title_page(self, pdf: PdfPages, data: Dict[str, Any]):
        """Create title page"""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')
        
        test_suite = data.get('test_suite', {})
        
        # Title
        ax.text(0.5, 0.8, test_suite.get('name', 'Benchmark Report'), 
                fontsize=24, fontweight='bold', ha='center')
        
        # Subtitle
        service_type = test_suite.get('service_type', 'unknown')
        ax.text(0.5, 0.75, f"{service_type.title()} Load Testing Results", 
                fontsize=16, ha='center', style='italic')
        
        # Test info
        info_lines = [
            f"Test Date: {test_suite.get('date', 'Unknown')[:10]}",
            f"Total Tests: {test_suite.get('total_tests', 0)}",
            f"Targets Tested: {len(test_suite.get('targets_tested', []))}",
            f"Requests per Test: {test_suite.get('total_requests_per_test', 'Unknown')}",
        ]
        
        for i, line in enumerate(info_lines):
            ax.text(0.5, 0.6 - i * 0.05, line, fontsize=12, ha='center')
        
        # Footer
        ax.text(0.5, 0.1, "Generated by GSH Benchmarker Suite", 
                fontsize=10, ha='center', style='italic', color='gray')
        ax.text(0.5, 0.05, f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                fontsize=8, ha='center', color='gray')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_summary_page(self, pdf: PdfPages, data: Dict[str, Any]):
        """Create executive summary page"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(8.5, 11))
        fig.suptitle('Executive Summary', fontsize=16, fontweight='bold')
        
        results = data.get('results', [])
        if not results:
            ax1.text(0.5, 0.5, 'No results data available', ha='center', va='center')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            return
        
        # Extract metrics
        rps_values = []
        response_times = []
        success_rates = []
        targets = []
        
        for result in results:
            result_data = result.get('results', {})
            rps_values.append(float(result_data.get('requests_per_second', 0)))
            response_times.append(float(result_data.get('mean_response_time_ms', 0)))
            success_rates.append(float(result_data.get('success_rate', '0').rstrip('%')))
            targets.append(result.get('target', 'Unknown'))
        
        # Chart 1: RPS Distribution
        ax1.hist(rps_values, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_title('Requests per Second Distribution')
        ax1.set_xlabel('RPS')
        ax1.set_ylabel('Frequency')
        
        # Chart 2: Response Time vs RPS
        ax2.scatter(response_times, rps_values, alpha=0.6, color='orange')
        ax2.set_title('Response Time vs RPS')
        ax2.set_xlabel('Response Time (ms)')
        ax2.set_ylabel('RPS')
        
        # Chart 3: Success Rate Distribution
        ax3.hist(success_rates, bins=10, alpha=0.7, color='lightgreen', edgecolor='black')
        ax3.set_title('Success Rate Distribution')
        ax3.set_xlabel('Success Rate (%)')
        ax3.set_ylabel('Frequency')
        
        # Chart 4: Summary Stats
        ax4.axis('off')
        stats_text = [
            f"Average RPS: {np.mean(rps_values):.1f}",
            f"Max RPS: {np.max(rps_values):.1f}",
            f"Average Response Time: {np.mean(response_times):.1f} ms",
            f"Average Success Rate: {np.mean(success_rates):.1f}%",
            f"Total Targets: {len(set(targets))}",
            f"Total Tests: {len(results)}",
        ]
        
        for i, stat in enumerate(stats_text):
            ax4.text(0.1, 0.9 - i * 0.15, stat, fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_performance_charts(self, pdf: PdfPages, data: Dict[str, Any]):
        """Create performance analysis charts"""
        results = data.get('results', [])
        if not results:
            return
        
        # Group results by target
        target_results = {}
        for result in results:
            target = result.get('target', 'Unknown')
            if target not in target_results:
                target_results[target] = []
            target_results[target].append(result)
        
        # Create charts for each target (max 4 per page)
        targets = list(target_results.keys())
        pages_needed = (len(targets) + 3) // 4
        
        for page in range(pages_needed):
            fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))
            fig.suptitle(f'Performance Analysis - Page {page + 1}', fontsize=14, fontweight='bold')
            axes = axes.flatten()
            
            start_idx = page * 4
            end_idx = min(start_idx + 4, len(targets))
            
            for i, target_idx in enumerate(range(start_idx, end_idx)):
                target = targets[target_idx]
                target_data = target_results[target]
                
                ax = axes[i]
                
                # Extract data for this target
                concurrency_levels = []
                rps_values = []
                response_times = []
                
                for result in target_data:
                    concurrency_levels.append(result.get('concurrency_level', 0))
                    result_data = result.get('results', {})
                    rps_values.append(float(result_data.get('requests_per_second', 0)))
                    response_times.append(float(result_data.get('mean_response_time_ms', 0)))
                
                # Sort by concurrency level
                sorted_data = sorted(zip(concurrency_levels, rps_values, response_times))
                concurrency_levels, rps_values, response_times = zip(*sorted_data)
                
                # Create dual-axis plot
                ax2 = ax.twinx()
                
                line1 = ax.plot(concurrency_levels, rps_values, 'b-o', label='RPS')
                line2 = ax2.plot(concurrency_levels, response_times, 'r-s', label='Response Time')
                
                ax.set_xlabel('Concurrency Level')
                ax.set_ylabel('Requests per Second', color='b')
                ax2.set_ylabel('Response Time (ms)', color='r')
                ax.set_title(target[:30] + ('...' if len(target) > 30 else ''))
                
                # Add legend
                lines = line1 + line2
                labels = [l.get_label() for l in lines]
                ax.legend(lines, labels, loc='upper left')
            
            # Hide unused subplots
            for i in range(end_idx - start_idx, 4):
                axes[i].axis('off')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
    
    def _create_detailed_tables(self, pdf: PdfPages, data: Dict[str, Any]):
        """Create detailed results tables"""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')
        fig.suptitle('Detailed Test Results', fontsize=16, fontweight='bold')
        
        results = data.get('results', [])
        if not results:
            ax.text(0.5, 0.5, 'No detailed results available', ha='center', va='center')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            return
        
        # Prepare table data
        headers = ['Target', 'Concurrency', 'RPS', 'Avg Time (ms)', 'Failed', 'Success %']
        table_data = []
        
        for result in results[:50]:  # Limit to first 50 results
            target = result.get('target', 'Unknown')
            if len(target) > 20:
                target = target[:17] + '...'
            
            result_data = result.get('results', {})
            row = [
                target,
                str(result.get('concurrency_level', 0)),
                f"{float(result_data.get('requests_per_second', 0)):.1f}",
                f"{float(result_data.get('mean_response_time_ms', 0)):.1f}",
                result_data.get('failed_requests', '0'),
                result_data.get('success_rate', '0%'),
            ]
            table_data.append(row)
        
        # Create table
        table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        
        # Style the table
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_recommendations_page(self, pdf: PdfPages, data: Dict[str, Any]):
        """Create recommendations page"""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')
        
        ax.text(0.5, 0.95, 'Performance Recommendations', 
                fontsize=18, fontweight='bold', ha='center')
        
        results = data.get('results', [])
        if not results:
            ax.text(0.5, 0.5, 'No data available for recommendations', ha='center', va='center')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            return
        
        # Analyze results for recommendations
        rps_values = [float(r.get('results', {}).get('requests_per_second', 0)) for r in results]
        success_rates = [float(r.get('results', {}).get('success_rate', '0').rstrip('%')) for r in results]
        response_times = [float(r.get('results', {}).get('mean_response_time_ms', 0)) for r in results]
        
        avg_rps = np.mean(rps_values)
        avg_success = np.mean(success_rates)
        avg_response = np.mean(response_times)
        
        recommendations = []
        
        # Generate recommendations based on performance metrics
        if avg_success < 95:
            recommendations.append(
                "• Consider reducing concurrency levels to improve success rates"
            )
        
        if avg_response > 1000:
            recommendations.append(
                "• High response times detected - investigate server capacity"
            )
        
        if avg_rps < 10:
            recommendations.append(
                "• Low throughput detected - consider optimizing server configuration"
            )
        
        # Group performance by target
        target_performance = {}
        for result in results:
            target = result.get('target', 'Unknown')
            rps = float(result.get('results', {}).get('requests_per_second', 0))
            if target not in target_performance:
                target_performance[target] = []
            target_performance[target].append(rps)
        
        # Find best and worst performing targets
        target_avg_rps = {t: np.mean(perfs) for t, perfs in target_performance.items()}
        best_target = max(target_avg_rps, key=target_avg_rps.get)
        worst_target = min(target_avg_rps, key=target_avg_rps.get)
        
        recommendations.extend([
            f"• Best performing target: {best_target} ({target_avg_rps[best_target]:.1f} RPS avg)",
            f"• Investigate optimization opportunities for: {worst_target}",
            "• Monitor server resources during peak load periods",
            "• Consider implementing caching strategies for frequently accessed layers",
        ])
        
        # Display recommendations
        y_pos = 0.8
        for rec in recommendations:
            ax.text(0.1, y_pos, rec, fontsize=11, ha='left', wrap=True)
            y_pos -= 0.08
        
        # Add footer
        ax.text(0.5, 0.1, "For more detailed analysis, review the performance charts and detailed results.", 
                fontsize=10, ha='center', style='italic', color='gray')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)


class ReportLabPDFGenerator:
    """Advanced PDF report generator using ReportLab for professional layouts"""
    
    def __init__(self, service_type: str = "geoserver", output_dir: Path = None, geoserver_url: str = None):
        self.service_type = service_type
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(exist_ok=True)
        self.geoserver_url = geoserver_url or "https://climate-adaptation-services.geospatialhosting.com/geoserver"
        self.wms_base = f"{self.geoserver_url}/wms"
        
        if not REPORTLAB_AVAILABLE:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ ReportLab not available. Install with: pip install reportlab[/]")
            raise ImportError("ReportLab required for professional PDF generation")
        
        # Set up matplotlib style if available
        if MATPLOTLIB_AVAILABLE:
            try:
                plt.style.use('default')
                if hasattr(sns, 'set_palette'):
                    sns.set_palette([KARTOZA_COLORS["highlight2"], KARTOZA_COLORS["highlight1"], 
                                   KARTOZA_COLORS["highlight4"], KARTOZA_COLORS["alert"]])
            except:
                pass
    
    def capture_map_image(self, layer_name: str, width: int = 800, height: int = 600) -> Optional[str]:
        """Capture a map image from WMS for the report"""
        bbox = "3.0501,50.7286,7.3450,53.7185"  # Netherlands bounding box - TODO: get from capabilities
        
        # Try both with and without workspace prefix
        layer_variations = [f"CAS:{layer_name}", layer_name]
        
        for layer_variant in layer_variations:
            wms_params = {
                'SERVICE': 'WMS',
                'VERSION': '1.1.1',
                'REQUEST': 'GetMap',
                'LAYERS': layer_variant,
                'STYLES': '',
                'BBOX': bbox,
                'WIDTH': str(width),
                'HEIGHT': str(height),
                'FORMAT': 'image/png',
                'SRS': 'EPSG:4326'
            }
            
            try:
                console.print(f"[{KARTOZA_COLORS['highlight3']}]🗺️  Capturing map image for {layer_variant}...[/]")
                response = requests.get(self.wms_base, params=wms_params, timeout=60)
                
                if response.status_code == 200:
                    # Check if response is actually an image
                    if response.content.startswith(b'<?xml') or b'ServiceException' in response.content:
                        console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  WMS error for {layer_variant}[/]")
                        continue
                    
                    # Clean filename by removing invalid characters
                    clean_layer_name = layer_name.replace(':', '_').replace('/', '_')
                    image_path = self.output_dir / f"{clean_layer_name}_map.png"
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Map image saved: {image_path}[/]")
                    return str(image_path)
                    
            except Exception as e:
                console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Failed to capture {layer_variant}: {e}[/]")
                continue
        
        console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Could not capture map for {layer_name}[/]")
        return None
    
    def create_concurrency_analysis_chart(self, layer_results: List[Dict], layer_name: str) -> Optional[str]:
        """Create concurrency analysis chart showing performance vs concurrency level"""
        if not MATPLOTLIB_AVAILABLE:
            return None
            
        try:
            console.print(f"[{KARTOZA_COLORS['highlight3']}]📊 Creating performance chart for {layer_name} with {len(layer_results)} results[/]")
            
            concurrencies = []
            rps_values = []
            response_times = []
            
            for result in layer_results:
                if result.get('results'):
                    def safe_float_convert(value, default=0):
                        try:
                            str_val = str(value).replace(',', '.').split('\n')[0]
                            return float(str_val)
                        except (ValueError, TypeError):
                            return default
                    
                    concurrencies.append(result['concurrency_level'])
                    rps_values.append(safe_float_convert(result['results'].get('requests_per_second', 0)))
                    response_times.append(safe_float_convert(result['results'].get('mean_response_time_ms', 0)))
            
            if not concurrencies:
                return None
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
            fig.suptitle(f'Performance Analysis: {layer_name}', 
                        fontsize=16, color=KARTOZA_COLORS["highlight2"], fontweight='bold')
            
            # Requests per second vs concurrency
            ax1.plot(concurrencies, rps_values, 'o-', 
                    color=KARTOZA_COLORS["highlight1"], linewidth=3, markersize=8)
            ax1.set_xlabel('Concurrent Connections')
            ax1.set_ylabel('Requests per Second')
            ax1.set_title('Throughput vs Concurrency Level', color=KARTOZA_COLORS["highlight4"])
            ax1.grid(True, alpha=0.3)
            if max(concurrencies) > min(concurrencies):
                ax1.set_xscale('log')
            
            # Response time vs concurrency
            ax2.plot(concurrencies, response_times, 's-', 
                    color=KARTOZA_COLORS["highlight4"], linewidth=3, markersize=8)
            ax2.set_xlabel('Concurrent Connections')
            ax2.set_ylabel('Mean Response Time (ms)')
            ax2.set_title('Response Time vs Concurrency Level', color=KARTOZA_COLORS["highlight4"])
            ax2.grid(True, alpha=0.3)
            if max(concurrencies) > min(concurrencies):
                ax2.set_xscale('log')
            
            # Response time distribution histogram
            ax3.hist(response_times, bins=min(15, len(response_times)), 
                    color=KARTOZA_COLORS["highlight1"], alpha=0.7, edgecolor='black')
            ax3.set_xlabel('Response Time (ms)')
            ax3.set_ylabel('Number of Tests')
            ax3.set_title('Response Time Distribution', color=KARTOZA_COLORS["highlight4"])
            ax3.grid(True, alpha=0.3)
            
            # Add statistics to histogram
            if response_times:
                mean_time = np.mean(response_times)
                median_time = np.median(response_times)
                ax3.axvline(mean_time, color=KARTOZA_COLORS["alert"], linestyle='--', 
                           label=f'Mean: {mean_time:.1f}ms')
                ax3.axvline(median_time, color=KARTOZA_COLORS["highlight4"], linestyle='--', 
                           label=f'Median: {median_time:.1f}ms')
                ax3.legend()
            
            plt.tight_layout()
            
            # Clean filename by removing invalid characters
            clean_layer_name = layer_name.replace(':', '_').replace('/', '_')
            chart_path = self.output_dir / f"{clean_layer_name}_performance_analysis.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error creating chart for {layer_name}: {e}[/]")
            return None
    
    def create_detailed_response_time_histogram(self, layer_name: str) -> Optional[str]:
        """Create detailed response time histogram from individual request data (CSV files)"""
        if not MATPLOTLIB_AVAILABLE:
            return None
            
        try:
            import pandas as pd
            
            # Find CSV files for this layer - need to match exact layer name including colons
            csv_pattern = f"{layer_name}_c*.csv"
            csv_files = list(RESULTS_DIR.glob(csv_pattern))
            
            console.print(f"[{KARTOZA_COLORS['highlight3']}]🔍 Looking for CSV files with pattern: {csv_pattern}[/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]📁 Found {len(csv_files)} CSV files for {layer_name}[/]")
            
            if not csv_files:
                return None
            
            all_response_times = []
            concurrency_data = []
            
            for csv_file in csv_files:
                try:
                    console.print(f"[{KARTOZA_COLORS['highlight3']}]📊 Processing: {csv_file.name}[/]")
                    
                    # Extract concurrency level from filename
                    filename = csv_file.stem
                    if '_c' in filename:
                        concurrency = filename.split('_c')[1].split('_')[0]
                    else:
                        concurrency = "unknown"
                    
                    # Read CSV data
                    df = pd.read_csv(csv_file, sep='\t')  # Apache Bench CSV is tab-separated
                    
                    # Check for different possible column names
                    time_column = None
                    if 'ttime' in df.columns:
                        time_column = 'ttime'  # Apache Bench total time
                    elif 'Time in ms' in df.columns:
                        time_column = 'Time in ms'
                    elif 'dtime' in df.columns:
                        time_column = 'dtime'  # Apache Bench processing time
                    
                    if time_column and len(df) > 0:
                        response_times = df[time_column].values
                        all_response_times.extend(response_times)
                        concurrency_data.extend([int(concurrency)] * len(response_times))
                        console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Added {len(response_times)} requests from concurrency {concurrency}[/]")
                        
                except Exception as e:
                    console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Error processing {csv_file}: {e}[/]")
                    continue
            
            if not all_response_times:
                return None
            
            # Create histogram
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Create histogram with reasonable bin count
            n_bins = min(50, max(10, len(all_response_times) // 100))
            counts, bins, patches = ax.hist(all_response_times, bins=n_bins, 
                                          color=KARTOZA_COLORS["highlight1"], 
                                          alpha=0.7, edgecolor='black')
            
            ax.set_xlabel('Response Time (ms)')
            ax.set_ylabel('Number of Requests')
            ax.set_title(f'Individual Request Response Time Distribution: {layer_name}', 
                        color=KARTOZA_COLORS["highlight2"], fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add statistical lines
            mean_time = np.mean(all_response_times)
            median_time = np.median(all_response_times)
            p95_time = np.percentile(all_response_times, 95)
            p99_time = np.percentile(all_response_times, 99)
            
            ax.axvline(mean_time, color=KARTOZA_COLORS["alert"], linestyle='--', 
                      label=f'Mean: {mean_time:.0f}ms')
            ax.axvline(median_time, color=KARTOZA_COLORS["highlight4"], linestyle='--', 
                      label=f'Median: {median_time:.0f}ms')
            ax.axvline(p95_time, color=KARTOZA_COLORS["highlight3"], linestyle=':', 
                      label=f'95th %ile: {p95_time:.0f}ms')
            ax.axvline(p99_time, color=KARTOZA_COLORS["highlight2"], linestyle=':', 
                      label=f'99th %ile: {p99_time:.0f}ms')
            
            ax.legend()
            
            # Add summary text
            summary_text = f'Total Requests: {len(all_response_times):,}\n'
            summary_text += f'Min: {np.min(all_response_times):.0f}ms\n'
            summary_text += f'Max: {np.max(all_response_times):.0f}ms\n'
            summary_text += f'Std Dev: {np.std(all_response_times):.0f}ms'
            
            ax.text(0.02, 0.98, summary_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', 
                   facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            
            # Create unique filename for this layer's histogram
            clean_layer_name = layer_name.replace(':', '_').replace('/', '_')
            chart_path = self.output_dir / f"{clean_layer_name}_response_time_histogram.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Created histogram: {chart_path}[/]")
            return str(chart_path)
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Could not create detailed histogram for {layer_name}: {e}[/]")
            return None
    
    def generate_comprehensive_report(self, timestamp: str = None) -> Optional[Path]:
        """Generate comprehensive PDF report using ReportLab"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Find consolidated results file
        consolidated_files = list(RESULTS_DIR.glob(f"consolidated_*_results_*.json"))
        
        if not consolidated_files:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ No consolidated results found[/]")
            return None
        
        # Use most recent if specific timestamp not found
        latest_file = max(consolidated_files, key=lambda p: p.stat().st_mtime)
        console.print(f"[{KARTOZA_COLORS['highlight2']}]📊 Using results: {latest_file}[/]")
        
        try:
            with open(latest_file) as f:
                data = json.load(f)
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error loading results: {e}[/]")
            return None
        
        # Generate report filename
        report_filename = self.output_dir / f"{self.service_type}_comprehensive_report_{timestamp}.pdf"
        console.print(f"[{KARTOZA_COLORS['highlight1']}]📄 Generating PDF: {report_filename}[/]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating PDF report...", total=100)
            
            try:
                self._build_reportlab_pdf(data, report_filename, progress, task)
                progress.update(task, completed=100, description="PDF generation complete")
                
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ PDF report generated: {report_filename}[/]")
                return report_filename
                
            except Exception as e:
                console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating PDF: {e}[/]")
                return None
    
    def _build_reportlab_pdf(self, data: Dict, filename: Path, progress, task):
        """Build PDF using ReportLab with professional formatting"""
        doc = SimpleDocTemplate(str(filename), pagesize=A4,
                              rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles with Kartoza branding
        title_style = ParagraphStyle('CustomTitle',
                                   parent=styles['Heading1'],
                                   fontSize=24,
                                   textColor=colors.HexColor(KARTOZA_COLORS["highlight2"]),
                                   alignment=TA_CENTER,
                                   spaceAfter=30)
        
        heading_style = ParagraphStyle('CustomHeading',
                                     parent=styles['Heading2'],
                                     fontSize=16,
                                     textColor=colors.HexColor(KARTOZA_COLORS["highlight4"]),
                                     spaceBefore=20,
                                     spaceAfter=10)
        
        subheading_style = ParagraphStyle('CustomSubHeading',
                                        parent=styles['Heading3'],
                                        fontSize=12,
                                        textColor=colors.HexColor(KARTOZA_COLORS["highlight1"]),
                                        spaceBefore=15,
                                        spaceAfter=8)
        
        progress.update(task, advance=10, description="Building report header...")
        
        # Report header
        story.append(Paragraph("GeoServer Comprehensive Benchmark Report", title_style))
        story.append(Paragraph("Dynamic Performance Analysis", styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Test configuration
        test_suite = data.get('test_suite', {})
        story.append(Paragraph("Test Configuration", heading_style))
        
        config_data = [
            ['Parameter', 'Value'],
            ['Service Type', test_suite.get('service_type', 'Unknown')],
            ['Test Date', test_suite.get('date', 'Unknown')],
            ['Total Tests', str(test_suite.get('total_tests', 'Unknown'))],
            ['Targets Tested', str(len(test_suite.get('targets_tested', [])))],
        ]
        
        config_table = Table(config_data, colWidths=[2.5*inch, 4*inch])
        config_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KARTOZA_COLORS["highlight2"])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(config_table)
        story.append(Spacer(1, 20))
        
        # Process results by target
        results_by_target = {}
        for result in data.get('results', []):
            target = result.get('target', result.get('layer', 'unknown'))
            if target not in results_by_target:
                results_by_target[target] = []
            results_by_target[target].append(result)
        
        progress.update(task, advance=20, description="Processing targets...")
        
        # Add layer sections with dynamic metadata
        for i, (target, target_results) in enumerate(results_by_target.items()):
            if target == 'unknown':
                continue
                
            progress.update(task, advance=60/len(results_by_target), 
                          description=f"Processing {target}...")
            
            story.append(PageBreak())
            
            # Get layer metadata from capabilities
            metadata = get_layer_metadata_from_capabilities(self.geoserver_url, target)
            
            story.append(Paragraph(metadata["title"], heading_style))
            story.append(Paragraph("Layer Information", subheading_style))
            story.append(Paragraph(metadata["description"], styles['Normal']))
            story.append(Spacer(1, 10))
            
            # Add map image
            map_image_path = self.capture_map_image(target)
            if map_image_path and os.path.exists(map_image_path):
                story.append(Paragraph("Map Preview", subheading_style))
                img = Image(map_image_path, width=4*inch, height=3*inch)
                story.append(img)
                story.append(Spacer(1, 15))
            
            # Results table
            story.append(Paragraph("Performance Results", subheading_style))
            
            target_results_sorted = sorted(target_results, key=lambda x: x.get('concurrency_level', 0))
            results_data = [['Concurrency', 'RPS', 'Avg Time (ms)', 'Failed', 'Success Rate']]
            
            for result in target_results_sorted:
                results = result.get('results', {})
                
                def safe_format_value(value, is_float=False):
                    if not value or value == 'N/A':
                        return 'N/A'
                    try:
                        str_val = str(value).replace(',', '.').split('\n')[0]
                        if is_float:
                            return f"{float(str_val):.1f}"
                        return str_val
                    except:
                        return 'N/A'
                
                results_data.append([
                    str(result.get('concurrency_level', 'N/A')),
                    safe_format_value(results.get('requests_per_second'), True),
                    safe_format_value(results.get('mean_response_time_ms'), True),
                    safe_format_value(results.get('failed_requests')),
                    safe_format_value(results.get('success_rate'))
                ])
            
            results_table = Table(results_data, colWidths=[1*inch, 1.2*inch, 1.4*inch, 1*inch, 1.4*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KARTOZA_COLORS["highlight4"])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(results_table)
            story.append(Spacer(1, 15))
            
            # Add performance chart
            chart_path = self.create_concurrency_analysis_chart(target_results, target)
            if chart_path and os.path.exists(chart_path):
                story.append(Paragraph("Performance Analysis", subheading_style))
                chart_img = Image(chart_path, width=6*inch, height=7.5*inch)
                story.append(chart_img)
                story.append(Spacer(1, 15))
            
            # Add detailed response time histogram
            histogram_path = self.create_detailed_response_time_histogram(target)
            if histogram_path and os.path.exists(histogram_path):
                story.append(Paragraph("Individual Request Response Time Distribution", subheading_style))
                histogram_img = Image(histogram_path, width=6*inch, height=4*inch)
                story.append(histogram_img)
                story.append(Spacer(1, 15))
        
        progress.update(task, advance=10, description="Building final PDF...")
        doc.build(story)


def generate_pdf_report(service_type: str = "geoserver", use_reportlab: bool = True) -> Optional[Path]:
    """
    Convenience function to generate a PDF report for a specific service type
    
    Args:
        service_type: Type of service (geoserver, nginx, etc.)
        use_reportlab: Whether to use ReportLab (True) or matplotlib (False)
        
    Returns:
        Path to generated PDF or None if failed
    """
    try:
        if use_reportlab and REPORTLAB_AVAILABLE:
            generator = ReportLabPDFGenerator(service_type)
            return generator.generate_comprehensive_report()
        else:
            generator = PDFReportGenerator(service_type)
            return generator.generate_comprehensive_report()
    except ImportError as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Cannot generate PDF: {e}[/]")
        console.print(f"[{KARTOZA_COLORS['highlight3']}]Install missing dependencies[/]")
        return None
    except Exception as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating PDF report: {e}[/]")
        return None


def main():
    """Main entry point when run as standalone script"""
    parser = argparse.ArgumentParser(description='Generate comprehensive benchmark PDF reports')
    parser.add_argument('--service-type', default='geoserver',
                       help='Service type (geoserver, nginx, etc.)')
    parser.add_argument('--results-pattern',
                       help='Pattern to match consolidated results files')
    parser.add_argument('--output', help='Output filename (without path)')
    parser.add_argument('--output-dir', type=Path, help='Output directory')
    
    args = parser.parse_args()
    
    try:
        generator = PDFReportGenerator(args.service_type, args.output_dir)
        result_path = generator.generate_comprehensive_report(
            results_pattern=args.results_pattern,
            output_filename=args.output
        )
        
        if result_path:
            console.print(f"[{KARTOZA_COLORS['highlight4']}]🎉 Report generation completed![/]")
            console.print(f"[{KARTOZA_COLORS['highlight3']}]📄 Output: {result_path}[/]")
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Report generation failed[/]")
            return 1
            
    except Exception as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error generating report: {e}[/]")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())