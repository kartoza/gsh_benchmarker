#!/usr/bin/env python3
"""
GeoServer Benchmark PDF Report Generator
Creates beautiful PDF reports from Apache Bench benchmark results
"""

import os
import sys
import json
import pandas as pd
import requests
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import numpy as np

# Import Kartoza themed console
from kartoza_rich_theme import console, print_info, print_warning, print_error, print_success, print_header

# Kartoza brand colors for PDF
KARTOZA_COLORS = {
    "highlight1": "#DF9E2F",  # yellow/orange
    "highlight2": "#569FC6",  # blue
    "highlight3": "#8A8B8B",  # grey
    "highlight4": "#06969A",  # teal
    "alert": "#CC0403",       # red
    "white": "#FFFFFF",
    "black": "#000000"
}

# Layer metadata
LAYER_METADATA = {
    "AfstandTotKoelte": {
        "title": "Distance to Cooling Areas",
        "description": "This layer shows the distance to nearest cooling areas (water bodies, parks, forests) in the Netherlands. Useful for heat stress adaptation planning and urban cooling strategies.",
        "data_source": "Climate Adaptation Services",
        "resolution": "High resolution raster data",
        "update_frequency": "Annual"
    },
    "bkb_2024": {
        "title": "Building Coverage Database 2024",
        "description": "Building footprint coverage data for the Netherlands showing building density and urban structure. Essential for urban heat island effect analysis and climate adaptation planning.",
        "data_source": "Dutch Cadastre (BRK)",
        "resolution": "Vector building polygons",
        "update_frequency": "Quarterly"
    },
    "pok_normplusklimaatverandering2100_50cm": {
        "title": "Climate Change Impact 2100 (+50cm sea level)",
        "description": "Projected climate change impacts for the year 2100 including 50cm sea level rise scenario. Shows areas at risk from flooding and climate change effects.",
        "data_source": "KNMI Climate Scenarios",
        "resolution": "High resolution climate model output",
        "update_frequency": "Per scenario update"
    },
    "zonalstatistics_pet2022actueel_2024124": {
        "title": "Potential Evapotranspiration Statistics 2022",
        "description": "Zonal statistics for potential evapotranspiration (PET) measurements across different administrative zones. Important for drought monitoring and water resource management.",
        "data_source": "Meteorological observations",
        "resolution": "Administrative zone aggregations",
        "update_frequency": "Monthly"
    }
}

