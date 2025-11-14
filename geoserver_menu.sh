#!/usr/bin/env bash
# GeoServer Load Testing Menu with gum and chafa
# Beautiful TUI interface for managing load tests and previewing maps

# Source Kartoza color scheme
source "$(dirname "$0")/kartoza_colors.sh"

# GeoServer configuration
GEOSERVER_BASE="https://climate-adaptation-services.geospatialhosting.com/geoserver"
WMTS_BASE="${GEOSERVER_BASE}/gwc/service/wmts"
WMS_BASE="${GEOSERVER_BASE}/wms"

# Layer definitions
declare -A LAYERS=(
  ["AfstandTotKoelte"]="CAS:AfstandTotKoelte"
  ["bkb_2024"]="CAS:bkb_2024"
  ["pok_klimaat"]="CAS:pok_normplusklimaatverandering2100_50cm"
  ["zonal_statistics"]="CAS:zonalstatistics_pet2022actueel_2024124"
)

# Layer descriptions
declare -A DESCRIPTIONS=(
  ["AfstandTotKoelte"]="Distance to Cooling Areas"
  ["bkb_2024"]="Built Environment Database 2024"
  ["pok_klimaat"]="Climate Change Impact 2100 (50cm)"
  ["zonal_statistics"]="Zonal Statistics PET 2022"
)

# Functions
show_banner() {
  gum style \
    --foreground 212 --border-foreground 212 --border double \
    --align center --width 60 --margin "1 2" --padding "2 4" \
    "🌍 GeoServer Load Testing Suite" \
    "" \
    "Climate Adaptation Services" \
    "WMTS Tile Performance Analysis"
}

get_tile_url() {
  local layer=$1
  local zoom=${2:-8}
  local col=${3:-133}
  local row=${4:-84}

  echo "${WMTS_BASE}?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=${zoom}&TILEROW=${row}&TILECOL=${col}&FORMAT=image/png"
}

get_wms_url() {
  local layer=$1
  local width=${2:-400}
  local height=${3:-300}

  echo "${WMS_BASE}?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=${layer}&STYLES=&SRS=EPSG:3857&BBOX=360584.6875,6618208.5,839275.4375,7108899.5&WIDTH=${width}&HEIGHT=${height}&FORMAT=image/png"
}

preview_layer() {
  local layer_key=$1
  local layer_name=${LAYERS[$layer_key]}
  local description=${DESCRIPTIONS[$layer_key]}

  gum style --foreground 212 "🖼️  Fetching preview for: $description"

  # Create temp directory for previews
  mkdir -p /tmp/geoserver_previews
  local preview_file="/tmp/geoserver_previews/${layer_key}.png"

  # Get WMS map
  local wms_url=$(get_wms_url "$layer_name" 600 400)

  gum spin --spinner dot --title "Downloading map..." -- \
    curl -s "$wms_url" -o "$preview_file"

  if [ -f "$preview_file" ] && [ -s "$preview_file" ]; then
    gum style --foreground 212 "📸 Preview for $description:"
    echo ""
    chafa --size 80x25 --format symbols "$preview_file"
    echo ""
    gum style --foreground 240 "Image saved to: $preview_file"
    echo ""
    gum confirm "Continue?" || return
  else
    gum style --foreground 196 "❌ Failed to fetch preview for $layer_name"
    gum confirm "Continue anyway?" || return
  fi
}

