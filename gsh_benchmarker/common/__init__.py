"""
Common utilities and shared resources for GSH Benchmarker Suite

This module contains shared functionality that can be used across all
benchmarker implementations (GeoServer, G3W, PostgreSQL, GeoNode).
"""

from .colors import KARTOZA_COLORS
from .config import (
    CONCURRENCY_LEVELS,
    DEFAULT_TOTAL_REQUESTS,
    DEFAULT_CONCURRENCY,
    RESULTS_DIR,
    REPORTS_DIR,
    TEMP_DIR,
    REQUEST_TIMEOUT,
    CONNECTION_TIMEOUT,
    MAX_RETRIES,
    AB_USER_AGENT,
    AB_ACCEPT_HEADER,
    AB_TIMEOUT,
    MAP_IMAGE_WIDTH,
    MAP_IMAGE_HEIGHT,
    PREVIEW_SIZE,
    CSV_PATTERN,
    LOG_PATTERN,
    JSON_PATTERN
)
from .url_utils import (
    ServerHistoryManager,
    normalize_url,
    validate_url,
    get_server_url_interactive
)
from .utils import (
    BenchmarkResult,
    BaseBenchmarker,
    run_apache_bench,
    parse_ab_output,
    save_benchmark_result,
    create_results_summary_table,
    format_timestamp,
    validate_concurrency_level
)
from .reports import (
    ReportGenerator,
    find_latest_report_file,
    execute_external_report_generator,
    create_benchmark_summary_panel
)
from .image_utils import (
    TerminalImageRenderer,
    download_preview_image,
    create_simple_chart_ascii
)

__all__ = [
    # Colors
    "KARTOZA_COLORS",
    
    # Configuration
    "CONCURRENCY_LEVELS",
    "DEFAULT_TOTAL_REQUESTS", 
    "DEFAULT_CONCURRENCY",
    "RESULTS_DIR",
    "REPORTS_DIR",
    "TEMP_DIR",
    "REQUEST_TIMEOUT",
    "CONNECTION_TIMEOUT",
    "MAX_RETRIES",
    "AB_USER_AGENT",
    "AB_ACCEPT_HEADER",
    "AB_TIMEOUT",
    "MAP_IMAGE_WIDTH",
    "MAP_IMAGE_HEIGHT",
    "PREVIEW_SIZE",
    "CSV_PATTERN",
    "LOG_PATTERN",
    "JSON_PATTERN",
    
    # URL utilities
    "ServerHistoryManager",
    "normalize_url",
    "validate_url", 
    "get_server_url_interactive",
    
    # Benchmark utilities
    "BenchmarkResult",
    "BaseBenchmarker",
    "run_apache_bench",
    "parse_ab_output",
    "save_benchmark_result",
    "create_results_summary_table",
    "format_timestamp",
    "validate_concurrency_level",
    
    # Report utilities
    "ReportGenerator",
    "find_latest_report_file",
    "execute_external_report_generator", 
    "create_benchmark_summary_panel",
    
    # Image utilities
    "TerminalImageRenderer",
    "download_preview_image",
    "create_simple_chart_ascii"
]