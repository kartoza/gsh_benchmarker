#!/usr/bin/env bash
# Test WMTS tile access for all four layers

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

# Beautiful banner
gum style \
  --foreground "$KARTOZA_HIGHLIGHT2" --border-foreground "$KARTOZA_HIGHLIGHT2" --border double \
  --align center --width 60 --margin "1 2" --padding "1 2" \
  "🔍 WMTS Connectivity Test" \
  "" \
  "Testing tile access for all layers" \
  "Netherlands area • Zoom level 8"

echo ""

# Base WMTS URL
WMTS_BASE="https://climate-adaptation-services.geospatialhosting.com/geoserver/gwc/service/wmts"

# Test tiles for Netherlands area at zoom level 8
# Calculated for Netherlands bounds: 3.05,50.73 to 7.35,53.72
ZOOM=8
TILECOL=133 # Tile column for Netherlands area
TILEROW=84  # Tile row for Netherlands area

gum style --foreground "$KARTOZA_HIGHLIGHT3" "🌐 Base URL: $WMTS_BASE"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "📍 Tile coordinates: Col=$TILECOL, Row=$TILEROW, Zoom=$ZOOM"
echo ""

# Define layers with descriptions
declare -A layers=(
  ["CAS:AfstandTotKoelte"]="Distance to Cooling Areas"
  ["CAS:bkb_2024"]="Built Environment Database 2024"
  ["CAS:pok_normplusklimaatverandering2100_50cm"]="Climate Change Impact 2100"
  ["CAS:zonalstatistics_pet2022actueel_2024124"]="Zonal Statistics PET 2022"
)

urls=()
success_count=0
total_count=0

for layer in "${!layers[@]}"; do
  description="${layers[$layer]}"
  ((total_count++))

  gum style --foreground "$KARTOZA_HIGHLIGHT2" "🧪 Testing: $description"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "   Layer: $layer"

  # Build tile URL
  TILE_URL="${WMTS_BASE}?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=${ZOOM}&TILEROW=${TILEROW}&TILECOL=${TILECOL}&FORMAT=image/png"
  urls+=("$TILE_URL")

  # Test the URL
  response=$(curl -s -I "$TILE_URL" | head -1)
  if echo "$response" | grep -q "200 OK"; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "   ✅ SUCCESS - HTTP 200 OK"
    ((success_count++))
  elif echo "$response" | grep -q "HTTP"; then
    status=$(echo "$response" | awk '{print $2}')
    gum style --foreground "$KARTOZA_ALERT" "   ❌ FAILED - HTTP $status"
  else
    gum style --foreground "$KARTOZA_ALERT" "   ❌ FAILED - No response"
  fi

  # Show content type if available
  content_type=$(curl -s -I "$TILE_URL" | grep -i "content-type" | cut -d: -f2 | tr -d ' \r')
  if [ -n "$content_type" ]; then
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "   📄 Content-Type: $content_type"
  fi

  echo ""
done

# Summary
if [ $success_count -eq $total_count ]; then
  gum style \
    --foreground 118 --border-foreground 118 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "🎉 All Tests Passed!" \
    "" \
    "$success_count/$total_count layers responding correctly" \
    "Ready for load testing"
elif [ $success_count -gt 0 ]; then
  gum style \
    --foreground 214 --border-foreground 214 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "⚠️  Partial Success" \
    "" \
    "$success_count/$total_count layers responding" \
    "Some layers may have issues"
else
  gum style \
    --foreground 196 --border-foreground 196 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "❌ All Tests Failed" \
    "" \
    "Check server connectivity" \
    "Verify GeoServer is running"
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📋 Sample tile URLs for reference:"
for i in "${!urls[@]}"; do
  layer_num=$((i + 1))
  url="${urls[$i]}"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "   $layer_num. ${url:0:80}..."
done

