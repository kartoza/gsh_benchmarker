{
  description = "GeoServer development environment with API testing tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        python-with-packages = pkgs.python3.withPackages (
          p: with p; [
            requests
            pyyaml
            click
            rich
            httpx
            pandas
            matplotlib
            seaborn
            reportlab
          ]
        );

        # Test runner script
        test-runner = pkgs.writeShellScriptBin "run-tests" ''
          #!/usr/bin/env bash
          set -euo pipefail
          
          echo "🧪 Running GeoServer Benchmarker Test Suite"
          echo "============================================"
          
          # Change to project directory
          cd "$(dirname "''${BASH_SOURCE[0]}")"
          
          # Find and run all test files
          test_files=$(find . -name "test_*.py" -not -path "./.*" | head -20)
          
          if [ -z "$test_files" ]; then
              echo "❌ No test files found (expected test_*.py pattern)"
              exit 1
          fi
          
          echo "Found test files:"
          for file in $test_files; do
              echo "  📄 $file"
          done
          echo
          
          # Run tests with coverage if available
          if command -v coverage &> /dev/null; then
              echo "📊 Running tests with coverage..."
              coverage erase
              for test_file in $test_files; do
                  echo "  🔍 Testing: $test_file"
                  coverage run --append --source=gsh_benchmarker "$test_file" || true
              done
              echo
              echo "📈 Coverage Report:"
              coverage report --show-missing
          else
              echo "🏃 Running tests..."
              for test_file in $test_files; do
                  echo "  🔍 Testing: $test_file"
                  python3 "$test_file" || echo "  ❌ Test failed: $test_file"
              done
          fi
          
          echo
          echo "✅ Test run completed"
        '';

        # Benchmark runner script
        benchmark-runner = pkgs.writeShellScriptBin "run-geoserver-benchmarks" ''
          #!/usr/bin/env bash
          set -euo pipefail
          
          echo "🚀 GeoServer Benchmark Runner"
          echo "============================="
          
          # Default values
          LAYER="AfstandTotKoelte"
          CONCURRENCY=10
          DURATION=30
          
          # Parse command line arguments
          while [[ $# -gt 0 ]]; do
              case $1 in
                  -l|--layer)
                      LAYER="$2"
                      shift 2
                      ;;
                  -c|--concurrency)
                      CONCURRENCY="$2"
                      shift 2
                      ;;
                  -d|--duration)
                      DURATION="$2"
                      shift 2
                      ;;
                  -h|--help)
                      echo "Usage: run-geoserver-benchmarks [OPTIONS]"
                      echo "Options:"
                      echo "  -l, --layer LAYER        Layer name (default: AfstandTotKoelte)"
                      echo "  -c, --concurrency NUM    Concurrent users (default: 10)"
                      echo "  -d, --duration SECONDS   Test duration (default: 30)"
                      echo "  -h, --help              Show this help"
                      echo
                      echo "Available layers:"
                      echo "  • AfstandTotKoelte"
                      echo "  • bkb_2024"
                      echo "  • pok_normplusklimaatverandering2100_50cm"
                      echo "  • zonalstatistics_pet2022actueel_2024124"
                      exit 0
                      ;;
                  *)
                      echo "❌ Unknown option: $1"
                      echo "Use --help for usage information"
                      exit 1
                      ;;
              esac
          done
          
          echo "🎯 Target: $LAYER"
          echo "👥 Concurrency: $CONCURRENCY users"
          echo "⏱️  Duration: $DURATION seconds"
          echo
          
          # Check if gsh_benchmarker module exists
          if [ ! -d "gsh_benchmarker" ]; then
              echo "❌ gsh_benchmarker module not found in current directory"
              exit 1
          fi
          
          # Run the benchmark
          echo "🏃 Starting benchmark..."
          python3 -m gsh_benchmarker.geoserver.gsh_benchmarker \
              --layer "$LAYER" \
              --concurrency "$CONCURRENCY" \
              --duration "$DURATION" \
              --output-format json \
              --output-format csv \
              --url "https://climate-adaptation-services.geospatialhosting.com/geoserver"
          
          echo "✅ Benchmark completed"
        '';

      in
      {
        # Make scripts available in packages
        packages = {
          inherit test-runner benchmark-runner;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Core development tools
            git
            curl
            jq

            apacheHttpd # HTTP/API testing tools
            httpie
            hurl

            # Benchmarking tools

            # Python environment with GeoServer libraries
            python-with-packages

            orbitron # Java development (for GeoServer Java client)
            openjdk17
            maven

            # Additional useful tools
            tree
            ripgrep
            fd

            # Network debugging
            netcat-openbsd
            nmap

            # JSON/XML processing
            yq-go
            xmlstarlet

            # Documentation and notes
            pandoc

            # Rust toolchain for building ATAC
            cargo
            rustc

            # Beautiful TUI components
            gum

            # Image display in terminal
            chafa

            # Image processing for map previews
            imagemagick

            # Make our custom scripts available
            test-runner
            benchmark-runner
          ];

          shellHook = ''
            echo "🌍 GeoServer Development Environment"
            echo "================================================"
            echo "Available tools:"
            echo "  • httpie - Modern command-line HTTP client"
            echo "  • hurl - Command-line tool for HTTP requests"  
            echo "  • apache-bench (ab) - HTTP server benchmarking"
            echo "  • gum - Beautiful interactive TUI components"
            echo "  • chafa - Display images in terminal"
            echo "  • python3 - With requests, httpx, and other libraries"
            echo "  • java/maven - For Java GeoServer client development"
            echo "  • cargo/rustc - For building Rust tools like ATAC"
            echo ""
            echo "Testing & Benchmarking:"
            echo "  • run-tests - Run the test suite"
            echo "  • run-geoserver-benchmarks - Run GeoServer benchmarks"
            echo ""
            echo "Target GeoServer: https://climate-adaptation-services.geospatialhosting.com/geoserver"
            echo ""
            echo "Quick start:"
            echo "  run-tests                        # Run all tests"
            echo "  run-geoserver-benchmarks --help  # See benchmark options"
            echo ""
            echo "Install Python GeoServer libraries:"
            echo "  pip install geoserver-rest geoserver-py gsconfig"
            echo ""
            echo "Install ATAC (TUI Postman alternative):"
            echo "  cargo install atac"
            echo "================================================"
          '';

          # Environment variables
          GEOSERVER_URL = "https://climate-adaptation-services.geospatialhosting.com/geoserver";
          GEOSERVER_WMS_URL = "https://climate-adaptation-services.geospatialhosting.com/geoserver/wms";
        };
      }
    );
}
