#!/usr/bin/env python3
"""
Monitoring Configuration Management for GSH Benchmarker Suite

Provides CRUD operations for monitoring endpoint configurations
with persistent storage in JSON format.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from rich.console import Console
from .colors import KARTOZA_COLORS

console = Console()

@dataclass
class MonitoringEndpoint:
    """Configuration for a monitoring endpoint"""
    name: str
    endpoint_type: str  # 'prometheus' or 'grafana'
    url: str
    api_key: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class MonitoringConfigManager:
    """Manager for monitoring endpoint configurations"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize config manager with optional custom config file path"""
        if config_file is None:
            # Store config in project root
            self.config_file = Path.cwd() / "monitoring_config.json"
        else:
            self.config_file = Path(config_file)
        
        self.endpoints: Dict[str, MonitoringEndpoint] = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                self.endpoints = {}
                for name, endpoint_data in data.get('endpoints', {}).items():
                    self.endpoints[name] = MonitoringEndpoint(**endpoint_data)
                
                return True
            else:
                # Create default configuration with examples
                self._create_default_config()
                return True
                
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error loading monitoring config: {e}[/]")
            self.endpoints = {}
            return False
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert endpoints to dict format
            config_data = {
                'endpoints': {name: asdict(endpoint) for name, endpoint in self.endpoints.items()},
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            return True
            
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]❌ Error saving monitoring config: {e}[/]")
            return False
    
    def _create_default_config(self):
        """Create default configuration with example endpoints"""
        self.endpoints = {
            'local_prometheus': MonitoringEndpoint(
                name='local_prometheus',
                endpoint_type='prometheus',
                url='http://localhost:9090',
                description='Local Prometheus instance',
                enabled=False
            ),
            'local_grafana': MonitoringEndpoint(
                name='local_grafana', 
                endpoint_type='grafana',
                url='http://localhost:3000',
                description='Local Grafana instance',
                enabled=False
            )
        }
        self.save_config()
    
    def create_endpoint(self, name: str, endpoint_type: str, url: str, 
                       api_key: Optional[str] = None, description: Optional[str] = None,
                       enabled: bool = True) -> bool:
        """Create a new monitoring endpoint"""
        if name in self.endpoints:
            return False  # Endpoint already exists
        
        # Validate endpoint type
        if endpoint_type not in ['prometheus', 'grafana']:
            return False
        
        # Ensure URL format
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        
        self.endpoints[name] = MonitoringEndpoint(
            name=name,
            endpoint_type=endpoint_type,
            url=url,
            api_key=api_key,
            description=description,
            enabled=enabled
        )
        
        return self.save_config()
    
    def read_endpoint(self, name: str) -> Optional[MonitoringEndpoint]:
        """Read a specific endpoint configuration"""
        return self.endpoints.get(name)
    
    def read_all_endpoints(self) -> Dict[str, MonitoringEndpoint]:
        """Read all endpoint configurations"""
        return self.endpoints.copy()
    
    def read_enabled_endpoints(self) -> Dict[str, MonitoringEndpoint]:
        """Read only enabled endpoint configurations"""
        return {name: endpoint for name, endpoint in self.endpoints.items() 
                if endpoint.enabled}
    
    def read_by_type(self, endpoint_type: str) -> Dict[str, MonitoringEndpoint]:
        """Read endpoints by type (prometheus or grafana)"""
        return {name: endpoint for name, endpoint in self.endpoints.items() 
                if endpoint.endpoint_type == endpoint_type}
    
    def update_endpoint(self, name: str, **kwargs) -> bool:
        """Update an existing endpoint configuration"""
        if name not in self.endpoints:
            return False
        
        endpoint = self.endpoints[name]
        
        # Update allowed fields
        for field, value in kwargs.items():
            if hasattr(endpoint, field):
                if field == 'url' and value and not value.startswith(('http://', 'https://')):
                    value = f'http://{value}'
                setattr(endpoint, field, value)
        
        # Update timestamp
        endpoint.updated_at = datetime.now().isoformat()
        
        return self.save_config()
    
    def delete_endpoint(self, name: str) -> bool:
        """Delete an endpoint configuration"""
        if name in self.endpoints:
            del self.endpoints[name]
            return self.save_config()
        return False
    
    def toggle_endpoint(self, name: str) -> bool:
        """Toggle enabled/disabled status of an endpoint"""
        if name in self.endpoints:
            self.endpoints[name].enabled = not self.endpoints[name].enabled
            self.endpoints[name].updated_at = datetime.now().isoformat()
            return self.save_config()
        return False
    
    def test_endpoint_connection(self, name: str) -> Tuple[bool, str]:
        """Test connection to a specific endpoint"""
        endpoint = self.read_endpoint(name)
        if not endpoint:
            return False, "Endpoint not found"
        
        try:
            from .monitoring import PrometheusClient, GrafanaClient
            
            if endpoint.endpoint_type == 'prometheus':
                client = PrometheusClient(endpoint.url)
                return client.test_connection()
            elif endpoint.endpoint_type == 'grafana':
                client = GrafanaClient(endpoint.url, endpoint.api_key)
                return client.test_connection()
            else:
                return False, "Unknown endpoint type"
                
        except ImportError:
            return False, "Monitoring modules not available"
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def get_active_prometheus_url(self) -> Optional[str]:
        """Get the URL of the first enabled Prometheus endpoint"""
        for endpoint in self.endpoints.values():
            if endpoint.endpoint_type == 'prometheus' and endpoint.enabled:
                return endpoint.url
        return None
    
    def get_active_grafana_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the URL and API key of the first enabled Grafana endpoint"""
        for endpoint in self.endpoints.values():
            if endpoint.endpoint_type == 'grafana' and endpoint.enabled:
                return endpoint.url, endpoint.api_key
        return None, None
    
    def export_to_env_vars(self) -> Dict[str, str]:
        """Export active endpoints as environment variable format"""
        env_vars = {}
        
        prometheus_url = self.get_active_prometheus_url()
        if prometheus_url:
            env_vars['PROMETHEUS_URL'] = prometheus_url
        
        grafana_url, grafana_key = self.get_active_grafana_config()
        if grafana_url:
            env_vars['GRAFANA_URL'] = grafana_url
            if grafana_key:
                env_vars['GRAFANA_API_KEY'] = grafana_key
        
        return env_vars
    
    def get_config_summary(self) -> Dict:
        """Get a summary of the configuration"""
        total_endpoints = len(self.endpoints)
        enabled_endpoints = len([e for e in self.endpoints.values() if e.enabled])
        prometheus_count = len([e for e in self.endpoints.values() if e.endpoint_type == 'prometheus'])
        grafana_count = len([e for e in self.endpoints.values() if e.endpoint_type == 'grafana'])
        
        return {
            'total_endpoints': total_endpoints,
            'enabled_endpoints': enabled_endpoints,
            'prometheus_endpoints': prometheus_count,
            'grafana_endpoints': grafana_count,
            'config_file': str(self.config_file),
            'last_modified': self.config_file.stat().st_mtime if self.config_file.exists() else None
        }