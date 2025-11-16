#!/usr/bin/env python3
"""
System Monitoring Integration for GSH Benchmarker Suite

Provides integration with Grafana/Prometheus and other monitoring systems
to capture system metrics during benchmark tests.
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import time
from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .colors import KARTOZA_COLORS
from .config import REPORTS_DIR

console = Console()

@dataclass
class MetricDataPoint:
    """A single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}

@dataclass 
class SystemMetrics:
    """Container for system metrics during a test period"""
    start_time: datetime
    end_time: datetime
    cpu_usage: List[MetricDataPoint] = None
    memory_usage: List[MetricDataPoint] = None
    disk_io: List[MetricDataPoint] = None
    network_activity: List[MetricDataPoint] = None
    
    def __post_init__(self):
        if self.cpu_usage is None:
            self.cpu_usage = []
        if self.memory_usage is None:
            self.memory_usage = []
        if self.disk_io is None:
            self.disk_io = []
        if self.network_activity is None:
            self.network_activity = []


class PrometheusClient:
    """Client for querying Prometheus metrics"""
    
    def __init__(self, prometheus_url: str, timeout: int = 30):
        """Initialize Prometheus client"""
        self.prometheus_url = prometheus_url.rstrip('/')
        self.timeout = timeout
        self.query_endpoint = f"{self.prometheus_url}/api/v1/query"
        self.range_query_endpoint = f"{self.prometheus_url}/api/v1/query_range"
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to Prometheus"""
        try:
            response = requests.get(f"{self.prometheus_url}/api/v1/status/config", 
                                  timeout=self.timeout)
            if response.status_code == 200:
                return True, "Connected successfully"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            return False, f"Connection failed: {e}"
    
    def query_metric(self, query: str, time_point: datetime = None) -> Optional[Dict]:
        """Query a metric at a specific time point"""
        params = {
            'query': query
        }
        
        if time_point:
            params['time'] = time_point.timestamp()
        
        try:
            response = requests.get(self.query_endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Prometheus query failed: {e}[/]")
            return None
    
    def query_range(self, query: str, start_time: datetime, end_time: datetime, 
                   step: str = "30s") -> Optional[Dict]:
        """Query a metric over a time range"""
        params = {
            'query': query,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(), 
            'step': step
        }
        
        try:
            response = requests.get(self.range_query_endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Prometheus range query failed: {e}[/]")
            return None


class GrafanaClient:
    """Client for querying Grafana dashboards and annotations"""
    
    def __init__(self, grafana_url: str, api_key: str = None, timeout: int = 30):
        """Initialize Grafana client"""
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {}
        
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to Grafana"""
        try:
            response = requests.get(f"{self.grafana_url}/api/health", 
                                  headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return True, "Connected successfully"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            return False, f"Connection failed: {e}"
    
    def create_annotation(self, text: str, tags: List[str] = None, 
                         start_time: datetime = None, end_time: datetime = None) -> bool:
        """Create an annotation in Grafana"""
        if not self.api_key:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  No API key provided for Grafana annotations[/]")
            return False
        
        if start_time is None:
            start_time = datetime.now()
        
        annotation_data = {
            'text': text,
            'tags': tags or ['benchmark'],
            'time': int(start_time.timestamp() * 1000)  # Grafana expects milliseconds
        }
        
        if end_time:
            annotation_data['timeEnd'] = int(end_time.timestamp() * 1000)
        
        try:
            response = requests.post(
                f"{self.grafana_url}/api/annotations",
                headers={**self.headers, 'Content-Type': 'application/json'},
                data=json.dumps(annotation_data),
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  Failed to create Grafana annotation: {e}[/]")
            return False


class SystemMonitoringClient:
    """Integrated client for capturing system metrics during benchmarks"""
    
    # Common Prometheus queries for system metrics
    SYSTEM_QUERIES = {
        'cpu_usage': 'cpu_usage_active',
        'cpu_usage_by_core': 'cpu_usage_active{cpu!="cpu-total"}',
        'memory_usage_percent': 'mem_used_percent',
        'memory_usage_bytes': 'mem_used',
        'disk_io_read': 'rate(diskio_reads[5m])',
        'disk_io_write': 'rate(diskio_writes[5m])', 
        'network_bytes_recv': 'rate(net_bytes_recv[5m])',
        'network_bytes_sent': 'rate(net_bytes_sent[5m])',
        'load_average': 'system_load1'
    }
    
    def __init__(self, prometheus_url: str = None, grafana_url: str = None, 
                 grafana_api_key: str = None):
        """Initialize monitoring client with optional Prometheus and Grafana endpoints"""
        self.prometheus = None
        self.grafana = None
        
        if prometheus_url:
            self.prometheus = PrometheusClient(prometheus_url)
        
        if grafana_url:
            self.grafana = GrafanaClient(grafana_url, grafana_api_key)
    
    def test_connections(self) -> Dict[str, Tuple[bool, str]]:
        """Test connections to all configured monitoring systems"""
        results = {}
        
        if self.prometheus:
            results['prometheus'] = self.prometheus.test_connection()
        
        if self.grafana:
            results['grafana'] = self.grafana.test_connection()
        
        return results
    
    def start_monitoring_session(self, session_name: str) -> bool:
        """Start a monitoring session with annotations"""
        success = True
        
        if self.grafana:
            annotation_text = f"Benchmark session started: {session_name}"
            if not self.grafana.create_annotation(annotation_text, ['benchmark', 'start']):
                success = False
        
        return success
    
    def end_monitoring_session(self, session_name: str, start_time: datetime) -> bool:
        """End a monitoring session with annotations"""
        success = True
        end_time = datetime.now()
        
        if self.grafana:
            duration = end_time - start_time
            annotation_text = f"Benchmark session completed: {session_name} (Duration: {duration})"
            if not self.grafana.create_annotation(annotation_text, ['benchmark', 'end'], 
                                                start_time, end_time):
                success = False
        
        return success
    
    def capture_metrics(self, start_time: datetime, end_time: datetime, 
                       step: str = "30s") -> Optional[SystemMetrics]:
        """Capture system metrics for the specified time period"""
        
        if not self.prometheus:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  No Prometheus connection available[/]")
            return None
        
        console.print(f"[{KARTOZA_COLORS['highlight3']}]📊 Capturing system metrics from {start_time} to {end_time}[/]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Querying metrics...", total=len(self.SYSTEM_QUERIES))
            
            metrics = SystemMetrics(start_time=start_time, end_time=end_time)
            
            for metric_name, query in self.SYSTEM_QUERIES.items():
                progress.update(task, advance=1, description=f"Querying {metric_name}...")
                
                data = self.prometheus.query_range(query, start_time, end_time, step)
                if data and data.get('status') == 'success':
                    # Parse the metric data
                    parsed_data = self._parse_prometheus_data(data['data']['result'])
                    
                    # Store in appropriate metric category
                    if 'cpu' in metric_name:
                        metrics.cpu_usage.extend(parsed_data)
                    elif 'memory' in metric_name:
                        metrics.memory_usage.extend(parsed_data)
                    elif 'disk' in metric_name:
                        metrics.disk_io.extend(parsed_data)
                    elif 'network' in metric_name:
                        metrics.network_activity.extend(parsed_data)
        
        return metrics
    
    def _parse_prometheus_data(self, result_data: List[Dict]) -> List[MetricDataPoint]:
        """Parse Prometheus query result data into MetricDataPoint objects"""
        data_points = []
        
        for series in result_data:
            metric_labels = series.get('metric', {})
            values = series.get('values', [])
            
            for timestamp, value in values:
                try:
                    dt = datetime.fromtimestamp(float(timestamp))
                    val = float(value)
                    data_points.append(MetricDataPoint(
                        timestamp=dt,
                        value=val,
                        labels=metric_labels
                    ))
                except (ValueError, TypeError):
                    continue
        
        return data_points
    
    def export_metrics_to_csv(self, metrics: SystemMetrics, output_path: Path) -> bool:
        """Export captured metrics to CSV for analysis"""
        try:
            import pandas as pd
            
            # Combine all metrics into a single DataFrame
            all_data = []
            
            for metric_type, data_points in [
                ('cpu', metrics.cpu_usage),
                ('memory', metrics.memory_usage),
                ('disk_io', metrics.disk_io),
                ('network', metrics.network_activity)
            ]:
                for point in data_points:
                    row = {
                        'timestamp': point.timestamp,
                        'metric_type': metric_type,
                        'value': point.value,
                        **point.labels
                    }
                    all_data.append(row)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df.to_csv(output_path, index=False)
                console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Metrics exported to {output_path}[/]")
                return True
            else:
                console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  No metrics data to export[/]")
                return False
                
        except ImportError:
            console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  pandas not available for CSV export[/]")
            return False
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Failed to export metrics: {e}[/]")
            return False


def create_monitoring_charts(metrics: SystemMetrics, output_dir: Path) -> List[Path]:
    """Create monitoring charts from captured metrics"""
    chart_paths = []
    
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        
        # CPU Usage Chart
        if metrics.cpu_usage:
            cpu_data = [(point.timestamp, point.value) for point in metrics.cpu_usage]
            if cpu_data:
                timestamps, values = zip(*cpu_data)
                
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, values, linewidth=2, color=KARTOZA_COLORS["highlight1"])
                plt.title('CPU Usage During Benchmark', fontsize=14, color=KARTOZA_COLORS["highlight2"])
                plt.xlabel('Time')
                plt.ylabel('CPU Usage (%)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                cpu_chart_path = output_dir / 'cpu_usage_chart.png'
                plt.savefig(cpu_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                chart_paths.append(cpu_chart_path)
        
        # Memory Usage Chart 
        if metrics.memory_usage:
            memory_data = [(point.timestamp, point.value) for point in metrics.memory_usage]
            if memory_data:
                timestamps, values = zip(*memory_data)
                
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, values, linewidth=2, color=KARTOZA_COLORS["highlight4"])
                plt.title('Memory Usage During Benchmark', fontsize=14, color=KARTOZA_COLORS["highlight2"])
                plt.xlabel('Time')
                plt.ylabel('Memory Usage (%)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                memory_chart_path = output_dir / 'memory_usage_chart.png'
                plt.savefig(memory_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                chart_paths.append(memory_chart_path)
        
        # Network Activity Chart
        if metrics.network_activity:
            network_data = [(point.timestamp, point.value) for point in metrics.network_activity]
            if network_data:
                timestamps, values = zip(*network_data)
                
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, values, linewidth=2, color=KARTOZA_COLORS["highlight3"])
                plt.title('Network Activity During Benchmark', fontsize=14, color=KARTOZA_COLORS["highlight2"])
                plt.xlabel('Time')
                plt.ylabel('Network I/O (bytes/sec)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                network_chart_path = output_dir / 'network_activity_chart.png'
                plt.savefig(network_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                chart_paths.append(network_chart_path)
        
        if chart_paths:
            console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Created {len(chart_paths)} monitoring charts[/]")
        
    except ImportError:
        console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  matplotlib/pandas not available for chart creation[/]")
    except Exception as e:
        console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error creating monitoring charts: {e}[/]")
    
    return chart_paths


def detect_monitoring_endpoints() -> Dict[str, Optional[str]]:
    """Attempt to auto-detect common monitoring endpoints"""
    endpoints = {
        'prometheus': None,
        'grafana': None
    }
    
    # Common ports and paths to check
    common_prometheus_ports = [9090, 9091]
    common_grafana_ports = [3000, 3001]
    common_hosts = ['localhost', '127.0.0.1', 'monitoring', 'prometheus', 'grafana']
    
    console.print(f"[{KARTOZA_COLORS['highlight3']}]🔍 Auto-detecting monitoring endpoints...[/]")
    
    # Check for Prometheus
    for host in common_hosts:
        for port in common_prometheus_ports:
            prometheus_url = f"http://{host}:{port}"
            try:
                response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
                if response.status_code == 200:
                    endpoints['prometheus'] = prometheus_url
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Found Prometheus at {prometheus_url}[/]")
                    break
            except:
                continue
        if endpoints['prometheus']:
            break
    
    # Check for Grafana
    for host in common_hosts:
        for port in common_grafana_ports:
            grafana_url = f"http://{host}:{port}"
            try:
                response = requests.get(f"{grafana_url}/api/health", timeout=5)
                if response.status_code == 200:
                    endpoints['grafana'] = grafana_url
                    console.print(f"[{KARTOZA_COLORS['highlight4']}]✅ Found Grafana at {grafana_url}[/]")
                    break
            except:
                continue
        if endpoints['grafana']:
            break
    
    if not any(endpoints.values()):
        console.print(f"[{KARTOZA_COLORS['alert']}]⚠️  No monitoring endpoints detected[/]")
    
    return endpoints