#!/usr/bin/env python3
"""
GeoServer Configuration Tool
Manages GeoWebCache configuration and layer publishing via REST API
"""

import json
import requests
from requests.auth import HTTPBasicAuth
import sys
import os
from urllib.parse import quote
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.live import Live
import time

# Import Kartoza themed console
from kartoza_rich_theme import console, print_info, print_warning, print_error, print_success, print_header

class GeoServerClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.rest_url = f"{self.base_url}/rest"
        self.gwc_url = f"{self.base_url}/gwc/rest"
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def test_connection(self):
        """Test connection to GeoServer"""
        try:
            response = self.session.get(f"{self.rest_url}/about/version")
            response.raise_for_status()
            return True, response.json()
        except requests.RequestException as e:
            return False, str(e)
            
    def get_workspaces(self):
        """Get all workspaces"""
        try:
            response = self.session.get(f"{self.rest_url}/workspaces")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error getting workspaces: {e}[/red]")
            return None
            
    def get_layers(self, workspace=None):
        """Get all layers or layers in a specific workspace"""
        try:
            if workspace:
                url = f"{self.rest_url}/workspaces/{workspace}/layers"
            else:
                url = f"{self.rest_url}/layers"
            
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error getting layers: {e}[/red]")
            return None
            
    def get_layer_info(self, layer_name, workspace=None):
        """Get detailed information about a layer"""
        try:
            if workspace:
                url = f"{self.rest_url}/workspaces/{workspace}/layers/{layer_name}"
            else:
                url = f"{self.rest_url}/layers/{layer_name}"
                
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error getting layer info for {layer_name}: {e}[/red]")
            return None
            
    def get_gwc_layer_config(self, layer_name):
        """Get GeoWebCache configuration for a layer"""
        try:
            url = f"{self.gwc_url}/layers/{quote(layer_name)}.json"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]Error getting GWC config for {layer_name}: {e}[/red]")
            return None
            
    def configure_gwc_layer(self, layer_name, config=None):
        """Configure GeoWebCache for a layer"""
        if config is None:
            # Default configuration with EPSG:3857 support
            config = {
                "GeoServerLayer": {
                    "name": layer_name,
                    "enabled": True,
                    "mimeFormats": [
                        "image/png",
                        "image/jpeg"
                    ],
                    "gridSubsets": [
                        {
                            "gridSetName": "EPSG:4326"
                        },
                        {
                            "gridSetName": "EPSG:900913"
                        },
                        {
                            "gridSetName": "WebMercatorQuad"
                        }
                    ],
                    "metaWidthHeight": [4, 4],
                    "expireCache": 0,
                    "expireClients": 0,
                    "parameterFilters": [],
                    "gutter": 0
                }
            }
        
        try:
            url = f"{self.gwc_url}/layers/{quote(layer_name)}.json"
            response = self.session.put(
                url,
                json=config,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return True, "Layer configured successfully"
        except requests.RequestException as e:
            return False, f"Error configuring layer {layer_name}: {e}"
            
    def seed_layer(self, layer_name, grid_set="WebMercatorQuad", format="image/png", 
                   zoom_start=0, zoom_stop=10, bbox=None):
        """Seed tiles for a layer"""
        seed_request = {
            "seedRequest": {
                "name": layer_name,
                "gridSetId": grid_set,
                "format": format,
                "type": "seed",
                "zoomStart": zoom_start,
                "zoomStop": zoom_stop,
                "threadCount": 4
            }
        }
        
        if bbox:
            seed_request["seedRequest"]["bounds"] = {
                "coords": {
                    "double": bbox
                }
            }
            
        try:
            url = f"{self.gwc_url}/seed/{quote(layer_name)}.json"
            response = self.session.post(
                url,
                json=seed_request,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return True, "Seeding started successfully"
        except requests.RequestException as e:
            return False, f"Error starting seed for {layer_name}: {e}"
            
    def get_cache_statistics(self, layer_name):
        """Get cache statistics for a layer"""
        try:
            # This endpoint might not be available in all GeoServer versions
            url = f"{self.gwc_url}/statistics"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[yellow]Cache statistics not available: {e}[/yellow]")
            return None

def load_credentials():
    """Load credentials from credentials.json file"""
    creds_file = "credentials.json"
    
    if not os.path.exists(creds_file):
        console.print(f"[red]❌ Credentials file {creds_file} not found![/red]")
        console.print("Create it from credentials.json.example")
        return None
        
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
            return creds['geoserver']
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]❌ Error reading credentials: {e}[/red]")
        return None

def show_banner():
    """Display beautiful banner using rich"""
    banner_text = Text("🔧 GeoServer Configuration Tool", style="bold cyan")
    subtitle_text = Text("Climate Adaptation Services • GeoWebCache Optimization", style="dim")
    
    banner_panel = Panel.fit(
        Text.assemble(
            (banner_text, "bold cyan"),
            "\n",
            (subtitle_text, "dim")
        ),
        border_style="blue"
    )
    
    console.print(banner_panel)
    console.print()

def create_layer_table(layers_info):
    """Create a beautiful table showing layer information"""
    table = Table(title="Target Layers for Configuration", show_header=True, header_style="bold cyan")
    
    table.add_column("Layer Name", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Description", style="dim")
    
    for layer_name, status, description in layers_info:
        if status == "found":
            status_text = "[green]✅ Found[/green]"
        elif status == "configured":
            status_text = "[blue]🔧 Configured[/blue]"
        elif status == "seeded":
            status_text = "[yellow]🌱 Seeded[/yellow]"
        else:
            status_text = "[red]❌ Error[/red]"
            
        table.add_row(layer_name, status_text, description)
    
    return table

def main():
    show_banner()
    
    # Load credentials
    creds = load_credentials()
    if not creds:
        return 1
        
    # Connect to GeoServer with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Connecting to GeoServer...", total=None)
        client = GeoServerClient(creds['url'], creds['username'], creds['password'])
        
        # Test connection
        success, result = client.test_connection()
        progress.update(task, description="Connection test completed")
        
    if not success:
        console.print(f"[red]❌ Connection failed: {result}[/red]")
        return 1
    
    version = result.get('about', {}).get('resource', {}).get('Version', 'Unknown')
    console.print(f"[green]✅ Connected to GeoServer {version}[/green]")
    console.print()
    
    # Target layers with descriptions
    target_layers = {
        "CAS:AfstandTotKoelte": "Distance to Cooling Areas",
        "CAS:bkb_2024": "Built Environment Database 2024",
        "CAS:pok_normplusklimaatverandering2100_50cm": "Climate Change Impact 2100 (50cm)",
        "CAS:zonalstatistics_pet2022actueel_2024124": "Zonal Statistics PET 2022"
    }
    
    layers_info = []
    
    # Netherlands bbox for seeding (in EPSG:3857)
    netherlands_bbox = [360584.6875, 6618208.5, 839275.4375, 7108899.5]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        
        task = progress.add_task("Configuring layers...", total=len(target_layers))
        
        for layer_name, description in target_layers.items():
            progress.update(task, description=f"Processing {layer_name}...")
            
            # Check if layer exists
            layer_info = client.get_layer_info(layer_name)
            if not layer_info:
                layers_info.append((layer_name, "error", f"{description} - Not found"))
                progress.advance(task)
                continue
                
            layers_info.append((layer_name, "found", description))
            
            # Configure GeoWebCache
            success, message = client.configure_gwc_layer(layer_name)
            if success:
                layers_info[-1] = (layer_name, "configured", description)
            else:
                layers_info[-1] = (layer_name, "error", f"{description} - Config failed")
                progress.advance(task)
                continue
                
            # Seed some tiles for better performance
            success, message = client.seed_layer(
                layer_name, 
                grid_set="WebMercatorQuad",
                zoom_start=0,
                zoom_stop=8,
                bbox=netherlands_bbox
            )
            if success:
                layers_info[-1] = (layer_name, "seeded", description)
            
            progress.advance(task)
    
    # Show results table
    console.print()
    table = create_layer_table(layers_info)
    console.print(table)
    
    # Summary
    console.print()
    successful_configs = sum(1 for _, status, _ in layers_info if status in ["configured", "seeded"])
    
    if successful_configs == len(target_layers):
        console.print(Panel.fit(
            Text.assemble(
                ("✅ Configuration Completed Successfully!", "bold green"), "\n\n",
                ("💡 All layers are now optimized for WMTS tile serving", "dim"), "\n",
                ("🚀 Run ", ""), ("./geoserver_menu.sh", "bold cyan"), (" to start load testing", "")
            ),
            border_style="green",
            title="[bold green]Success[/bold green]"
        ))
    else:
        console.print(Panel.fit(
            Text.assemble(
                (f"⚠️  Partial Success: {successful_configs}/{len(target_layers)} layers configured", "yellow"), "\n\n",
                ("Some layers may have configuration issues", "dim"), "\n",
                ("Check credentials and layer availability", "dim")
            ),
            border_style="yellow",
            title="[bold yellow]Warning[/bold yellow]"
        ))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())