class BenchmarkReportGenerator:
    def __init__(self, results_dir="results", output_dir="reports"):
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.geoserver_base = "https://climate-adaptation-services.geospatialhosting.com/geoserver"
        self.wms_base = f"{self.geoserver_base}/wms"
        
        # Set up matplotlib style for Kartoza colors
        plt.style.use('seaborn-v0_8')
        sns.set_palette([KARTOZA_COLORS["highlight2"], KARTOZA_COLORS["highlight1"], 
                        KARTOZA_COLORS["highlight4"], KARTOZA_COLORS["alert"]])
        
        # Concurrency levels for incremental testing
        self.concurrency_levels = [1, 10, 100, 500, 1000, 2000, 3000, 4000, 5000]
    
    def parse_apache_bench_log(self, log_file):
        """Parse Apache Bench log file to extract key metrics"""
        metrics = {}
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            for line in lines:
                if 'Server Hostname:' in line:
                    metrics['hostname'] = line.split(':', 1)[1].strip()
                elif 'Server Port:' in line:
                    metrics['port'] = line.split(':', 1)[1].strip()
                elif 'Document Path:' in line:
                    metrics['path'] = line.split(':', 1)[1].strip()
                elif 'Concurrency Level:' in line:
                    metrics['concurrency'] = int(line.split(':', 1)[1].strip())
                elif 'Time taken for tests:' in line:
                    metrics['total_time'] = float(line.split(':', 1)[1].split()[0])
                elif 'Complete requests:' in line:
                    metrics['total_requests'] = int(line.split(':', 1)[1].strip())
                elif 'Failed requests:' in line:
                    metrics['failed_requests'] = int(line.split(':', 1)[1].strip())
                elif 'Requests per second:' in line:
                    metrics['rps'] = float(line.split(':', 1)[1].split()[0])
                elif 'Time per request:' in line and '(mean)' in line:
                    metrics['mean_response_time'] = float(line.split(':', 1)[1].split()[0])
                elif 'Transfer rate:' in line:
                    metrics['transfer_rate'] = float(line.split(':', 1)[1].split()[0])
        
        except Exception as e:
            print_error(f"Error parsing log file {log_file}: {e}")
            return {}
        
        return metrics
    
    def load_consolidated_results(self, timestamp):
        """Load consolidated JSON results file"""
        # Try different naming patterns for consolidated results
        patterns = [
            f"consolidated_results_{timestamp}.json",
            f"consolidated_results_test_{timestamp}.json"
        ]
        
        consolidated_file = None
        for pattern in patterns:
            candidate_file = self.results_dir / pattern
            if candidate_file.exists():
                consolidated_file = candidate_file
                break
        
        if not consolidated_file:
            # Try to find any consolidated results file if timestamp doesn't match exactly
            consolidated_files = list(self.results_dir.glob("consolidated_results_*.json"))
            if consolidated_files:
                # Use the most recent one
                consolidated_file = max(consolidated_files, key=lambda p: p.stat().st_mtime)
                print_warning(f"Using most recent consolidated results file: {consolidated_file}")
            else:
                print_warning(f"No consolidated results file found for timestamp {timestamp}")
                return None
        
        try:
            with open(consolidated_file, 'r') as f:
                data = json.load(f)
            print_success(f"Loaded consolidated results: {consolidated_file}")
            return data
        except Exception as e:
            print_error(f"Error loading consolidated results: {e}")
            return None
    
    def create_concurrency_analysis_chart(self, layer_results, layer_name):
        """Create concurrency analysis chart showing performance vs concurrency level"""
        try:
            # Extract data for plotting
            concurrencies = []
            rps_values = []
            response_times = []
            
            for result in layer_results:
                if result.get('results'):
                    def safe_float_convert(value, default=0):
                        try:
                            # Convert European format (0,00) to US format (0.00)
                            str_val = str(value).replace(',', '.')
                            return float(str_val)
                        except (ValueError, TypeError):
                            return default
                    
                    concurrencies.append(result['concurrency_level'])
                    rps_values.append(safe_float_convert(result['results'].get('requests_per_second', 0)))
                    response_times.append(safe_float_convert(result['results'].get('mean_response_time_ms', 0)))
            
            if not concurrencies:
                return None
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            fig.suptitle(f'Concurrency Analysis: {layer_name}', 
                        fontsize=16, color=KARTOZA_COLORS["highlight2"], fontweight='bold')
            
            # Requests per second vs concurrency
            ax1.plot(concurrencies, rps_values, 'o-', 
                    color=KARTOZA_COLORS["highlight1"], linewidth=3, markersize=8)
            ax1.set_xlabel('Concurrent Connections')
            ax1.set_ylabel('Requests per Second')
            ax1.set_title('Throughput vs Concurrency Level', color=KARTOZA_COLORS["highlight4"])
            ax1.grid(True, alpha=0.3)
            ax1.set_xscale('log')
            
            # Response time vs concurrency
            ax2.plot(concurrencies, response_times, 's-', 
                    color=KARTOZA_COLORS["highlight4"], linewidth=3, markersize=8)
            ax2.set_xlabel('Concurrent Connections')
            ax2.set_ylabel('Mean Response Time (ms)')
            ax2.set_title('Response Time vs Concurrency Level', color=KARTOZA_COLORS["highlight4"])
            ax2.grid(True, alpha=0.3)
            ax2.set_xscale('log')
            
            plt.tight_layout()
            
            chart_path = self.output_dir / f"{layer_name}_concurrency_analysis.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            print_error(f"Error creating concurrency analysis chart for {layer_name}: {e}")
            return None
    
    def capture_map_image(self, layer_name, width=800, height=600):
        """Capture a map image from WMS for the report"""
        # Netherlands bounding box
        bbox = "3.0501,50.7286,7.3450,53.7185"  # minx,miny,maxx,maxy
        
        wms_params = {
            'SERVICE': 'WMS',
            'VERSION': '1.1.1',
            'REQUEST': 'GetMap',
            'LAYERS': f'CAS:{layer_name}',
            'STYLES': '',
            'BBOX': bbox,
            'WIDTH': str(width),
            'HEIGHT': str(height),
            'FORMAT': 'image/png',
            'SRS': 'EPSG:4326'
        }
        
        try:
            print_info(f"Capturing map image for {layer_name}...")
            response = requests.get(self.wms_base, params=wms_params, timeout=60)
            
            if response.status_code == 200:
                image_path = self.output_dir / f"{layer_name}_map.png"
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                print_success(f"Map image saved: {image_path}")
                return str(image_path)
            else:
                print_warning(f"Failed to capture map image for {layer_name}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print_warning(f"Timeout capturing map image for {layer_name} - skipping map preview")
            return None
        except Exception as e:
            print_error(f"Error capturing map image for {layer_name}: {e}")
            return None
    
    def create_performance_chart(self, csv_file, layer_name):
        """Create performance visualization chart"""
        try:
            df = pd.read_csv(csv_file)
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            fig.suptitle(f'Performance Metrics: {layer_name}', 
                        fontsize=14, color=KARTOZA_COLORS["highlight2"], fontweight='bold')
            
            # Response time over percentage of requests
            ax1.plot(df['Percentage served'], df['Time in ms'], 
                    color=KARTOZA_COLORS["highlight1"], linewidth=2)
            ax1.set_xlabel('Percentage of Requests Served (%)')
            ax1.set_ylabel('Response Time (ms)')
            ax1.set_title('Response Time Distribution')
            ax1.grid(True, alpha=0.3)
            
            # Response time histogram
            ax2.hist(df['Time in ms'], bins=50, color=KARTOZA_COLORS["highlight4"], alpha=0.7)
            ax2.set_xlabel('Response Time (ms)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Response Time Histogram')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            chart_path = self.output_dir / f"{layer_name}_performance_chart.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            print_error(f"Error creating performance chart for {layer_name}: {e}")
            return None
    
    def generate_pdf_report(self, timestamp=None):
        """Generate comprehensive PDF report with incremental concurrency analysis"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_filename = self.output_dir / f"geoserver_comprehensive_benchmark_report_{timestamp}.pdf"
        
        print_header(f"Generating PDF Report: {report_filename}")
        
        # Load consolidated results
        consolidated_data = self.load_consolidated_results(timestamp)
        if not consolidated_data:
            print_error("No consolidated results found - cannot generate report")
            return None
        
        # Create PDF document
        doc = SimpleDocTemplate(str(report_filename), pagesize=A4,
                              rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
        
        # Build story for PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles with Kartoza colors
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
        
        # Report title and header
        story.append(Paragraph("GeoServer Comprehensive Benchmark Report", title_style))
        story.append(Paragraph(f"Climate Adaptation Services", styles['Normal']))
        story.append(Paragraph(f"Incremental Concurrency Analysis", styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Test Configuration Summary
        test_suite = consolidated_data.get('test_suite', {})
        story.append(Paragraph("Test Configuration", heading_style))
        
        config_data = [
            ['Parameter', 'Value'],
            ['Test Suite', test_suite.get('name', 'N/A')],
            ['Test Date', test_suite.get('date', 'N/A')],
            ['Total Requests per Test', f"{test_suite.get('total_requests_per_test', 'N/A'):,}"],
            ['Concurrency Levels', ', '.join(map(str, test_suite.get('concurrency_levels', [])))],
            ['Layers Tested', ', '.join(test_suite.get('layers_tested', []))],
            ['Server', test_suite.get('server', 'N/A')],
        ]
        
        config_table = Table(config_data, colWidths=[2.5*inch, 4*inch])
        config_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KARTOZA_COLORS["highlight2"])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(config_table)
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        summary_text = f"""
        This report presents comprehensive benchmark results for the Climate Adaptation Services GeoServer instance
        using incremental concurrency testing methodology. Performance testing was conducted using Apache Bench (ab) 
        with {test_suite.get('total_requests_per_test', 5000):,} requests across {len(test_suite.get('concurrency_levels', []))} 
        different concurrency levels ranging from 1 to {max(test_suite.get('concurrency_levels', [0]))} concurrent connections.
        
        The testing focused on WMTS tile performance for {len(test_suite.get('layers_tested', []))} climate adaptation 
        datasets covering the Netherlands. Each test measures how the server performs under increasing load conditions,
        providing insights into scalability characteristics and optimal concurrency configurations.
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Group results by layer
        results_by_layer = {}
        for result in consolidated_data.get('results', []):
            layer_name = result.get('layer', 'unknown')
            if layer_name not in results_by_layer:
                results_by_layer[layer_name] = []
            results_by_layer[layer_name].append(result)
        
        # Process each layer's results
        for layer_name, layer_results in results_by_layer.items():
            if layer_name not in LAYER_METADATA:
                continue
                
            print_info(f"Processing results for {layer_name}")
            
            # Layer section header
            story.append(PageBreak())
            metadata = LAYER_METADATA[layer_name]
            story.append(Paragraph(metadata["title"], heading_style))
            
            # Layer description and metadata
            story.append(Paragraph("Layer Information", subheading_style))
            story.append(Paragraph(metadata["description"], styles['Normal']))
            story.append(Spacer(1, 10))
            
            # Layer metadata table
            layer_meta_data = [
                ['Attribute', 'Value'],
                ['Data Source', metadata.get('data_source', 'N/A')],
                ['Resolution', metadata.get('resolution', 'N/A')],
                ['Update Frequency', metadata.get('update_frequency', 'N/A')],
                ['Layer Name', f"CAS:{layer_name}"],
            ]
            
            layer_meta_table = Table(layer_meta_data, colWidths=[2*inch, 4*inch])
            layer_meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KARTOZA_COLORS["highlight1"])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(layer_meta_table)
            story.append(Spacer(1, 15))
            
            # Capture and include map image
            map_image_path = self.capture_map_image(layer_name)
            if map_image_path and os.path.exists(map_image_path):
                story.append(Paragraph("Map Preview", subheading_style))
                img = Image(map_image_path, width=4*inch, height=3*inch)
                story.append(img)
                story.append(Spacer(1, 15))
            
            # Incremental test results table
            story.append(Paragraph("Incremental Concurrency Test Results", subheading_style))
            
            # Sort results by concurrency level
            layer_results_sorted = sorted(layer_results, key=lambda x: x.get('concurrency_level', 0))
            
            results_data = [['Concurrency', 'RPS', 'Mean Time (ms)', 'Failed', 'Transfer Rate (KB/s)']]
            
            for result in layer_results_sorted:
                concurrency = result.get('concurrency_level', 'N/A')
                results = result.get('results', {})
                rps = results.get('requests_per_second', 'N/A')
                mean_time = results.get('mean_response_time_ms', 'N/A')
                failed = results.get('failed_requests', 'N/A')
                transfer_rate = results.get('transfer_rate_kbps', 'N/A')
                
                # Format the values - handle European number format (comma as decimal separator)
                def safe_float_convert(value):
                    if value == 'N/A' or value == '':
                        return 'N/A'
                    try:
                        # Convert European format (0,00) to US format (0.00)
                        str_val = str(value).replace(',', '.')
                        return float(str_val)
                    except (ValueError, TypeError):
                        return 'N/A'
                
                rps_float = safe_float_convert(rps)
                time_float = safe_float_convert(mean_time)
                transfer_float = safe_float_convert(transfer_rate)
                
                rps_str = f"{rps_float:.1f}" if rps_float != 'N/A' else 'N/A'
                time_str = f"{time_float:.1f}" if time_float != 'N/A' else 'N/A'
                failed_str = str(failed) if failed != 'N/A' and failed != '' else 'N/A'
                transfer_str = f"{transfer_float:.1f}" if transfer_float != 'N/A' else 'N/A'
                
                results_data.append([str(concurrency), rps_str, time_str, failed_str, transfer_str])
            
            results_table = Table(results_data, colWidths=[1*inch, 1.2*inch, 1.4*inch, 1*inch, 1.4*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KARTOZA_COLORS["highlight4"])),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(results_table)
            story.append(Spacer(1, 15))
            
            # Concurrency analysis chart
            chart_path = self.create_concurrency_analysis_chart(layer_results, layer_name)
            if chart_path and os.path.exists(chart_path):
                story.append(Paragraph("Performance vs Concurrency Analysis", subheading_style))
                chart_img = Image(chart_path, width=7*inch, height=5*inch)
                story.append(chart_img)
                story.append(Spacer(1, 15))
        
        # Build PDF
        try:
            doc.build(story)
            print_success(f"PDF report generated: {report_filename}")
            return str(report_filename)
        except Exception as e:
            print_error(f"Error generating PDF: {e}")
            return None

