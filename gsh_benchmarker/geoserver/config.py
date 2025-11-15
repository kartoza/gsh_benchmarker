"""
GeoServer-specific configuration settings
"""

import os
from pathlib import Path

# Import shared configuration from common module
from ..common import (
    KARTOZA_COLORS, CONCURRENCY_LEVELS, DEFAULT_TOTAL_REQUESTS, 
    DEFAULT_CONCURRENCY, RESULTS_DIR, REPORTS_DIR, TEMP_DIR,
    AB_USER_AGENT, REQUEST_TIMEOUT, CONNECTION_TIMEOUT, MAX_RETRIES,
    MAP_IMAGE_WIDTH, MAP_IMAGE_HEIGHT, PREVIEW_SIZE,
    CSV_PATTERN, LOG_PATTERN, JSON_PATTERN
)

# Default GeoServer configuration (can be overridden dynamically)
DEFAULT_BASE_DOMAIN = "geospatialhosting.com"
DEFAULT_SUBDOMAIN = "climate-adaptation-services"

# Layer discovery configuration
# Note: Layers are now discovered dynamically from WMS GetCapabilities
# This replaces the previous hardcoded LAYERS dictionary

# GeoServer-specific test configuration
DEFAULT_ZOOM_LEVEL = 8
DEFAULT_TILE_ROW = 84
DEFAULT_TILE_COL = 133

# Generic world bounding boxes for fallback when layer bbox is not available
WORLD_BBOX_4326 = [-180, -90, 180, 90]  # Full world in WGS84
WORLD_BBOX_3857 = [-20037508, -20037508, 20037508, 20037508]  # Web Mercator world extent

# GeoServer-specific Apache Bench configuration
AB_ACCEPT_HEADER = "image/png,*/*"
AB_TIMEOUT = 60

# Tile matrix configuration
TILE_MATRIX_SET = "WebMercatorQuad"
TILE_FORMAT = "image/png"