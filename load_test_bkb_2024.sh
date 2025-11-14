#!/bin/bash
# Load test for CAS:bkb_2024 layer

# Check if gum is available, fallback to echo if not
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

# Beautiful banner
gum style \
    --foreground 212 --border-foreground 212 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "⚡ Load Test: bkb_2024 Layer" \
    "" \
    "Built Environment Database 2024" \
    "5000 requests • 100 concurrent connections"

echo ""

# Tile URL for Netherlands area
TILE_URL="https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=CAS:bkb_2024&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=8&TILEROW=84&TILECOL=133&FORMAT=image/png"

gum style --foreground 240 "🎯 Target URL: $TILE_URL"
echo ""

# Test single request first
gum style --foreground 212 "1️⃣ Testing single tile request..."
result=$(ab -n 1 -c 1 "$TILE_URL" 2>/dev/null | grep -E "(Requests per second|Time per request|Transfer rate)")
if [ -n "$result" ]; then
    gum style --foreground 118 "✅ Single request test passed"
    echo "$result" | while read line; do
        gum style --foreground 240 "   $line"
    done
else
    gum style --foreground 196 "❌ Single request test failed"
    exit 1
fi

echo ""
gum style --foreground 214 "2️⃣ Warm-up test (100 requests, 10 concurrent)..."
gum spin --spinner dot --title "Running warm-up..." -- \
    ab -n 100 -c 10 "$TILE_URL" >/tmp/warmup_result.txt 2>&1

warmup_result=$(grep -E "(Requests per second|Time per request|Transfer rate|Failed requests)" /tmp/warmup_result.txt)
if [ -n "$warmup_result" ]; then
    gum style --foreground 118 "✅ Warm-up completed successfully"
    echo "$warmup_result" | while read line; do
        gum style --foreground 240 "   $line"
    done
else
    gum style --foreground 196 "❌ Warm-up test failed"
fi

echo ""
gum style --foreground 212 "3️⃣ Starting main load test..."
gum style --foreground 240 "   • 5000 requests with 100 concurrent connections"
gum style --foreground 240 "   • Results will be saved to bkb_2024_results.csv"
gum style --foreground 240 "   • Gnuplot data: bkb_2024_load.data"

echo ""
gum style --foreground 214 --bold "🚀 Running Apache Bench load test..."

# Main load test with detailed output
ab -n 5000 -c 100 \
   -g bkb_2024_load.data \
   -e bkb_2024_results.csv \
   -H "Accept: image/png,*/*" \
   -H "User-Agent: GeoServer-LoadTest/1.0" \
   -H "Cache-Control: no-cache" \
   "$TILE_URL"

echo ""
# Check if test completed successfully
if [ $? -eq 0 ] && [ -f "bkb_2024_results.csv" ]; then
    gum style \
        --foreground 118 --border-foreground 118 --border double \
        --align center --width 60 --margin "1 2" --padding "1 2" \
        "✅ Load Test Completed Successfully!" \
        "" \
        "📊 Results: bkb_2024_results.csv" \
        "📈 Gnuplot data: bkb_2024_load.data"
    
    # Show quick summary if CSV exists
    if [ -f "bkb_2024_results.csv" ] && [ -s "bkb_2024_results.csv" ]; then
        echo ""
        gum style --foreground 212 "📈 Quick Performance Summary:"
        tail -1 "bkb_2024_results.csv" | awk -F, '{
            printf "   Average Response Time: %.2f ms\n", $5
            printf "   95th Percentile: %.2f ms\n", $7  
            printf "   Requests per Second: %.2f\n", $9
        }' | while read line; do
            gum style --foreground 240 "$line"
        done
    fi
else
    gum style \
        --foreground 196 --border-foreground 196 --border double \
        --align center --width 60 --margin "1 2" --padding "1 2" \
        "❌ Load Test Failed" \
        "" \
        "Check server connectivity and try again"
fi

# Clean up temp files
rm -f /tmp/warmup_result.txt