run_load_test() {
  local layer_key=$1
  local layer_name=${LAYERS[$layer_key]}
  local description=${DESCRIPTIONS[$layer_key]}

  # Get test parameters
  gum style --foreground 212 "⚡ Configuring load test for: $description"

  local requests=$(gum input --placeholder "5000" --prompt "Number of requests: " --value "5000")
  local concurrency=$(gum input --placeholder "100" --prompt "Concurrent connections: " --value "100")

  # Confirm test parameters
  gum confirm "$(gum style --foreground 214 "⚠️  Warning: This will send $requests requests with $concurrency concurrent connections to the server. Continue?")" || return

  # Create results directory
  mkdir -p results

  local tile_url=$(get_tile_url "$layer_name")
  local result_prefix="results/${layer_key}_$(date +%Y%m%d_%H%M%S)"

  gum style --foreground 212 "🚀 Starting load test..."
  gum style --foreground 240 "Target: $tile_url"
  echo ""

  # Single request test first
  gum spin --spinner dot --title "Testing connectivity..." -- \
    ab -n 1 -c 1 "$tile_url" 2>/dev/null

  if [ $? -eq 0 ]; then
    gum style --foreground 118 "✅ Connectivity test passed"
  else
    gum style --foreground 196 "❌ Connectivity test failed"
    return 1
  fi

  # Warm-up test
  echo ""
  gum style --foreground 214 "🔥 Running warm-up (100 requests, 10 concurrent)..."
  ab -n 100 -c 10 "$tile_url" 2>/dev/null | grep -E "(Requests per second|Time per request|Failed requests)" |
    while read line; do
      gum style --foreground 240 "  $line"
    done

  # Main load test
  echo ""
  gum style --foreground 212 "⚡ Running main load test..."
  gum style --foreground 240 "Progress will be shown below..."
  echo ""

  # Run the actual load test
  ab -n "$requests" -c "$concurrency" \
    -g "${result_prefix}.data" \
    -e "${result_prefix}.csv" \
    -H "Accept: image/png,*/*" \
    -H "User-Agent: GeoServer-LoadTest/1.0" \
    "$tile_url" | tee "${result_prefix}.log"

  echo ""
  gum style --foreground 118 "✅ Load test completed!"
  gum style --foreground 240 "Results saved to: ${result_prefix}.*"

  # Show summary
  if [ -f "${result_prefix}.csv" ]; then
    echo ""
    gum style --foreground 212 "📊 Performance Summary:"
    tail -1 "${result_prefix}.csv" | awk -F, '{
            printf "  Average Response Time: %.2f ms\n", $5
            printf "  95th Percentile: %.2f ms\n", $7
            printf "  Requests per Second: %.2f\n", $9
        }' | while read line; do
      gum style --foreground 240 "  $line"
    done
  fi

  # Ask if user wants to generate PDF report
  echo ""
  if gum confirm "Generate PDF report for this test?"; then
    generate_pdf_report
  fi

  gum confirm "View detailed results?" && cat "${result_prefix}.log" | less
}

generate_pdf_report() {
  gum style --foreground "$KARTOZA_HIGHLIGHT2" --border thick \
    "📊 Generating PDF Report" \
    "" \
    "Creating comprehensive benchmark report with:" \
    "• Performance metrics and charts" \
    "• Map images for each layer" \
    "• Kartoza branded styling"
  
  echo
  gum spin --spinner dot --title "Generating PDF report..." -- \
    python3 ./benchmark_report_generator.py
  
  # Check if report was created successfully
  local latest_report=$(ls -t reports/geoserver_benchmark_report_*.pdf 2>/dev/null | head -1)
  if [[ -n "$latest_report" ]]; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" \
      "✅ PDF report generated successfully!" \
      "" \
      "📄 Report: $latest_report"
    
    if gum confirm "Open the PDF report?"; then
      xdg-open "$latest_report" 2>/dev/null || echo "Please open: $latest_report"
    fi
  else
    gum style --foreground "$KARTOZA_ALERT" "❌ Failed to generate PDF report"
  fi
}

