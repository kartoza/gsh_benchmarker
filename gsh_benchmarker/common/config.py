"""
Shared configuration settings for GSH Benchmarker Suite
"""

import os
from pathlib import Path

# Default concurrency levels for incremental testing (shared across all benchmarkers)
CONCURRENCY_LEVELS = [1, 10, 100, 500, 1000, 2000, 3000, 4000, 5000]

# Test configuration defaults (common to all service types)
DEFAULT_TOTAL_REQUESTS = 5000
DEFAULT_CONCURRENCY = 100

# Directory paths (shared)
RESULTS_DIR = Path("results")
REPORTS_DIR = Path("reports") 
TEMP_DIR = Path("/tmp/gsh_benchmarker_previews")

# File patterns (shared)
CSV_PATTERN = "*.csv"
LOG_PATTERN = "*.log" 
JSON_PATTERN = "*.json"

# Request configuration (shared)
REQUEST_TIMEOUT = 30
CONNECTION_TIMEOUT = 10
MAX_RETRIES = 3

# Report configuration (shared)
MAP_IMAGE_WIDTH = 600
MAP_IMAGE_HEIGHT = 400
PREVIEW_SIZE = "80x25"

# Apache Bench configuration (can be used by multiple benchmarkers)
AB_USER_AGENT = "GSH-Benchmarker/1.0"
AB_ACCEPT_HEADER = "application/json,text/html,*/*"
AB_TIMEOUT = 60