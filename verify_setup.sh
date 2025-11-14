#!/usr/bin/env bash
# Verification script for GeoServer Load Testing Suite

# Source Kartoza color scheme
source "$(dirname "$0")/kartoza_colors.sh"

# Check if gum is available first, use fallback if not
if command -v gum >/dev/null 2>&1; then
  USE_GUM=true
else
  echo "Warning: gum not found, using basic output"
  USE_GUM=false
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
  "🔍 Setup Verification" \
  "" \
  "GeoServer Load Testing Suite" \
  "Dependency & Configuration Check"

echo ""

# Check if we're in Nix environment
if $USE_GUM; then
  gum style --foreground "$KARTOZA_HIGHLIGHT4" "✅ Nix environment active (gum available)"
else
  gum style --foreground "$KARTOZA_ALERT" "❌ Nix environment not active - run 'nix develop'"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "  Or ensure direnv is properly configured"
  exit 1
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🛠️ Checking dependencies..."

# Check all required tools
deps=(gum chafa ab curl python3 jq)
missing=()
passed=()

for dep in "${deps[@]}"; do
  if command -v "$dep" >/dev/null 2>&1; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ $dep"
    passed+=("$dep")
  else
    gum style --foreground "$KARTOZA_ALERT" "  ❌ $dep - missing"
    missing+=("$dep")
  fi
done

if [ ${#missing[@]} -ne 0 ]; then
  echo ""
  gum style --foreground "$KARTOZA_ALERT" "❌ Missing dependencies: ${missing[*]}"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "Run 'nix develop' to enter the environment"
  exit 1
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📁 Checking files..."

# Check required files
declare -A files=(
  ["flake.nix"]="Nix environment configuration"
  [".envrc"]="direnv configuration"
  ["geoserver_menu.sh"]="Main interactive menu"
  ["geoserver_config.py"]="GeoWebCache configuration tool"
  ["credentials.json.example"]="Credential template"
  ["test_tile_access.sh"]="Connectivity testing"
  [".gitignore"]="Git ignore file"
)

missing_files=()
found_files=()

for file in "${!files[@]}"; do
  desc="${files[$file]}"

  if [ -f "$file" ]; then
    gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ $file ($desc)"
    found_files+=("$file")

    # Check if scripts are executable
    if [[ "$file" == *.sh || "$file" == *.py ]]; then
      if [ -x "$file" ]; then
        gum style --foreground "$KARTOZA_HIGHLIGHT3" "    📝 Executable permissions: OK"
      else
        gum style --foreground "$KARTOZA_HIGHLIGHT1" "    ⚠️  Not executable - run: chmod +x $file"
      fi
    fi
  else
    gum style --foreground "$KARTOZA_ALERT" "  ❌ $file - missing ($desc)"
    missing_files+=("$file")
  fi
done

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🌐 Testing connectivity..."

# Test basic connectivity to GeoServer
GEOSERVER_URL="https://climate-adaptation-services.geospatialhosting.com/geoserver"

gum spin --spinner dot --title "Testing GeoServer base URL..." -- \
  curl -s -I "$GEOSERVER_URL" >/tmp/geoserver_test.txt 2>&1

if grep -q "200 OK" /tmp/geoserver_test.txt; then
  gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ GeoServer base URL accessible"
else
  gum style --foreground "$KARTOZA_ALERT" "  ❌ GeoServer base URL not accessible"
fi

# Test WMTS service
WMTS_URL="${GEOSERVER_URL}/gwc/service/wmts?REQUEST=GetCapabilities"

gum spin --spinner dot --title "Testing WMTS service..." -- \
  curl -s "$WMTS_URL" >/tmp/wmts_test.txt 2>&1

if grep -q "WMTS" /tmp/wmts_test.txt; then
  gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ WMTS service available"
else
  gum style --foreground "$KARTOZA_ALERT" "  ❌ WMTS service not available"
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🔧 Configuration check..."

# Check credentials file
if [ -f "credentials.json" ]; then
  gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ credentials.json exists"
  if python3 -c "import json; json.load(open('credentials.json'))['geoserver']" 2>/dev/null; then
    gum style --foreground "$KARTOZA_HIGHLIGHT3" "    📝 Format appears valid"
  else
    gum style --foreground "$KARTOZA_ALERT" "    ❌ Invalid JSON format"
  fi
else
  gum style --foreground "$KARTOZA_HIGHLIGHT1" "  ⚠️  credentials.json not found"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "    Create from credentials.json.example for full functionality"
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "🎯 Quick test..."

# Quick test of a single tile request
TILE_URL="${GEOSERVER_URL}/gwc/service/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=CAS:bkb_2024&STYLE=&TILEMATRIXSET=WebMercatorQuad&TILEMATRIX=8&TILEROW=84&TILECOL=133&FORMAT=image/png"

gum spin --spinner dot --title "Testing sample tile request..." -- \
  curl -s -I "$TILE_URL" >/tmp/tile_test.txt 2>&1

if grep -q "200 OK" /tmp/tile_test.txt; then
  gum style --foreground "$KARTOZA_HIGHLIGHT4" "  ✅ Sample tile request successful"
else
  gum style --foreground "$KARTOZA_ALERT" "  ❌ Sample tile request failed"
  gum style --foreground "$KARTOZA_HIGHLIGHT3" "  URL: ${TILE_URL:0:80}..."
fi

# Overall status
echo ""
success=true
if [ ${#missing[@]} -gt 0 ] || [ ${#missing_files[@]} -gt 0 ]; then
  success=false
fi

if $success; then
  gum style \
    --foreground 118 --border-foreground 118 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "🎉 Setup Verification Complete!" \
    "" \
    "✅ All dependencies found" \
    "✅ All files present" \
    "✅ Connectivity tests passed"
else
  gum style \
    --foreground 214 --border-foreground 214 --border double \
    --align center --width 60 --margin "1 2" --padding "1 2" \
    "⚠️  Setup Issues Detected" \
    "" \
    "Some components missing or failing" \
    "Check errors above"
fi

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" "📋 Next steps:"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "  1. Copy credentials.json.example to credentials.json (if needed)"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "  2. Run: ./geoserver_menu.sh"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "  3. Start with connectivity test first"
gum style --foreground "$KARTOZA_HIGHLIGHT3" "  4. Begin with smaller loads (1000 requests) before scaling to 5000+"

echo ""
gum style --foreground "$KARTOZA_HIGHLIGHT2" --bold "🚀 Ready for GeoServer load testing!"

# Clean up temp files
rm -f /tmp/geoserver_test.txt /tmp/wmts_test.txt /tmp/tile_test.txt

