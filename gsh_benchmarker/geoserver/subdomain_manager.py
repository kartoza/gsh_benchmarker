"""
GeoServer-specific subdomain management with history storage
"""

from typing import Optional
from rich.console import Console

from .config import KARTOZA_COLORS, DEFAULT_BASE_DOMAIN, DEFAULT_SUBDOMAIN
from ..common.url_utils import ServerHistoryManager, get_server_url_interactive as get_server_url_base

console = Console()


def get_server_url_interactive() -> Optional[str]:
    """
    GeoServer-specific server URL selection with history support
    
    Returns:
        Selected GeoServer URL or None if cancelled
    """
    return get_server_url_base("geoserver")


class SubdomainManager(ServerHistoryManager):
    """GeoServer-specific subdomain manager - extends common ServerHistoryManager"""
    
    def __init__(self, config_file: str = "geoserver_history.json"):
        """Initialize GeoServer subdomain manager"""
        super().__init__(config_file)
    
    def add_geoserver_subdomain(self, subdomain: str, base_domain: str = None) -> str:
        """Add a GeoServer subdomain to history"""
        if base_domain is None:
            base_domain = DEFAULT_BASE_DOMAIN
            
        full_url = f"https://{subdomain}.{base_domain}/geoserver"
        self.add_server(full_url, "geoserver", f"Subdomain: {subdomain}")
        return full_url
    
    def get_subdomain_interactive(self) -> Optional[str]:
        """Interactive subdomain selection - delegates to common functionality"""
        return get_server_url_interactive()