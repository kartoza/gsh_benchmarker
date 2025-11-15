# 🌍 GeoServer Load Testing Suite

A comprehensive Python-based load testing framework for GeoServer WMTS tiles with rich UI components and detailed reporting capabilities.

## 🚀 Quick Start

### Running Tests

Run the comprehensive test suite with beautiful progress reporting:

```bash
./test
```

Or directly with Python:
```bash
python3 run_tests.py
```

The test runner provides:
- 🎨 Rich terminal UI with Kartoza colors
- ⚡ Real-time progress tracking
- 📊 Detailed test results with module breakdown
- 🔍 Coverage analysis (if coverage.py is available)
- ✅ Pass/fail indicators for each test
- 🌳 Tree view of test hierarchy

### Interactive Menu (Recommended)

```bash
python3 geotest.py
```

### Command Line Usage

Test connectivity to all layers:
```bash
python3 geotest.py --connectivity
```

Run a single layer test:
```bash
python3 geotest.py --single AfstandTotKoelte --requests 1000
```

Run comprehensive tests across all layers:
```bash
python3 geotest.py --comprehensive --requests 5000
```

### Legacy Shell Scripts (Deprecated)

The old shell scripts are deprecated. Use the Python tool instead:

```bash
# Old way (deprecated):
./geoserver_menu.sh

# New way:
python3 geotest.py
```

## 🎯 Features

### 🎨 Rich Python Interface
- **Interactive Menu System** - Beautiful command-line interface with progress bars
- **Real-time Progress** - Live feedback during load tests with Rich UI components
- **Results Visualization** - Comprehensive tables and summaries
- **Color-coded Output** - Kartoza-themed color scheme throughout
- **Map Previews** - Download and optionally display map images (with chafa)

### ⚡ Load Testing Capabilities  
- **Apache Bench Integration** - Industry-standard HTTP benchmarking
- **WMTS Tile Testing** - High-performance WebMercatorQuad (EPSG:3857) tile requests
- **Configurable Parameters** - Custom request counts and concurrency levels
- **Multiple Test Modes** - Single layer, comprehensive, and connectivity testing
- **Results Management** - Automatic results clearing and storage
- **Detailed Metrics** - CSV/JSON exports with timing data, RPS, percentiles

### 🔧 Python Architecture
- **Modular Design** - Clean separation of core, UI, and configuration
- **Type Hints** - Full type annotations for better code quality
- **Rich Progress Tracking** - Real-time task management with visual feedback
- **Error Handling** - Comprehensive error handling with user-friendly messages
- **Extensible Configuration** - Easy to adapt for other GeoServer instances

## 📊 Target Layers

The suite tests these Climate Adaptation Services layers on `https://climate-adaptation-services.geospatialhosting.com/geoserver`:

1. **CAS:AfstandTotKoelte** - Distance to Cooling Areas (vector data)
2. **CAS:bkb_2024** - Built Environment Database 2024 (raster data, 8.5GB TIF)
3. **CAS:pok_normplusklimaatverandering2100_50cm** - Climate Change Impact 2100 (50cm sea level rise)
4. **CAS:zonalstatistics_pet2022actueel_2024124** - Zonal Statistics PET 2022

**Coverage Area**: Netherlands (BBOX: 3.05°E, 50.73°N to 7.35°E, 53.72°N)  
**Tile Coordinates**: WebMercatorQuad zoom 8, TileCol 133, TileRow 84

## 🛠️ Tools Included

### Performance Testing
- **Apache Bench (ab)** - HTTP server benchmarking
- **Custom Scripts** - WMTS-optimized load testing

### API Interaction
- **httpie** - Modern command-line HTTP client
- **hurl** - Command-line HTTP request tool
- **Custom Python Client** - GeoServer REST API integration

### Development
- **Python 3** - With requests, httpx, PyYAML
- **Java/Maven** - For GeoServer Java client development
- **Rust toolchain** - For building ATAC (TUI Postman alternative)

### Visualization & UI
- **gum** - Beautiful interactive TUI components for menus and prompts
- **rich** - Stunning Python terminal interfaces with progress bars and tables
- **chafa** - Display PNG/JPEG images in terminal with symbol rendering
- **ImageMagick** - Image processing for map previews and format conversion

## 📁 File Structure

```
├── flake.nix                                          # Nix development environment (gum, chafa, ab, etc.)
├── .envrc                                            # direnv configuration for auto-activation
├── .gitignore                                        # Excludes credentials.json and test results
├── credentials.json.example                          # Template for GeoServer admin credentials
│
├── geoserver_menu.sh                                # 🎨 Main interactive gum-powered menu
├── geoserver_config.py                              # 🔧 Rich Python GeoWebCache configuration tool
├── test_tile_access.sh                              # 🔍 Basic connectivity testing script
│
├── load_test_AfstandTotKoelte.sh                    # ⚡ Individual layer load tests
├── load_test_bkb_2024.sh                            #    (5000 requests, 100 concurrent)
├── load_test_pok_normplusklimaatverandering2100_50cm.sh
├── load_test_zonalstatistics_pet2022actueel_2024124.sh
├── load_test_setup.py                               # 🐍 Python tile URL generator (backup)
│
├── results/                                          # 📊 Auto-generated test results
│   ├── *_results.csv                               #    Performance metrics (RPS, latency)
│   ├── *_load.data                                 #    Gnuplot data files
│   └── *_output.log                                #    Complete Apache Bench logs
│
└── README.md                                        # 📖 This documentation
```

## 🎮 Usage Guide

### Interactive Menu Options

1. **🖼️ Preview Layer Maps**
   - Fetches WMS map images
   - Displays in terminal with chafa
   - Useful for verifying layer visibility