def main():
    if len(sys.argv) > 1:
        timestamp = sys.argv[1]
    else:
        # Find all consolidated results files
        results_dir = Path("results")
        if results_dir.exists():
            consolidated_files = list(results_dir.glob("consolidated_results_*.json"))
            if consolidated_files:
                # Sort by modification time (newest first)
                consolidated_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                
                print_header("Available consolidated results:")
                for i, file in enumerate(consolidated_files):
                    mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    print_info(f"{i+1}. {file.name} (modified: {mtime})")
                
                # Ask user to choose
                print_info(f"\nDefault: {consolidated_files[0].name} (latest)")
                try:
                    choice = input("Enter number to select file (or press Enter for default): ").strip()
                except (EOFError, KeyboardInterrupt):
                    # Non-interactive mode, use default
                    choice = ""
                
                if choice == "":
                    selected_file = consolidated_files[0]
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(consolidated_files):
                            selected_file = consolidated_files[idx]
                        else:
                            print_error("Invalid selection, using latest file")
                            selected_file = consolidated_files[0]
                    except ValueError:
                        print_error("Invalid input, using latest file")
                        selected_file = consolidated_files[0]
                
                print_success(f"Selected: {selected_file.name}")
                timestamp = selected_file.name.replace("consolidated_results_", "").replace(".json", "")
            else:
                print_error("No consolidated results files found")
                timestamp = None
        else:
            print_error("Results directory not found")
            timestamp = None
    
    generator = BenchmarkReportGenerator()
    report_path = generator.generate_pdf_report(timestamp)
    
    if report_path:
        print_success(f"\n🎉 Benchmark report generated successfully!")
        print_info(f"📄 Report location: {report_path}")
        print_info(f"📊 Open with: xdg-open '{report_path}'")
    else:
        print_error("❌ Failed to generate benchmark report")
        sys.exit(1)

if __name__ == "__main__":
    main()