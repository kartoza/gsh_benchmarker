#!/usr/bin/env bash
# Test workflow for comprehensive load testing and PDF generation
# This creates mock data to test the reporting system without running actual load tests

# Source Kartoza color scheme
source "$(dirname "$0")/kartoza_colors.sh"

# Check if gum is available
if ! command -v gum >/dev/null 2>&1; then
  echo "Warning: gum not found, using basic output"
  gum() {
    case "$1" in
    style) shift; echo "$@" ;;
    spin) shift 2; "$@" ;;
    *) echo "$@" ;;
    esac
  }
fi

gum style \
  --foreground "$KARTOZA_HIGHLIGHT2" --border-foreground "$KARTOZA_HIGHLIGHT2" --border double \
  --align center --width 80 --margin "1 2" --padding "1 2" \
  "🧪 Testing Comprehensive Workflow" \
  "" \
  "Mock Data Generation & PDF Report Test"

echo ""

# Create test directories
TIMESTAMP="test_$(date +"%Y%m%d_%H%M%S")"
RESULTS_DIR="results"
REPORT_DIR="reports"

mkdir -p "$RESULTS_DIR" "$REPORT_DIR"

gum style --foreground "$KARTOZA_HIGHLIGHT1" "📊 Creating mock test data..."

# Mock test data for different concurrency levels
CONCURRENCY_LEVELS=(1 10 100 500 1000 2000 3000 4000 5000)
LAYERS=("AfstandTotKoelte" "bkb_2024" "pok_normplusklimaatverandering2100_50cm" "zonalstatistics_pet2022actueel_2024124")

# Create consolidated results file
consolidated_file="$RESULTS_DIR/consolidated_results_$TIMESTAMP.json"

cat > "$consolidated_file" << 'EOF'
{
  "test_suite": {
    "name": "GeoServer Comprehensive Load Test",
    "timestamp": "test_20241114_123000",
    "date": "2024-11-14T12:30:00+00:00",
    "total_requests_per_test": 5000,
    "concurrency_levels": [1, 10, 100, 500, 1000, 2000, 3000, 4000, 5000],
    "layers_tested": ["AfstandTotKoelte", "bkb_2024", "pok_normplusklimaatverandering2100_50cm", "zonalstatistics_pet2022actueel_2024124"],
    "server": "climate-adaptation-services.geospatialhosting.com"
  },
  "results": [
EOF

# Generate mock results for each layer and concurrency level
first_result=true
for layer in "${LAYERS[@]}"; do
  for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
    if [ "$first_result" = false ]; then
      echo "," >> "$consolidated_file"
    fi
    first_result=false
    
    # Calculate mock performance metrics (realistic degradation with higher concurrency)
    base_rps=50
    rps=$(echo "$base_rps * sqrt(1000 / $concurrency)" | bc -l)
    mean_time=$(echo "$concurrency / 10" | bc -l)
    failed=$(echo "$concurrency / 100" | bc -l | cut -d. -f1)
    transfer_rate=$(echo "$rps * 8.5" | bc -l)
    
    # Format the numbers nicely
    rps=$(printf "%.2f" "$rps")
    mean_time=$(printf "%.2f" "$mean_time")
    transfer_rate=$(printf "%.2f" "$transfer_rate")
    
    cat >> "$consolidated_file" << EOF
    {
      "layer": "$layer",
      "description": "Mock test for $layer",
      "timestamp": "$TIMESTAMP",
      "test_id": "${layer}_c${concurrency}_$TIMESTAMP",
      "total_requests": 5000,
      "concurrency_level": $concurrency,
      "tile_url": "https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts",
      "test_date": "2024-11-14T12:30:00+00:00",
      "server": "climate-adaptation-services.geospatialhosting.com",
      "protocol": "WMTS",
      "tile_matrix": "8",
      "tile_row": "84",
      "tile_col": "133",
      "format": "image/png",
      "results": {
        "requests_per_second": "$rps",
        "mean_response_time_ms": "$mean_time",
        "failed_requests": "$failed",
        "total_time_seconds": "100.00",
        "transfer_rate_kbps": "$transfer_rate",
        "success_rate": 99.5
      }
    }
EOF
  done
done

cat >> "$consolidated_file" << 'EOF'
  ]
}
EOF

gum style --foreground "$KARTOZA_HIGHLIGHT4" "✅ Mock consolidated results created: $consolidated_file"

# Test the PDF generation
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📄 Testing PDF generation..."

if command -v python3 >/dev/null 2>&1; then
  python3 benchmark_report_generator.py "$TIMESTAMP"
  if [ $? -eq 0 ]; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "✅ PDF generation test successful!"
  else
    gum style --foreground "$KARTOZA_ALERT" "❌ PDF generation failed"
  fi
else
  gum style --foreground "$KARTOZA_ALERT" "⚠️ Python3 not found - cannot test PDF generation"
fi

gum style \
  --foreground "$KARTOZA_HIGHLIGHT4" --border-foreground "$KARTOZA_HIGHLIGHT4" --border double \
  --align center --width 70 --margin "1 0" --padding "1 2" \
  "🎉 Workflow Test Complete!" \
  "" \
  "Mock Results: $consolidated_file" \
  "Reports: $REPORT_DIR/"

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🚀 Comprehensive workflow tested successfully!"