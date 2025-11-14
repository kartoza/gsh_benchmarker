#!/usr/bin/env bash
# Comprehensive Load Test for all CAS layers with incremental concurrency
# Tests: 1, 10, 100, 500, 1000, 2000, 3000, 4000, 5000 concurrent connections
# Each test makes 5000 total requests

# Source Kartoza color scheme
source "$(dirname "$0")/kartoza_colors.sh"

# Check if gum is available, fallback to echo if not
if ! command -v gum >/dev/null 2>&1; then
  echo "Warning: gum not found, using basic output"
  gum() {
    case "$1" in
    style)
      shift
      echo "$@"
      ;;
    spin)
      shift 2
      "$@"
      ;;
    *) echo "$@" ;;
    esac
  }
fi

# Test configuration
TOTAL_REQUESTS=5000
CONCURRENCY_LEVELS=(1 10 100 500 1000 2000 3000 4000 5000)
WMTS_BASE="https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="results"
REPORT_DIR="reports"

# Layer definitions
declare -A LAYERS=(
  ["AfstandTotKoelte"]="Distance to Cooling Areas"
  ["bkb_2024"]="Building Coverage Database 2024"
  ["pok_normplusklimaatverandering2100_50cm"]="Climate Change Impact 2100 (+50cm sea level)"
  ["zonalstatistics_pet2022actueel_2024124"]="Potential Evapotranspiration Statistics 2022"
)

# Create results directory
mkdir -p "$RESULTS_DIR" "$REPORT_DIR"

# Beautiful banner
gum style \
  --foreground "$KARTOZA_HIGHLIGHT2" --border-foreground "$KARTOZA_HIGHLIGHT2" --border double \
  --align center --width 80 --margin "1 2" --padding "1 2" \
  "🚀 Comprehensive GeoServer Load Test Suite" \
  "" \
  "Climate Adaptation Services Performance Testing" \
  "Incremental Concurrency Analysis: 1-5000 concurrent connections" \
  "Total requests per test: $TOTAL_REQUESTS"

echo ""

# Test parameters summary
gum style --foreground "$KARTOZA_HIGHLIGHT1" --bold "📊 Test Configuration:"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   • Total requests per test: $TOTAL_REQUESTS"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   • Concurrency levels: ${CONCURRENCY_LEVELS[*]}"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   • Layers to test: ${#LAYERS[@]}"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   • Results directory: $RESULTS_DIR"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   • Timestamp: $TIMESTAMP"

echo ""

# Function to generate WMTS URL for a layer
generate_tile_url() {
  local layer=$1
  echo "${WMTS_BASE}?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=CAS:${layer}&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=8&TILEROW=84&TILECOL=133&FORMAT=image/png"
}

# Function to run a single load test
run_load_test() {
  local layer=$1
  local concurrency=$2
  local description="$3"
  local tile_url=$4
  
  local test_id="${layer}_c${concurrency}_${TIMESTAMP}"
  local log_file="${RESULTS_DIR}/${test_id}.log"
  local csv_file="${RESULTS_DIR}/${test_id}.csv"
  local json_file="${RESULTS_DIR}/${test_id}.json"
  
  gum style --foreground "$KARTOZA_HIGHLIGHT2" "🧪 Testing: $description (C=$concurrency)"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "   Layer: $layer"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "   Concurrency: $concurrency connections"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "   Total requests: $TOTAL_REQUESTS"
  
  # Test parameters for JSON storage
  local test_params="{
    \"layer\": \"$layer\",
    \"description\": \"$description\",
    \"timestamp\": \"$TIMESTAMP\",
    \"test_id\": \"$test_id\",
    \"total_requests\": $TOTAL_REQUESTS,
    \"concurrency_level\": $concurrency,
    \"tile_url\": \"$tile_url\",
    \"test_date\": \"$(date -Iseconds)\",
    \"server\": \"climate-adaptation-services.geospatialhosting.com\",
    \"protocol\": \"WMTS\",
    \"tile_matrix\": \"8\",
    \"tile_row\": \"84\",
    \"tile_col\": \"133\",
    \"format\": \"image/png\"
  }"
  
  # Store test parameters
  echo "$test_params" > "$json_file"
  
  # Run Apache Bench test
  gum spin --spinner dot --title "Running Apache Bench test..." -- \
    ab -n $TOTAL_REQUESTS -c $concurrency -g "$csv_file" "$tile_url" > "$log_file" 2>&1
  
  if [ $? -eq 0 ]; then
    # Parse results and add to JSON
    local rps=$(grep "Requests per second" "$log_file" | awk '{print $4}')
    local mean_time=$(grep "Time per request.*mean" "$log_file" | awk '{print $4}')
    local failed=$(grep "Failed requests" "$log_file" | awk '{print $3}')
    local total_time=$(grep "Time taken for tests" "$log_file" | awk '{print $5}')
    local transfer_rate=$(grep "Transfer rate" "$log_file" | awk '{print $3}')
    
    # Calculate success rate (simple approximation)
    local success_requests=$((TOTAL_REQUESTS - ${failed:-0}))
    local success_rate=$((success_requests * 100 / TOTAL_REQUESTS))
    
    # Update JSON with results  
    local results_json=$(echo "$test_params" | jq --arg rps "$rps" --arg mean_time "$mean_time" \
      --arg failed "$failed" --arg total_time "$total_time" --arg transfer_rate "$transfer_rate" \
      --arg success_rate "$success_rate" \
      '. + {
        "results": {
          "requests_per_second": $rps,
          "mean_response_time_ms": $mean_time,
          "failed_requests": $failed,
          "total_time_seconds": $total_time,
          "transfer_rate_kbps": $transfer_rate,
          "success_rate": $success_rate
        }
      }')
    echo "$results_json" > "$json_file"
    
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "   ✅ SUCCESS"
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "      RPS: $rps"
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "      Mean time: ${mean_time}ms"
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "      Failed: $failed/$TOTAL_REQUESTS"
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "      Transfer rate: ${transfer_rate} KB/s"
  else
    gum style --foreground "$KARTOZA_ALERT" "   ❌ FAILED"
    echo "   Error details in: $log_file"
  fi
  
  echo ""
}

