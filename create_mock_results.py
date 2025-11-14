#!/usr/bin/env python3
"""
Create mock test results for testing the PDF report generator
"""

import json
import math
from datetime import datetime

def create_mock_results():
    timestamp = "test_20241114_123000"
    
    # Layer definitions
    layers = [
        "AfstandTotKoelte",
        "bkb_2024", 
        "pok_normplusklimaatverandering2100_50cm",
        "zonalstatistics_pet2022actueel_2024124"
    ]
    
    concurrency_levels = [1, 10, 100, 500, 1000, 2000, 3000, 4000, 5000]
    
    consolidated_data = {
        "test_suite": {
            "name": "GeoServer Comprehensive Load Test",
            "timestamp": timestamp,
            "date": "2024-11-14T12:30:00+00:00",
            "total_requests_per_test": 5000,
            "concurrency_levels": concurrency_levels,
            "layers_tested": layers,
            "server": "climate-adaptation-services.geospatialhosting.com"
        },
        "results": []
    }
    
    # Generate realistic mock performance data
    for layer in layers:
        for concurrency in concurrency_levels:
            # Realistic performance degradation with higher concurrency
            # Base performance starts good and degrades with higher concurrency
            base_rps = 100.0
            
            # RPS decreases with higher concurrency due to bottlenecks
            if concurrency <= 10:
                rps = base_rps * (1 - (concurrency - 1) * 0.05)
            elif concurrency <= 100:
                rps = base_rps * 0.5 * (1 - (concurrency - 10) * 0.002)
            else:
                rps = base_rps * 0.3 * (1 - (concurrency - 100) * 0.0001)
            
            # Response time increases with concurrency
            mean_time = 50.0 + (concurrency * 0.1)
            if concurrency > 1000:
                mean_time += (concurrency - 1000) * 0.05
                
            # Failed requests increase slightly with higher concurrency
            failed = min(int(concurrency / 500), 50)
            
            # Transfer rate correlates with RPS
            transfer_rate = rps * 8.5
            
            # Total time is requests / rps
            total_time = 5000.0 / rps
            
            # Success rate
            success_rate = ((5000 - failed) / 5000) * 100
            
            result = {
                "layer": layer,
                "description": f"Load test for {layer}",
                "timestamp": timestamp,
                "test_id": f"{layer}_c{concurrency}_{timestamp}",
                "total_requests": 5000,
                "concurrency_level": concurrency,
                "tile_url": f"https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts?LAYER=CAS:{layer}",
                "test_date": "2024-11-14T12:30:00+00:00",
                "server": "climate-adaptation-services.geospatialhosting.com",
                "protocol": "WMTS",
                "tile_matrix": "8",
                "tile_row": "84",
                "tile_col": "133",
                "format": "image/png",
                "results": {
                    "requests_per_second": f"{rps:.2f}",
                    "mean_response_time_ms": f"{mean_time:.2f}",
                    "failed_requests": str(failed),
                    "total_time_seconds": f"{total_time:.2f}",
                    "transfer_rate_kbps": f"{transfer_rate:.2f}",
                    "success_rate": f"{success_rate:.1f}"
                }
            }
            
            consolidated_data["results"].append(result)
    
    # Save to file
    output_file = f"results/consolidated_results_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(consolidated_data, f, indent=2)
    
    print(f"Mock results created: {output_file}")
    return timestamp

if __name__ == "__main__":
    create_mock_results()