"""
GSH Benchmarker Suite

A comprehensive benchmarking framework for geospatial services including:
- GeoServer WMTS tiles
- G3W (coming soon)  
- PostgreSQL/PostGIS (coming soon)
- GeoNode (coming soon)
"""

__version__ = "1.0.0"
__author__ = "Kartoza"

# Import common utilities
from .common import (
    KARTOZA_COLORS,
    CONCURRENCY_LEVELS,
    DEFAULT_TOTAL_REQUESTS,
    BenchmarkResult,
    BaseBenchmarker,
    ServerHistoryManager
)

# Import GeoServer benchmarker components
from .geoserver import (
    GeoServerTester,
    MenuInterface,
    discover_layers,
    LayerInfo,
    CapabilitiesParser,
    SubdomainManager,
    get_server_url_interactive
)

__all__ = [
    # Common utilities
    "KARTOZA_COLORS", 
    "CONCURRENCY_LEVELS",
    "DEFAULT_TOTAL_REQUESTS",
    "BenchmarkResult",
    "BaseBenchmarker", 
    "ServerHistoryManager",
    
    # GeoServer components
    "GeoServerTester", 
    "MenuInterface",
    "discover_layers",
    "LayerInfo",
    "CapabilitiesParser", 
    "SubdomainManager",
    "get_server_url_interactive"
]