# Main testing loop
total_tests=$((${#LAYERS[@]} * ${#CONCURRENCY_LEVELS[@]}))
current_test=0

for layer in "${!LAYERS[@]}"; do
  description="${LAYERS[$layer]}"
  tile_url=$(generate_tile_url "$layer")
  
  gum style \
    --foreground "$KARTOZA_HIGHLIGHT1" --border-foreground "$KARTOZA_HIGHLIGHT4" --border rounded \
    --align center --width 70 --margin "1 0" --padding "1 2" \
    "🗺️ Testing Layer: $layer" \
    "$description"
  
  echo ""
  
  # Test single request first
  gum style --foreground "$KARTOZA_HIGHLIGHT2" "🔍 Pre-test: Single request validation..."
  single_result=$(curl -s -o /dev/null -w "%{http_code}" "$tile_url")
  
  if [ "$single_result" = "200" ]; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "   ✅ Layer accessible (HTTP 200)"
  else
    gum style --foreground "$KARTOZA_ALERT" "   ❌ Layer not accessible (HTTP $single_result)"
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "   Skipping this layer..."
    echo ""
    continue
  fi
  
  echo ""
  
  # Run tests for each concurrency level
  for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
    current_test=$((current_test + 1))
    
    gum style --foreground "$KARTOZA_HIGHLIGHT1" "📈 Progress: Test $current_test/$total_tests"
    
    run_load_test "$layer" "$concurrency" "$description" "$tile_url"
    
    # Brief pause between tests
    sleep 2
  done
  
  echo ""
done

# Generate summary report
gum style \
  --foreground "$KARTOZA_HIGHLIGHT2" --border-foreground "$KARTOZA_HIGHLIGHT2" --border double \
  --align center --width 70 --margin "1 0" --padding "1 2" \
  "📊 Load Testing Complete!" \
  "" \
  "Generating Comprehensive Report..."

echo ""

# Create consolidated results file
consolidated_results="$RESULTS_DIR/consolidated_results_$TIMESTAMP.json"
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📋 Creating consolidated results..."

echo "{" > "$consolidated_results"
echo "  \"test_suite\": {" >> "$consolidated_results"
echo "    \"name\": \"GeoServer Comprehensive Load Test\"," >> "$consolidated_results"
echo "    \"timestamp\": \"$TIMESTAMP\"," >> "$consolidated_results"
echo "    \"date\": \"$(date -Iseconds)\"," >> "$consolidated_results"
echo "    \"total_requests_per_test\": $TOTAL_REQUESTS," >> "$consolidated_results"
echo "    \"concurrency_levels\": [$(IFS=','; echo "${CONCURRENCY_LEVELS[*]}")],\"" >> "$consolidated_results"
echo "    \"layers_tested\": [$(printf '"%s",' "${!LAYERS[@]}" | sed 's/,$//')]," >> "$consolidated_results"
echo "    \"server\": \"climate-adaptation-services.geospatialhosting.com\"" >> "$consolidated_results"
echo "  }," >> "$consolidated_results"
echo "  \"results\": [" >> "$consolidated_results"

# Add individual test results
first=true
for json_file in "$RESULTS_DIR"/*_"$TIMESTAMP".json; do
  if [ -f "$json_file" ] && [ "$(basename "$json_file")" != "$(basename "$consolidated_results")" ]; then
    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> "$consolidated_results"
    fi
    cat "$json_file" >> "$consolidated_results"
  fi
done

echo "" >> "$consolidated_results"
echo "  ]" >> "$consolidated_results"
echo "}" >> "$consolidated_results"

gum style --foreground "$KARTOZA_HIGHLIGHT4" "✅ Consolidated results saved: $consolidated_results"

# Generate PDF report
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📄 Generating PDF report..."
if command -v python3 >/dev/null 2>&1; then
  python3 benchmark_report_generator.py "$TIMESTAMP"
else
  gum style --foreground "$KARTOZA_ALERT" "⚠️ Python3 not found - skipping PDF generation"
fi

# Final summary
gum style \
  --foreground "$KARTOZA_HIGHLIGHT4" --border-foreground "$KARTOZA_HIGHLIGHT4" --border double \
  --align center --width 70 --margin "1 0" --padding "1 2" \
  "🎉 All Tests Completed Successfully!" \
  "" \
  "Results available in: $RESULTS_DIR/" \
  "Reports available in: $REPORT_DIR/" \
  "" \
  "View consolidated results:" \
  "$consolidated_results"

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT1" --bold "📊 Next Steps:"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   1. Review individual test logs in $RESULTS_DIR/"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   2. Open PDF report from $REPORT_DIR/"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   3. Analyze consolidated results: $consolidated_results"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "   4. Compare performance across concurrency levels"

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🚀 Load testing suite complete!"