2. **⚡ Run Single Layer Test**
   - Select specific layer to test
   - Configure request count and concurrency
   - Get detailed performance metrics

3. **🔥 Run All Tests**
   - Sequential testing of all layers
   - Configurable pause between tests
   - Comprehensive performance analysis

4. **📊 View Results**
   - Browse previous test results
   - CSV and log file viewing
   - Performance trend analysis

5. **🔧 Test Connectivity**
   - Verify all WMTS endpoints
   - Quick health check before testing

### Manual Commands

```bash
# Test single layer manually (5000 requests, 100 concurrent)
ab -n 5000 -c 100 \
   -H "Accept: image/png,*/*" \
   -H "User-Agent: GeoServer-LoadTest/1.0" \
   "https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=CAS:bkb_2024&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=8&TILEROW=84&TILECOL=133&FORMAT=image/png"

# Configure GeoWebCache with beautiful rich interface
python3 geoserver_config.py

# Preview a layer map in terminal (Netherlands bbox)
curl -s "https://climate-adaptation-services.geospatialhosting.com/geoserver/wms?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=CAS:bkb_2024&SRS=EPSG:3857&BBOX=360584.6875,6618208.5,839275.4375,7108899.5&WIDTH=600&HEIGHT=400&FORMAT=image/png" -o preview.png && chafa --size 80x25 preview.png

# Test WMTS connectivity for all layers
./test_tile_access.sh

# Run individual layer test
./load_test_bkb_2024.sh
```

## 📈 Performance Metrics

The load tests generate comprehensive metrics including:

- **Requests per Second (RPS)** - Server throughput capacity
- **Average Response Time** - Mean latency for tile delivery
- **95th Percentile Response Time** - Performance under load
- **Minimum/Maximum Response Times** - Best/worst case scenarios
- **Failed Request Count** - Error rate analysis
- **Transfer Rate (KB/sec)** - Bandwidth utilization
- **Connection Times** - Network overhead analysis
- **Concurrency Level** - Simultaneous connection handling

### Output Formats
- **CSV files** (`*_results.csv`) - Detailed percentile data for spreadsheet analysis
- **Gnuplot data** (`*_load.data`) - Time-series plotting data
- **Log files** (`*_output.log`) - Complete Apache Bench output with headers and timing
- **Console output** - Real-time summary statistics during testing

### Example Results
```
Requests per Second:    847.23 [#/sec] (mean)
Time per request:       118.021 [ms] (mean)
Transfer rate:          2891.45 [Kbytes/sec] received
```

## 🔐 Security Notes

- Store credentials in `credentials.json` (automatically gitignored)
- Use read-only credentials when possible
- Monitor server resources during load testing
- Start with lower request counts to avoid overwhelming the server

## 🎯 Load Testing Best Practices

1. **Start Small** - Begin with 100-1000 requests
2. **Increase Gradually** - Build up to 5000+ requests
3. **Monitor Server** - Watch CPU/memory usage
4. **Use Caching** - Configure GeoWebCache for optimal performance
5. **Test Realistic Scenarios** - Use actual tile coordinates for your region

## 🚨 Warning

**Load testing generates significant server load!** 

- The default **5000 requests with 100 concurrent connections** is aggressive
- This equals **50 requests per concurrent connection** hitting the server simultaneously
- Only use on servers you own or have **explicit permission** to test
- Monitor server CPU/memory during testing to avoid overwhelming the system
- Consider starting with 1000 requests and 50 concurrent connections for initial testing

**Target server**: `climate-adaptation-services.geospatialhosting.com` - Ensure you have authorization!

## 📞 Support & Troubleshooting

### Common Issues

1. **Nix environment not loading**:
   ```bash
   nix develop --show-trace
   direnv allow  # If using direnv
   ```

2. **Dependencies missing**:
   ```bash
   # Check if all tools are available
   which gum chafa ab curl python3
   ```

3. **GeoServer connectivity issues**:
   - Use the "🔧 Test Connectivity" menu option
   - Verify the server URL is accessible: `curl -I https://climate-adaptation-services.geospatialhosting.com/geoserver`
   - Check if WMTS service is available: `curl -s "https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts?REQUEST=GetCapabilities"`

4. **Credential configuration**:
   - Verify `credentials.json` format matches `credentials.json.example`
   - Test credentials with: `python3 geoserver_config.py`

5. **Load tests failing**:
   - Start with smaller loads (100 requests, 10 concurrent)
   - Check Apache Bench installation: `ab -V`
   - Review target URLs in test scripts

### Debug Mode

Enable debug output for troubleshooting:
```bash
export CURL_VERBOSE=1  # For curl debugging
bash -x geoserver_menu.sh  # For script debugging
```

## 🌟 Contributing & Customization

### Adapting for Other GeoServer Instances

1. **Update server configuration** in `geoserver_menu.sh`:
   ```bash
   GEOSERVER_BASE="https://your-server.com/geoserver"
   ```

2. **Modify layer list** in both `geoserver_menu.sh` and `geoserver_config.py`:
   ```bash
   declare -A LAYERS=(
       ["your_layer"]="workspace:layername"
   )
   ```

3. **Adjust bounding box** for your region:
   ```bash
   # Update tile coordinates and bbox for your area of interest
   ```

### Adding New Features

- **New metrics**: Extend Apache Bench output parsing in load test scripts
- **Additional formats**: Add JPEG/WebP testing alongside PNG
- **Custom tile matrices**: Support for different projections beyond EPSG:3857
- **Monitoring integration**: Add hooks for external monitoring systems

This suite provides a solid foundation for GeoServer performance testing and can be extended for various geospatial load testing scenarios.