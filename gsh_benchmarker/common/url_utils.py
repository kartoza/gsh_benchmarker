"""
Shared URL management utilities for GSH Benchmarker Suite
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel

from .colors import KARTOZA_COLORS

console = Console()


class ServerHistoryManager:
    """Manages server URL history and configuration across all benchmarkers"""
    
    def __init__(self, config_file: str = "gsh_benchmarker_history.json"):
        """Initialize server history manager with config file"""
        self.config_file = Path(config_file)
        self.history = self._load_history()
    
    def _load_history(self) -> List[dict]:
        """Load server history from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('servers', [])
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]Warning: Could not load server history: {e}[/]")
        
        return []
    
    def _save_history(self):
        """Save server history to JSON file"""
        try:
            data = {
                'servers': self.history,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            console.print(f"[{KARTOZA_COLORS['alert']}]Warning: Could not save server history: {e}[/]")
    
    def add_server(self, url: str, server_type: str = "unknown", description: str = ""):
        """Add a server URL to history"""
        # Parse URL to normalize it
        parsed = urlparse(url)
        normalized_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))
        
        # Check if URL already exists
        for entry in self.history:
            if entry['url'] == normalized_url:
                entry['last_used'] = datetime.now().isoformat()
                entry['access_count'] = entry.get('access_count', 0) + 1
                if description:
                    entry['description'] = description
                self._save_history()
                return
        
        # Add new entry
        self.history.append({
            'url': normalized_url,
            'server_type': server_type,
            'description': description,
            'first_added': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'access_count': 1
        })
        
        # Keep only last 20 entries
        self.history = self.history[-20:]
        self._save_history()
    
    def get_recent_servers(self, server_type: Optional[str] = None, limit: int = 10) -> List[dict]:
        """Get recent servers, optionally filtered by type"""
        filtered_history = self.history
        
        if server_type:
            filtered_history = [entry for entry in self.history if entry.get('server_type') == server_type]
        
        # Sort by last used (most recent first)
        sorted_history = sorted(filtered_history, key=lambda x: x.get('last_used', ''), reverse=True)
        
        return sorted_history[:limit]
    
    def display_history(self, server_type: Optional[str] = None):
        """Display server history in a table"""
        recent_servers = self.get_recent_servers(server_type)
        
        if not recent_servers:
            console.print(f"[{KARTOZA_COLORS['highlight3']}]No server history found[/]")
            return
        
        table = Table(title="Recent Servers", show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("URL", style=f"{KARTOZA_COLORS['highlight2']}")
        table.add_column("Type", style=f"{KARTOZA_COLORS['highlight3']}", width=12)
        table.add_column("Description", style="dim")
        table.add_column("Last Used", style="dim", width=12)
        
        for i, entry in enumerate(recent_servers, 1):
            last_used = entry.get('last_used', '')
            if last_used:
                try:
                    dt = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                    last_used = dt.strftime("%Y-%m-%d")
                except:
                    pass
            
            table.add_row(
                str(i),
                entry['url'],
                entry.get('server_type', 'unknown'),
                entry.get('description', '')[:30] + '...' if len(entry.get('description', '')) > 30 else entry.get('description', ''),
                last_used
            )
        
        console.print(table)


def normalize_url(url: str) -> str:
    """Normalize a URL by ensuring proper schema and removing trailing slashes"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', '', ''))


def validate_url(url: str) -> bool:
    """Validate if a URL has proper format"""
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
    except:
        return False


def get_server_url_interactive(server_type: str = "server", history_manager: Optional[ServerHistoryManager] = None) -> Optional[str]:
    """
    Interactive server URL selection with history support
    
    Args:
        server_type: Type of server (e.g., 'geoserver', 'g3w', 'postgres')
        history_manager: Optional history manager instance
    
    Returns:
        Selected server URL or None if cancelled
    """
    if history_manager is None:
        history_manager = ServerHistoryManager()
    
    console.print(f"\n[{KARTOZA_COLORS['highlight2']}]🌐 {server_type.title()} Server Configuration[/]")
    
    # Show recent servers
    recent_servers = history_manager.get_recent_servers(server_type, 5)
    
    if recent_servers:
        console.print(f"\n[{KARTOZA_COLORS['highlight3']}]Recent {server_type} servers:[/]")
        for i, entry in enumerate(recent_servers, 1):
            description = entry.get('description', '')
            display_text = f"{entry['url']}"
            if description:
                display_text += f" ({description})"
            console.print(f"  [{KARTOZA_COLORS['highlight4']}]{i}.[/] {display_text}")
    
    # Get user choice
    console.print(f"\n[{KARTOZA_COLORS['highlight1']}]Options:[/]")
    if recent_servers:
        console.print(f"  • Enter a number (1-{len(recent_servers)}) to use a recent server")
    else:
        console.print(f"  • No recent {server_type} servers found")
    console.print(f"  • Enter a new {server_type} URL (e.g., http://your-server.com:8080/geoserver)")
    console.print(f"  • Press Enter to cancel")
    
    choice = Prompt.ask(f"\n[{KARTOZA_COLORS['highlight2']}]Your choice[/]").strip()
    
    if not choice:
        return None
    
    # Check if it's a number (selecting from recent servers)
    try:
        index = int(choice) - 1
        if 0 <= index < len(recent_servers):
            selected_url = recent_servers[index]['url']
            history_manager.add_server(selected_url, server_type)
            return selected_url
        else:
            console.print(f"[{KARTOZA_COLORS['alert']}]Invalid selection[/]")
            return get_server_url_interactive(server_type, history_manager)
    except ValueError:
        pass
    
    # Treat as new URL
    url = normalize_url(choice)
    
    if not validate_url(url):
        console.print(f"[{KARTOZA_COLORS['alert']}]Invalid URL format[/]")
        return get_server_url_interactive(server_type, history_manager)
    
    # Ask for description
    description = Prompt.ask(
        f"[{KARTOZA_COLORS['highlight3']}]Description (optional)[/]", 
        default=""
    ).strip()
    
    # Add to history
    history_manager.add_server(url, server_type, description)
    
    console.print(f"[{KARTOZA_COLORS['highlight4']}]✓ Server configured: {url}[/]")
    return url