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

      in
      {
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
            echo "Target GeoServer: https://climate-adaptation-services.geospatialhosting.com/geoserver"
            echo ""
            echo "Quick start:"
            echo "  ./geoserver_menu.sh    # Interactive menu for load testing"
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