run_all_tests() {
  gum style --foreground 214 "🔥 Running ALL load tests in sequence"

  local requests=$(gum input --placeholder "5000" --prompt "Requests per layer: " --value "5000")
  local concurrency=$(gum input --placeholder "100" --prompt "Concurrent connections: " --value "100")
  local pause=$(gum input --placeholder "30" --prompt "Pause between tests (seconds): " --value "30")

  local total_requests=$((requests * ${#LAYERS[@]}))

  gum confirm "$(gum style --foreground 214 "⚠️  This will run ${#LAYERS[@]} tests with $total_requests total requests. Continue?")" || return

  mkdir -p results
  local timestamp=$(date +%Y%m%d_%H%M%S)

  for layer_key in "${!LAYERS[@]}"; do
    local layer_name=${LAYERS[$layer_key]}
    local description=${DESCRIPTIONS[$layer_key]}

    gum style --border double --padding 1 --foreground 212 "Testing: $description"

    local tile_url=$(get_tile_url "$layer_name")
    local result_prefix="results/${layer_key}_${timestamp}"

    ab -n "$requests" -c "$concurrency" \
      -g "${result_prefix}.data" \
      -e "${result_prefix}.csv" \
      -H "Accept: image/png,*/*" \
      -H "User-Agent: GeoServer-LoadTest/1.0" \
      "$tile_url" >"${result_prefix}.log" 2>&1

    gum style --foreground 118 "✅ Completed: $description"

    # Show quick summary
    if [ -f "${result_prefix}.csv" ]; then
      tail -1 "${result_prefix}.csv" | awk -F, -v desc="$description" '{
                printf "  %s: %.2f RPS, %.2f ms avg\n", desc, $9, $5
            }' | gum style --foreground 240
    fi

    # Pause between tests
    if [ "$layer_key" != "$(echo ${!LAYERS[@]} | awk '{print $NF}')" ]; then
      gum spin --spinner dot --title "Pausing between tests..." sleep "$pause"
    fi
  done

  gum style --foreground 118 "🎉 All tests completed!"
  gum style --foreground 240 "Results saved in results/ directory"
  
  # Ask if user wants to generate comprehensive PDF report
  echo ""
  if gum confirm "Generate comprehensive PDF report for all tests?"; then
    generate_pdf_report
  fi
}

view_results() {
  local results_dir="results"

  if [ ! -d "$results_dir" ] || [ -z "$(ls -A $results_dir 2>/dev/null)" ]; then
    gum style --foreground 196 "❌ No results found. Run some tests first!"
    return
  fi

  gum style --foreground 212 "📊 Available Results:"

  local selected_file=$(find "$results_dir" -name "*.csv" -o -name "*.log" |
    sort -r |
    gum choose --header "Select a result file to view:")

  if [ -n "$selected_file" ]; then
    gum style --foreground 212 "📖 Viewing: $(basename $selected_file)"
    echo ""

    if [[ "$selected_file" == *.csv ]]; then
      # Pretty print CSV results
      column -t -s ',' "$selected_file" | head -20 |
        while read line; do
          gum style --foreground 240 "$line"
        done
    else
      # Show log file
      cat "$selected_file" | less
    fi
  fi
}

# Main menu loop
main_menu() {
  while true; do
    clear
    show_banner

    local choice=$(gum choose \
      "🖼️  Preview Layer Maps" \
      "⚡ Run Single Layer Test" \
      "🔥 Run All Tests" \
      "📊 View Results" \
      "📄 Generate PDF Report" \
      "🔧 Test Connectivity" \
      "❌ Exit")

    case "$choice" in
    "🖼️  Preview Layer Maps")
      local layer_choice=$(gum choose \
        --header "Select a layer to preview:" \
        "${!DESCRIPTIONS[@]}")

      if [ -n "$layer_choice" ]; then
        preview_layer "$layer_choice"
      fi
      ;;

    "⚡ Run Single Layer Test")
      local layer_choice=$(gum choose \
        --header "Select a layer to test:" \
        "${!DESCRIPTIONS[@]}")

      if [ -n "$layer_choice" ]; then
        run_load_test "$layer_choice"
      fi
      ;;

    "🔥 Run All Tests")
      run_all_tests
      ;;

    "📊 View Results")
      view_results
      ;;

    "📄 Generate PDF Report")
      generate_pdf_report
      ;;

    "🔧 Test Connectivity")
      gum style --foreground 212 "🔍 Testing connectivity to all layers..."
      for layer_key in "${!LAYERS[@]}"; do
        local layer_name=${LAYERS[$layer_key]}
        local description=${DESCRIPTIONS[$layer_key]}
        local tile_url=$(get_tile_url "$layer_name")

        if curl -s -f "$tile_url" >/dev/null; then
          gum style --foreground 118 "✅ $description"
        else
          gum style --foreground 196 "❌ $description"
        fi
      done
      echo ""
      gum confirm "Press enter to continue..."
      ;;

    "❌ Exit")
      gum style --foreground 212 "👋 Goodbye!"
      exit 0
      ;;
    esac
  done
}

# Check dependencies
check_dependencies() {
  local missing=()

  for cmd in gum chafa ab curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing+=("$cmd")
    fi
  done

  if [ ${#missing[@]} -ne 0 ]; then
    echo "❌ Missing dependencies: ${missing[*]}"
    echo "Please run: nix develop"
    exit 1
  fi
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
  check_dependencies
  main_menu
fi
