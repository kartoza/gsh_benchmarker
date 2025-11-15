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

# Netherlands bounding box (EPSG:3857 - Web Mercator)
NETHERLANDS_BBOX = [360584.6875, 6618208.5, 839275.4375, 7108899.5]

# Netherlands bounding box (EPSG:4326 - WGS84)  
NETHERLANDS_BBOX_4326 = [3.0501, 50.7286, 7.3450, 53.7185]

# GeoServer-specific Apache Bench configuration
AB_ACCEPT_HEADER = "image/png,*/*"
AB_TIMEOUT = 60

# Tile matrix configuration
TILE_MATRIX_SET = "WebMercatorQuad"
TILE_FORMAT = "image/png"