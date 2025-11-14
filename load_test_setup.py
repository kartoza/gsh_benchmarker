#!/usr/bin/env python3
"""
GeoServer Load Testing Setup
Creates WMTS tile requests and Apache Bench load testing scripts
"""

import requests
import json
import math
import os

# GeoServer configuration
GEOSERVER_BASE = "https://climate-adaptation-services.geospatialhosting.com/geoserver"
WMTS_BASE = f"{GEOSERVER_BASE}/gwc/service/wmts"

# Four published layers discovered
LAYERS = [
    "CAS:AfstandTotKoelte",
    "CAS:bkb_2024", 
    "CAS:pok_normplusklimaatverandering2100_50cm",
    "CAS:zonalstatistics_pet2022actueel_2024124"
]

# Tile Matrix Set for EPSG:3857 (Web Mercator)
TILE_MATRIX_SET = "WebMercatorQuad"

# Bounding box for Netherlands area (from capabilities)
BBOX = {
    'minx': 3.0501174525180246,
    'miny': 50.72860969022719, 
    'maxx': 7.345047048668708,
    'maxy': 53.718455402582535
}

def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile numbers"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def get_tile_urls(layer, zoom_level=10):
    """Generate tile URLs for a layer at given zoom level"""
    # Calculate tile bounds for the Netherlands area
    min_tile = deg2num(BBOX['miny'], BBOX['minx'], zoom_level)
    max_tile = deg2num(BBOX['maxy'], BBOX['maxx'], zoom_level)
    
    urls = []
    
    # Generate a subset of tiles to avoid overwhelming the server
    x_step = max(1, (max_tile[0] - min_tile[0]) // 10)  # Sample every 10th tile
    y_step = max(1, (max_tile[1] - min_tile[1]) // 10)
    
    for x in range(min_tile[0], max_tile[0] + 1, x_step):
        for y in range(min_tile[1], max_tile[1] + 1, y_step):
            url = (f"{WMTS_BASE}?"
                   f"SERVICE=WMTS&"
                   f"REQUEST=GetTile&"
                   f"VERSION=1.0.0&"
                   f"LAYER={layer}&"
                   f"STYLE=&"
                   f"TILEMATRIXSET={TILE_MATRIX_SET}&"
                   f"TILEMATRIX={zoom_level}&"
                   f"TILEROW={y}&"
                   f"TILECOL={x}&"
                   f"FORMAT=image/png")
            urls.append(url)
    
    return urls[:50]  # Limit to 50 tiles per layer for testing

def create_url_file(layer, urls, filename):
    """Create URL file for Apache Bench"""
    with open(filename, 'w') as f:
        for url in urls:
            f.write(f"{url}\n")
    print(f"Created {filename} with {len(urls)} URLs for {layer}")

def create_load_test_scripts():
    """Create Apache Bench load testing scripts"""
    
    # Create individual layer test scripts
    for layer in LAYERS:
        layer_name = layer.split(':')[1]  # Remove CAS: prefix
        urls = get_tile_urls(layer)
        url_file = f"urls_{layer_name}.txt"
        script_file = f"load_test_{layer_name}.sh"
        
        # Create URL file
        create_url_file(layer, urls, url_file)
        
        # Create bash script for load testing
        script_content = f"""#!/bin/bash
# Load test for {layer}
echo "Starting load test for {layer}"
echo "Testing with 5000 total requests, 100 concurrent connections"
echo "Target: WMTS tiles for layer {layer}"
echo ""

# Test single URL first
echo "Testing single tile request..."
ab -n 1 -c 1 "{urls[0] if urls else ''}" 

echo ""
echo "Starting main load test..."

# Main load test - 5000 requests with high concurrency
ab -n 5000 -c 100 -g load_test_{layer_name}.data -e load_test_{layer_name}.csv \\
   -H "Accept: image/png,*/*" \\
   -H "User-Agent: LoadTest/1.0" \\
   "{urls[0] if urls else ''}"

echo ""
echo "Load test completed for {layer}"
echo "Results saved to load_test_{layer_name}.csv"
echo "Gnuplot data saved to load_test_{layer_name}.data"
"""
        
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_file, 0o755)
        print(f"Created {script_file}")

def create_master_test_script():
    """Create master script to run all tests"""
    master_script = """#!/bin/bash
# Master load testing script for all GeoServer layers
echo "========================================="
echo "GeoServer Load Testing Suite"
echo "========================================="
echo "Testing 4 layers with WMTS tile requests"
echo "Each test: 5000 requests, 100 concurrent"
echo ""

# Create results directory
mkdir -p results
cd results

# Run individual layer tests
"""
    
    for layer in LAYERS:
        layer_name = layer.split(':')[1]
        master_script += f"""
echo "Testing {layer}..."
../load_test_{layer_name}.sh | tee {layer_name}_output.log
sleep 10  # Brief pause between tests
"""
    
    master_script += """
echo ""
echo "========================================="
echo "All load tests completed!"
echo "Check individual log files for detailed results"
echo "Summary files: load_test_*.csv"
echo "========================================="
"""
    
    with open("run_all_load_tests.sh", 'w') as f:
        f.write(master_script)
    
    os.chmod("run_all_load_tests.sh", 0o755)
    print("Created run_all_load_tests.sh")

def test_single_tile():
    """Test a single tile request to verify everything works"""
    test_layer = LAYERS[0]
    urls = get_tile_urls(test_layer, zoom_level=5)  # Lower zoom for testing
    
    if urls:
        test_url = urls[0]
        print(f"Testing single tile request: {test_url}")
        
        try:
            response = requests.get(test_url, timeout=10)
            if response.status_code == 200:
                print(f"✓ Success! Content-Type: {response.headers.get('content-type')}")
                print(f"✓ Response size: {len(response.content)} bytes")
                return True
            else:
                print(f"✗ Error: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"✗ Request failed: {e}")
            return False
    else:
        print("✗ No URLs generated")
        return False

if __name__ == "__main__":
    print("GeoServer Load Testing Setup")
    print("=" * 50)
    
    # Test connectivity first
    print("\n1. Testing connectivity...")
    if test_single_tile():
        print("\n2. Creating load test scripts...")
        create_load_test_scripts()
        
        print("\n3. Creating master test script...")
        create_master_test_script()
        
        print("\n" + "=" * 50)
        print("Setup complete! Usage:")
        print("  ./run_all_load_tests.sh    # Run all layer tests")
        print("  ./load_test_<layer>.sh     # Run single layer test")
        print("\nNote: 5000 concurrent requests is aggressive.")
        print("Consider starting with lower numbers (e.g., 1000 requests, 50 concurrent)")
        print("to avoid overwhelming the server.")
    else:
        print("✗ Connectivity test failed. Check server availability.")